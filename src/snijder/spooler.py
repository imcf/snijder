# -*- coding: utf-8 -*-
"""Job spooler class module.

Classes
-------

JobSpooler()
    Spooler processing jobs.
"""

# TODO: don't transfer the image files, create a symlink or put their path
#       into the HuCore Tcl script
# TODO: catch exceptions on dispatching jobs, otherwise the QM gets stuck:
#       it stops watching the "new" spool directory if instantiating a
#       gc3libs.Application fails (resulting in a "dead" state right now),
#       instead a notification needs to be sent/printed to the user (later
#       this should trigger an email).

import os
import pprint
import time
import psutil

import gc3libs
import gc3libs.config

from . import logi, logd, logw, logc, loge
from . import JOBFILE_VER
from .apps import hucore, dummy
from .jobs import JobDescription


class JobSpooler(object):

    """Spooler class processing the queue, dispatching jobs, etc.

        Instance Attributes
        -------------------
        apps : list
        dirs : dict
            A dict with runtime dirs as returned by JobSpooler.setup_rundirs().
        queue : JobQueue
            The queue for this spooler.
        # queues : dict(snijder.JobQueue)  # TODO: multi-queue logic (#136, #272)
        gc3cfg : dict
            A dict with gc3 config paths as returned by JobSpooler.check_gc3conf().
        engine : gc3libs.core.Engine
            The gc3 engine object to be used for this spooler.
        status : str
            The current spooler status.
    """

    __allowed_status_values__ = ["shutdown", "refresh", "pause", "run"]

    def __init__(self, spooldir, queue, gc3conf):
        """Prepare the spooler.

        Check the GC3Pie config file, set up the gc3 engine, check the resource
        directories.

        Parameters
        ----------
        spooldir : str
            Spooling directory base path.
        queue : snijder.JobQueue
        gc3conf : str
            The path to a gc3pie configuration file.
        """
        self.apps = list()
        self.dirs = self.setup_rundirs(spooldir)
        # set the JobDescription class variable for the spooldirs:
        JobDescription.spooldirs = self.dirs
        self.queue = queue
        # self.queues = dict()  # TODO: multi-queue logic (#136, #272)
        self._status = self._status_pre = "run"  # the initial status is 'run'
        self.gc3cfg = self.check_gc3conf(gc3conf)
        self.engine = self.setup_engine()
        logi("Created JobSpooler.")

    @property
    def status(self):
        """Get the 'status' variable."""
        return self._status

    @status.setter
    def status(self, newstatus):
        """Set the 'status' variable, perform non-spooling actions."""
        if newstatus not in self.__allowed_status_values__:
            logw("Invalid spooler status requested, ignoring: [%s]", newstatus)
            return

        if newstatus == "refresh":
            # don't change the status on "refresh", instead simply print the
            # queue status and update the status file:
            logi("Received spooler queue status refresh request.")
            logd(self.queue.update_status(force=True))
            return

        if newstatus == self.status:
            # no change required, so return immediately:
            return

        self._status_pre = self.status
        self._status = newstatus
        logw(
            "Received spooler status change request: %s -> %s",
            self._status_pre,
            self.status,
        )

    def run(self):
        """Set the spooler status to 'run'."""
        self.status = "run"

    def refresh(self):
        """Request a refresh of the spooler status.

        This will update the status file and print the queue status to the logs.
        """
        self.status = "refresh"

    def pause(self):
        """Set the spooler status to 'pause'."""
        self.status = "pause"

    def shutdown(self):
        """Request the spooler to shut down."""
        self.status = "shutdown"

    @staticmethod
    def setup_rundirs(base_dir):
        """Check if all runtime dirs exist or try to create them otherwise.

        Assuming base_dir is '/run', the expected structure is like this:

        /run
            |-- queue
            |   |-- requests
            |   `-- status
            `-- spool
                |-- cur
                |-- done
                `-- new

        Parameters
        ----------
        base_dir : str
            Base path where to set up / check the run directories.

        Returns
        -------
        full_subdirs : {
            'new'      : '/run/spool/new',
            'cur'      : '/run/spool/cur',
            'done'     : '/run/spool/done',
            'requests' : '/run/queue/requests',
            'status'   : '/run/queue/status',
            'newfiles' : list of existing files in the 'new' directory,
            'curfiles' : list of existing files in the 'cur' directory
        }
        """
        full_subdirs = dict()
        tree = {"spool": ["new", "cur", "done"], "queue": ["status", "requests"]}
        for run_dir in tree:
            for sub_dir in tree[run_dir]:
                cur = os.path.join(base_dir, run_dir, sub_dir)
                if not os.access(cur, os.W_OK):
                    if os.path.exists(cur):
                        raise OSError(
                            "Directory '%s' exists, but it is not "
                            "writable for us. Stopping!" % cur
                        )
                    try:
                        os.makedirs(cur)
                        logi("Created spool directory '%s'.", cur)
                    except OSError as err:
                        raise OSError(
                            "Error creating Queue Manager runtime "
                            "directory '%s': %s" % (cur, err)
                        )
                full_subdirs[sub_dir] = cur

        # pick up any existing jobfiles in the 'new' spooldir
        full_subdirs["newfiles"] = list()
        new_existing = os.listdir(full_subdirs["new"])
        if new_existing:
            logw("%s PRE-SUBMITTED JOBS %s", "=" * 60, "=" * 60)
            logw(
                "Spooling directory '%s' contains files that were already "
                "submitted prior to the QM startup.",
                full_subdirs["new"],
            )
            for fname in new_existing:
                logw("- file: %s", fname)
                full_subdirs["newfiles"].append(fname)
            logw("%s PRE-SUBMITTED JOBS %s", "=" * 60, "=" * 60)
        logi("Runtime directories:\n%s", pprint.pformat(full_subdirs))

        # check 'cur' dir and remember files for resuming from a queue shutdown:
        full_subdirs["curfiles"] = list()
        cur_existing = os.listdir(full_subdirs["cur"])
        if cur_existing:
            logi("%s PREVIOUS JOBS %s", "=" * 60, "=" * 60)
            logi(
                "Spooling directory '%s' contains files from a previous "
                "session, will try to resume them!",
                full_subdirs["cur"],
            )
            for fname in cur_existing:
                logi("- file: %s", fname)
                full_subdirs["curfiles"].append(fname)
            logi("%s PREVIOUS JOBS %s", "=" * 60, "=" * 60)
        return full_subdirs

    @staticmethod
    def check_gc3conf(gc3conffile):
        """Check the gc3 config file and extract the gc3 spooldir.

        Parameters
        ----------
        gc3conffile : str

        Returns
        -------
        cfg : dict
            A dict with keys 'spooldir' and 'conffile'.
        """
        cfg = dict()
        gc3conf = gc3libs.config.Configuration(gc3conffile)
        try:
            cfg["spooldir"] = gc3conf.resources["localhost"].spooldir
            logi("Using gc3pie spooldir: %s", cfg["spooldir"])
        except AttributeError:
            raise AttributeError(
                "Unable to parse spooldir for resource "
                "'localhost' from gc3pie config file '%s'!" % gc3conffile
            )
        cfg["conffile"] = gc3conffile
        return cfg

    @staticmethod
    def scan_gc3_resource_dirs(engine):
        """Check if the resource dirs of all resources are clean.

        Parameters
        ----------
        engine : gc3libs.core.Engine
            The gc3 engine from which the resource dirs should be checked.

        Returns
        -------
        list(str)
            All files in any resource directory, empty if all clean.
        """
        unclean = list()
        for resource in engine.get_resources():
            resourcedir = os.path.expandvars(resource.resource_dir)
            logi(
                "Checking resource dir for resource '%s': [%s]",
                resource.name,
                resourcedir,
            )
            if not os.path.exists(resourcedir):
                # TODO: should this really be ignored silently?!
                continue
            files = os.listdir(resourcedir)
            if files:
                logw("Resource dir unclean: [%s] - files: %s", resourcedir, files)
                for resfile in files:
                    unclean.append(os.path.join(resourcedir, resfile))
            else:
                logd("Resource dir is clean, all good!")

        return unclean

    @staticmethod
    def check_running_gc3_jobs(engine):
        """Inspect and clean up PID files in gc3pie resource dirs.

        Parameters
        ----------
        engine : gc3libs.core.Engine
            The gc3 engine from which the resource dirs should be checked.

        Returns
        -------
        dict
            A dict with PIDs as keys, having resource file names as values.
        """
        gc3_files = JobSpooler.scan_gc3_resource_dirs(engine)
        logi("Inspecting gc3pie resource files for running processes.")
        gc3_jobs = dict()
        for resfile in gc3_files:
            try:
                pid = int(os.path.basename(resfile))
                cmd = psutil.Process(pid).cmdline()
                logd("Found process matching [pid:%s]: %s", pid, cmd)
                if "gc3pie" in str(cmd):
                    logw("Potentially a running gc3 job: [pid:%s] [cmd:%s]", pid, cmd)
                    gc3_jobs[pid] = resfile
                    continue

            except ValueError as err:
                logw("Unable to parse a pid from file [%s]: %s", resfile, err)
            except psutil.NoSuchProcess:
                logd("No process found matching [pid:%s].", pid)
            except Exception as err:  # pragma: no cover
                loge(
                    "Unexpected error while checking resource file [%s]: %s",
                    resfile,
                    err,
                )
                raise err

            logi("Removing file not related to a gc3 job: [file:%s]", resfile)
            os.remove(resfile)

        return gc3_jobs

    @staticmethod
    def check_gc3_resources(engine):
        """Check if gc3 resource directories are clean.

        Parameters
        ----------
        engine : gc3libs.core.Engine
            The gc3 engine from which the resource dirs should be checked.

        Raises
        ------
        RuntimeError
            In case the resource dir can't be cleaned (e.g. because the job files
            therein correspond to existing processes), a RuntimeError is raised.
        """
        running_gc3jobs = JobSpooler.check_running_gc3_jobs(engine)
        if running_gc3jobs:
            logc("The gc3pie resource directories are unclean!")
            msg = (
                "One or more gc3pie resource directories are containing gc3 job files "
                "referring to running processes.\n\n"
                "Please check if these processes are terminated and clean up those "
                "files before starting the queue manager again!\n"
            )
            for job in running_gc3jobs.iteritems():
                msg += "\n PID: %s - gc3pie job resource file: [%s]" % job
            raise RuntimeError(msg)

    def setup_engine(self):
        """Wrapper to set up the GC3Pie engine.

        Returns
        -------
        gc3libs.core.Engine
        """
        logi('Creating GC3Pie engine using config file "%s".', self.gc3cfg["conffile"])
        engine = gc3libs.create_engine(self.gc3cfg["conffile"])
        self.check_gc3_resources(engine)

        return engine

    def engine_status(self):
        """Helper to get the engine status and print a formatted log."""
        stats = self.engine.counts()
        logd(
            "Engine: NEW:%s  SUBM:%s  RUN:%s  TERM'ing:%s  TERM'ed:%s  "
            "UNKNWN:%s  STOP:%s  (total:%s)",
            stats["NEW"],
            stats["SUBMITTED"],
            stats["RUNNING"],
            stats["TERMINATING"],
            stats["TERMINATED"],
            stats["UNKNOWN"],
            stats["STOPPED"],
            stats["total"],
        )
        return stats

    def check_status_request(self):
        """Check if a status change for the QM was requested."""
        for fname in self.__allowed_status_values__:
            check_file = os.path.join(self.dirs["requests"], fname)
            if os.path.exists(check_file):
                os.remove(check_file)
                self.status = fname
                # we don't process more than one request at a time, so exit:
                return

    def check_for_jobs_to_delete(self):
        """Process job deletion requests for all queues."""
        # first process jobs that have been dispatched already:
        for app in self.apps:
            uid = app.job["uid"]
            if uid in self.queue.deletion_list:
                # TODO: we need to make sure that the calls to the engine in
                # kill_running_job() do not accidentally submit the next job
                # as it could be potentially enlisted for removal...
                self.kill_running_job(app)
                self.queue.deletion_list.remove(uid)
        # then process deletion requests for waiting jobs (note: killed jobs
        # have been removed from the queue by the kill_running_job() method)
        self.queue.process_deletion_list()

    def spool(self):
        """Wrapper for the spooler to catch Ctrl-C and clean up after spooling."""
        try:
            self._spool()
        except KeyboardInterrupt:
            logi("Received keyboard interrupt, stopping queue manager.")
        finally:
            self.cleanup()

    def _spool(self):
        """Spooler function dispatching jobs from the queues. BLOCKING!"""
        print "*" * 80
        print "snijder-queue spooler running, press ctrl-c to shut it down"
        print "*" * 80
        logi("SNIJDER spooler started, expected jobfile version: %s.", JOBFILE_VER)
        # dict with a mapping from jobtypes to app classes:
        apptypes = {
            "hucore": hucore.HuDeconApp,
            "dummy": dummy.DummySleepApp,
        }
        while True:
            self.check_status_request()
            if self.status == "run":
                # process deletion requests before anything else
                self.check_for_jobs_to_delete()
                # TODO: gc3pie logs an 'UnrecoverableDataStagingError' in case
                # one of the input files can't be found - can we somehow catch
                # this (it doesn't seem to raise an exception)?
                self.engine.progress()
                for i, app in enumerate(self.apps):
                    new_state = app.status_changed()
                    if new_state is not None:
                        self.queue.set_jobstatus(app.job, new_state)

                    # pylint: disable-msg=no-member
                    if new_state == gc3libs.Run.State.TERMINATED:
                        app.job.move_jobfile("done")
                        self.apps.pop(i)
                    # pylint: enable-msg=no-member

                stats = self.engine_status()
                # NOTE: in theory, we could simply add all apps to the engine
                # and let gc3 decide when to dispatch the next one, however
                # this it is causing a lot of error messages if the engine has
                # more tasks than available resources, see ticket #421 and
                # upstream gc3pie ticket #359 for more details. For now we do
                # not submit new jobs if there are any running or submitted:
                if stats["RUNNING"] > 0 or stats["SUBMITTED"] > 0:
                    time.sleep(1)
                    continue
                nextjob = self.queue.next_job()
                if nextjob is not None:
                    logd("Current joblist: %s", self.queue.queue)
                    apptype = apptypes[nextjob["type"]]
                    logi("Adding job (type '%s') to the gc3 engine.", apptype.__name__)
                    app = apptype(nextjob, self.gc3cfg["spooldir"])
                    self.apps.append(app)
                    self.engine.add(app)
                    # as a new job is dispatched now, we also print out the
                    # human readable queue status:
                    self.queue.queue_details_hr()
            elif self.status == "shutdown":
                return True

            elif self.status == "refresh":
                # the actual refresh action is handled by the status.setter
                # method, so we simply pass on:
                pass
            elif self.status == "pause":
                # no need to do anything, just sleep and check requests again:
                pass
            time.sleep(0.5)

    def cleanup(self):
        """Clean up the spooler, terminate jobs, store status."""
        # TODO: store the current queue (see #516)
        logw("Queue Manager shutdown initiated.")
        logi("QM shutdown: cleaning up spooler.")
        if self.apps:
            logw("v%sv", "-" * 80)
            logw("Unfinished jobs, trying to stop them:")
            for app in self.apps:
                logw("Status of running job: %s", app.job["status"])
                self.kill_running_job(app)
            logw("^%s^", "-" * 80)
            self.engine.progress()
            stats = self.engine_status()
            if stats["RUNNING"] > 0:
                logc("Killing jobs failed, %s still running.", stats["RUNNING"])
            else:
                logi("Successfully terminated remaining jobs, none left.")
        self.check_gc3_resources(self.engine)
        logi("QM shutdown: spooler cleanup completed.")

    def kill_running_job(self, app):
        """Helper method to kill a running job."""
        logw("<KILLING> [%s] %s", app.job["user"], type(app).__name__)
        app.kill()
        self.engine.progress()
        state = app.status_changed()
        if state != "TERMINATED":
            loge("Expected status 'TERMINATED', found '%s'!", state)
        else:
            logw("App has terminated, removing from list of apps.")
            self.apps.remove(app)
        # TODO: clean up temporary gc3lib processing dir(s)
        #       app.kill() leaves the temporary gc3libs spooldir (files
        #       transferred for / generated from processing, logfiles
        #       etc.) alone, unfortunately the fetch_output() methods
        #       tested below do not work as suggested by the docs:
        # ## self.engine.fetch_output(app)
        # ## app.fetch_output()
        # ## self.engine.progress()
        # remove the job from the queue:
        self.queue.remove(app.job["uid"])
        # trigger an update of the queue status:
        self.queue.update_status()
        # this is just to trigger the stats messages in debug mode:
        self.engine_status()


# NOTE: if desired, we could implement other spooling methods than the
# files-and-directories based one, e.g. using a DB or JSON files for tracking
# the status. In this case, simply turn the above into an abstract spooler and
# implement the details in its derived classes, e.g.:
#
# class DirectorySpooler(JobSpooler):
#
#     def __init__(self, spool_dirs, queue, gc3conf):
#         super(DirectorySpooler, self).__init__(job, gc3_output)
