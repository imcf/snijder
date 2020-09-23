# -*- coding: utf-8 -*-
"""
Job description class module.

Classes
-------

JobDescription()
    Parser for job descriptions, works on files or strings.
"""

import ConfigParser
import StringIO
import os
import pprint
import shutil
import time
import json
from hashlib import sha1

from . import logi, logd, logw, logc, loge
from . import JOBFILE_VER


### TODO (refactoring): group exception-silencing functions into own module
# these module-level functions are basically there to catch exceptions, add a message to
# the logs and then continue, which is required when operating a spooler / queue in a
# daemon process - they should go into their own module


def select_queue_for_job(job, mapping=None):
    """Select a queue for a job, depending on its job- and tasktype.

    Parameters
    ----------
    job : snijder.jobs.JobDescription
    mapping : dict, optional
        A mapping translating jobtype and tasktype to a queue name, by default `None`
        which gets expanded to the built-in mapping (see code below).
    """
    if mapping is None:
        mapping = {
            "hucore": {"decon": "hucore", "preview": "hucore"},
            "dummy": {"sleep": "hucore"},
        }
    if job["type"] not in mapping:
        logc("No queue found for jobtype '%s'!", job["type"])
        return None
    if job["tasktype"] not in mapping[job["type"]]:
        logc("No queue found for tasktype '%s'!", job["tasktype"])
        return None
    queuetype = mapping[job["type"]][job["tasktype"]]
    logd(
        "Selected queue for jobtype (%s) and tasktype (%s): %s",
        job["type"],
        job["tasktype"],
        queuetype,
    )
    return queuetype


def process_jobfile(fname, queues, mapping=None):
    """Parse a jobfile and add it to its destination queue.

    Parameters
    ----------
    fname : str
        The name of the job file to parse.
    queues : dict
        Containing the JobQueue objects for the different queues, using the
        corresponding 'type' keyword as identifier.
    mapping : dict, optional
        A mapping being passed on to select_queue_for_job(), by default `None`.
    """
    try:
        job = JobDescription(fname, "file")
    except IOError as err:
        logw("Error reading job description file (%s), skipping.", err)
        # there is nothing to add to the queue and the IOError indicates
        # problems accessing the file, so we simply return silently:
        return

    except (SyntaxError, ValueError) as err:
        # jobfile was already moved out of the way by the constructor of the
        # JobDescription object, so we simply stop here and return:
        return

    if job["type"] == "deletejobs":
        logw("Received job deletion request(s)!")
        # TODO: append only to specific queue!
        for queue in queues.itervalues():
            for delete_id in job["ids"]:
                queue.deletion_list.append(delete_id)
        # we're finished, so move the jobfile and return:
        job.move_jobfile("done")
        return
    selected_queue = select_queue_for_job(job, mapping)
    if selected_queue not in queues:
        logc("Selected queue does not exist: %s", selected_queue)
        job.move_jobfile("done")
        return

    job.move_jobfile("cur")
    try:
        queues[selected_queue].append(job)
    except ValueError as err:
        loge("Adding the new job from [%s] failed:\n    %s", fname, err)


### TODO (refactoring): group exception-silencing functions into own module


class AbstractJobConfigParser(dict):
    """Abstract class to parse new jobs from an ini-style syntax.

    Read a job description either from a file or a string and parse
    the sections, check them for sane values and store them in a dict.
    """

    def __init__(self, jobconfig, srctype):
        """Set up the object for parsing job configurations.

        Parameters
        ----------
        jobconfig : str
            Either the path to a file, or the job configuration directly.
        srctype : str
            One of 'file' or 'string', denoting what's in 'jobconfig'.
        """
        super(AbstractJobConfigParser, self).__init__()
        self.sections = []
        self["infiles"] = []
        if srctype == "file":
            jobconfig = self.read_jobfile(jobconfig)
        elif srctype == "string":
            pass
        else:
            raise TypeError("Unknown source type '%s'" % srctype)
        # store the SHA1 digest of this job, serving as the UID:
        self["uid"] = sha1(jobconfig).hexdigest()
        self.parse_jobconfig(jobconfig)
        # fill in keys without a reasonable value, they'll be updated later:
        self["status"] = "N/A"
        self["start"] = "N/A"
        self["progress"] = "N/A"
        self["pid"] = "N/A"
        self["server"] = "N/A"

    @staticmethod
    def read_jobfile(jobfile):
        """Read in a job config file into a string.

        Parameters
        ----------
        jobfile : str

        Returns
        -------
        config_raw : str
            The file content as a single string.
        """
        logi("Parsing jobfile '%s'...", os.path.basename(jobfile))
        logd("Full jobfile path: '%s'...", jobfile)
        if not os.path.exists(jobfile):
            raise IOError("Can't find file '%s'!" % jobfile)
        if not os.access(jobfile, os.R_OK):
            raise IOError("No permission reading file '%s'!" % jobfile)
        # sometimes the inotify event gets processed very rapidly and we're
        # trying to parse the file *BEFORE* it has been written to disk
        # entirely, which breaks the parsing, so we introduce four additional
        # levels of waiting time to avoid this race condition:
        config_raw = []
        for snooze in [0, 0.00001, 0.0001, 0.001, 0.01, 0.1]:
            if snooze > 0:  # pragma: no cover
                logd("Failed reading jobfile, trying again in %ss.", snooze)
            time.sleep(snooze)
            try:
                with open(jobfile, "r") as fileobject:
                    config_raw = fileobject.read()
            except TypeError as err:  # pragma: no cover
                # sometimes the 'with open' statement raises a TypeError
                # ("coercing to Unicode: need string or buffer, file found"),
                # which is probably some race condition - just try again...
                loge("'with open' statement resulted in error: %s", err)
                continue

            if config_raw:
                logd("Reading the job file succeeded after %ss!", snooze)
                break

        if not config_raw:
            raise IOError("Unable to read job config file '%s'!" % jobfile)

        return config_raw

    def get_option(self, section, option):
        """Helper method to get an option and remove it from the section.

        Parameters
        ----------
        section : str
        option : str

        Returns
        -------
        value : str
        """
        value = self.jobparser.get(section, option)
        self.jobparser.remove_option(section, option)
        return value

    def check_for_remaining_options(self, section):
        """Helper method to check if a section has remaining items."""
        remaining = self.jobparser.items(section)
        if remaining:
            raise ValueError(
                "Job config invalid, section '%s' contains unknown options: %s"
                % (section, remaining)
            )

    def parse_section_entries(self, section, mapping):
        """Helper function to read a given list of options from a section.

        Parameters
        ----------
        section : str
            The name of the section to parse.
        mapping : list of tuples
            A list of tuples containing the mapping from the option names in
            the config file to the key names in the JobDescription object, e.g.

            mapping = [
                ['version', 'ver'],
                ['username', 'user'],
                ['useremail', 'email'],
                ['timestamp', 'timestamp'],
                ['jobtype', 'type']
            ]
        """
        if not self.jobparser.has_section(section):
            raise ValueError("Section '%s' missing in job config!" % section)
        for cfg_option, job_key in mapping:
            try:
                self[job_key] = self.get_option(section, cfg_option)
            except ConfigParser.NoOptionError:
                raise ValueError(
                    "Option '%s' missing from section '%s'!" % (cfg_option, section)
                )
        # by now the section should be fully parsed and therefore empty:
        self.check_for_remaining_options("snijderjob")

    def parse_jobconfig(self, cfg_raw):
        """Initialize ConfigParser and run parsing method."""
        # we only initialize the ConfigParser object now, not in __init__():
        self.jobparser = ConfigParser.RawConfigParser()
        try:
            self.jobparser.readfp(StringIO.StringIO(cfg_raw))
            logd("Read job configuration file / string.")
        except ConfigParser.MissingSectionHeaderError as err:
            raise SyntaxError("ERROR in JobDescription: %s" % err)
        self.sections = self.jobparser.sections()
        if not self.sections:
            raise SyntaxError("No sections found in job config!")
        logd("Job description sections: %s", self.sections)
        self.parse_jobdescription()

    def parse_jobdescription(self):
        """Abstract method to be overridden in derived classes.

        Raises a NotImplementedError if called.
        """
        raise NotImplementedError(
            "This is an abstract class, which is not meant to be instantiated!"
        )


class SnijderJobConfigParser(AbstractJobConfigParser):
    """Derived class to parse snijder job configurations."""

    def __init__(self, jobconfig, srctype):
        """Call the parent class constructor with the appropriate arguments.

        Parameters
        ----------
        jobconfig : str
            Either the path to a file, or the job configuration directly.
        srctype : str
            One of 'file' or 'string', denoting what's in 'jobconfig'.
        """
        super(SnijderJobConfigParser, self).__init__(jobconfig, srctype)

    def parse_jobdescription(self):
        """Parse details for a snijder job and check for sanity.

        Use the ConfigParser object and assemble a dicitonary with the collected details
        that contains all the information for launching a new processing task. Raises
        Exceptions in case something unexpected is found in the given file.
        """
        # prepare the parser-mapping for the generic 'snijderjob' section:
        mapping = [
            ["version", "ver"],
            ["username", "user"],
            ["useremail", "email"],
            ["timestamp", "timestamp"],
            ["jobtype", "type"],
        ]
        # now parse the section:
        self.parse_section_entries("snijderjob", mapping)
        # sanity-check / validate the parsed options:
        if self["ver"] != JOBFILE_VER:
            raise ValueError("Unexpected jobfile version '%s'." % self["ver"])
        if self["timestamp"] == "on_parsing":
            # the keyword "on_parsing" requires us to fill in the value:
            self["timestamp"] = time.time()
            # in this case we also adjust the UID of the job - this is mostly
            # done to allow submitting the same jobfile multiple times during
            # testing and should not be used in production, therefore we also
            # issue a corresponding warning message:
            self["uid"] = sha1("%.18f" % self["timestamp"]).hexdigest()
            logw("===%s", " WARNING ===" * 8)
            logw('"timestamp = on_parsing" is meant for testing only!!!')
            logw("===%s", " WARNING ===" * 8)
        else:
            # otherwise we need to convert to float, or raise an error:
            try:
                self["timestamp"] = float(self["timestamp"])
            except ValueError:
                raise ValueError("Invalid timestamp: %s." % self["timestamp"])
        # now call the jobtype-specific parser method(s):
        if self["type"] == "hucore":
            self.parse_job_hucore()
        elif self["type"] == "dummy":
            self.parse_job_dummy()
        elif self["type"] == "deletejobs":
            self.parse_job_deletejobs()
        else:
            raise ValueError("Unknown jobtype '%s'" % self["type"])

    def parse_job_hucore(self):
        """Do the specific parsing of "hucore" type jobfiles.

        Parse the "hucore" and the "inputfiles" sections of snijder job
        configuration files.
        """
        # prepare the parser-mapping for the specific 'hucore' section:
        mapping = [
            ["tasktype", "tasktype"],
            ["executable", "exec"],
            ["template", "template"],
        ]
        # now parse the section:
        self.parse_section_entries("hucore", mapping)
        if self["tasktype"] not in ["decon", "preview"]:
            raise ValueError("Tasktype invalid: %s" % self["tasktype"])
        # and the input file(s) section:
        # TODO: can we check if this section contains nonsense values?
        if "inputfiles" not in self.sections:
            raise ValueError("Section 'inputfiles' missing in job config!")
        for option in self.jobparser.options("inputfiles"):
            infile = self.get_option("inputfiles", option)
            self["infiles"].append(infile)
        if not self["infiles"]:
            raise ValueError("No input files defined in job config!")

    def parse_job_dummy(self):
        """Do the specific parsing of "dummy" type jobfiles."""
        # prepare the parser-mapping for the specific 'hucore' section:
        mapping = [["tasktype", "tasktype"], ["executable", "exec"]]
        # now parse the section:
        self.parse_section_entries("hucore", mapping)
        if self["tasktype"] != "sleep":
            raise ValueError("Tasktype invalid: %s" % self["tasktype"])

    def parse_job_deletejobs(self):
        """Do the specific parsing of "deletejobs" type jobfiles."""
        if "deletejobs" not in self.sections:
            raise ValueError("No 'deletejobs' section in job config!")
        try:
            jobids = self.get_option("deletejobs", "ids")
        except ConfigParser.NoOptionError:
            raise ValueError("Can't find job IDs in job config!")
        # split string at commas, strip whitespace from components:
        self["ids"] = [jobid.strip() for jobid in jobids.split(",")]
        for jobid in self["ids"]:
            logi("Request to --- DELETE --- job '%s'", jobid)


class JobDescription(dict):
    """Abstraction class for handling snijder job descriptions.

    Class Variables
    ---------------
    spooldirs : dict
        The spooldirs dict is supposed to be set explicitly before the first instance of
        a JobDescription is created, this way giving all objects access to the same
        dict. Can be left at its default 'None', but this only makes sense for testing,
        probably not in a real scenario.

    Instance Variables
    ------------------
    fname : str
        The file name from where the job configuration has been parsed, or 'None' in
        case the job was supplied in a string directly.
    """

    spooldirs = None

    def __init__(self, job, srctype):
        """Initialize depending on the type of description source.

        Parameters
        ----------
        job : string
            The actual job configuration. Can be either a filename pointing to a job
            config file, or a configuration (plain-text) itself, requires 'srctype' to
            be set accordingly!
        srctype : string
            One of ['file', 'string'], determines whether 'job' should be
            interpreted as a filename or as a job description string.

        Example
        -------
        >>> job = snijder.JobDescription('/path/to/jobdescription.cfg', 'file')
        """
        super(JobDescription, self).__init__()

        if JobDescription.spooldirs is None:
            logc(
                "Class variable 'spooldirs' is 'None', this is not intended "
                "for production use! TESTING ONLY!!"
            )
        if srctype == "file":
            self.fname = job
        else:
            self.fname = None
        try:
            parsed_job = SnijderJobConfigParser(job, srctype)
        except (SyntaxError, ValueError) as err:
            logw("Ignoring job config, parsing failed: %s", err)
            if srctype == "file":
                logw("Invalid job config file: %s", job)
                # set the 'uid' key as otherwise moving the file would fail:
                self["uid"] = os.path.basename(job)
                self.move_jobfile("done", ".invalid")
            raise err
        self.update(parsed_job)
        del parsed_job

        logd("Finished initialization of JobDescription().")
        logd(pprint.pformat(self))

    def __setitem__(self, key, value):
        if self.has_key(key) and self[key] == value:
            return
        logd("Setting JobDescription '%s' to '%s'", key, value)
        super(JobDescription, self).__setitem__(key, value)
        # on status changes, update / store the job
        if key == "status":
            self.store_job()

    def store_job(self):
        """Store the job configuration into a JSON file."""
        # TODO: implement real storing instead of dumping the json!
        logd("JobDescription.store_job: %s", json.dumps(self))

    def move_jobfile(self, target, suffix=".jobfile"):
        """Move a jobfile to the desired spooling subdir.

        The file name will be set automatically to the job's UID with an
        added suffix ".jobfile", no matter how the file was called before.

        WARNING: destination file is not checked, if it exists and we have
        write permissions, it is simply overwritten!

        Parameters
        ----------
        target : str
            The key for the spooldirs-dict denoting the target directory.
        suffix : str (optional)
            An optional suffix, by default ".jobfile" will be used if empty.
        """
        # make sure to only move "file" job descriptions, return otherwise:
        if self.fname is None:
            logd("Job description is a string, move_jobfile() doesn't make sense here.")
            return
        if JobDescription.spooldirs is None:
            logw("Not moving jobfile as 'spooldirs' class variable is unset!")
            return

        # pylint: disable-msg=unsubscriptable-object
        target = os.path.join(JobDescription.spooldirs[target], self["uid"] + suffix)
        # pylint: enable-msg=unsubscriptable-object

        if os.path.exists(target):
            target += ".%s" % time.time()
            logd("Adding suffix to prevent overwriting file: %s", target)
        # logd("Moving file '%s' to '%s'.", self.fname, target)
        shutil.move(self.fname, target)
        logd("Moved job file '%s' to '%s'.", self.fname, target)
        # update the job's internal fname pointer:
        self.fname = target

    def get_category(self):
        """Get the category of this job, in our case the value of 'user'."""
        return self["user"]
