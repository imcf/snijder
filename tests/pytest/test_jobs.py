"""Tests for the snijder.jobs module."""

# pylint: disable-msg=invalid-name

from __future__ import print_function

import os
import glob
import pprint

import snijder.jobs
import snijder.logger
import snijder.spooler

import pytest  # pylint: disable-msg=unused-import


def prepare_logging(caplog):
    """Helper function to set up logging appropriately."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


def test_select_queue_for_job(caplog):
    """Test the select_queue_for_job function."""
    prepare_logging(caplog)
    print("testing select_queue_for_job()...")

    caplog.clear()
    fake_job = {"type": "UNKNOWN_JOBTYPE"}
    assert snijder.jobs.select_queue_for_job(fake_job) is None
    assert "No queue found for jobtype" in caplog.text

    caplog.clear()
    fake_job = {"type": "dummy", "tasktype": "UNKNOWN_TASKTYPE"}
    assert snijder.jobs.select_queue_for_job(fake_job) is None
    assert "No queue found for tasktype" in caplog.text

    caplog.clear()
    fake_job = {"type": "dummy", "tasktype": "sleep"}
    assert snijder.jobs.select_queue_for_job(fake_job) == "hucore"
    assert "Selected queue for jobtype" in caplog.text


def test_snijder_job_config_parser(caplog):
    """Test the SnijderJobConfigParser constructor."""
    prepare_logging(caplog)

    # test with an invalid source type
    caplog.clear()
    with pytest.raises(TypeError):
        snijder.jobs.SnijderJobConfigParser(jobconfig="", srctype="invalid")

    # test with an empty job configuration
    caplog.clear()
    with pytest.raises(SyntaxError):
        snijder.jobs.SnijderJobConfigParser(jobconfig="", srctype="string")
    assert "Read job configuration file / string." in caplog.text


def test_snijder_job_config_parser_valid_jobfiles(caplog):
    """Test parsing the valid job configuration files."""
    prepare_logging(caplog)

    # locate the provided sample job configuration files:
    jobfile_path = os.path.join("tests", "snijder-queue", "jobfiles")
    jobfile_list = glob.glob(jobfile_path + "/*.cfg")
    jobfile_list.sort()
    print("Found %s job config files in [%s]." % (len(jobfile_list), jobfile_path))
    assert jobfile_list

    # test parsing the job configuration files
    for jobfile in jobfile_list:
        caplog.clear()
        job = snijder.jobs.JobDescription(jobfile, "file")
        assert "Finished initialization of JobDescription" in caplog.text
        # print(" - Parsing worked without errors on '%s'." % jobfile)
        pprint.pprint(job)


def test_snijder_job_config_parser_invalid_jobfiles(caplog):
    """Test parsing the INVALID job configuration files."""
    prepare_logging(caplog)

    # locate the provided sample job configuration files:
    jobfile_path = os.path.join("tests", "resources", "jobfiles", "invalid")
    jobfile_list = glob.glob(jobfile_path + "/*.cfg")
    jobfile_list.sort()
    print("Found %s job config files in [%s]." % (len(jobfile_list), jobfile_path))
    assert jobfile_list

    # test parsing the invalid job configuration files
    error_messages = [
        "Section '.*' missing in job config!",
        "Option '.*' missing from section '.*'!",
        "Job config invalid, section '.*' contains unknown options:",
        "No input files defined in job config.",
        "Invalid timestamp: on_parse.",
        "Can't find job IDs in job config!",
        "Unexpected jobfile version",
        "Unknown jobtype",
        "Tasktype invalid",
        "No 'deletejobs' section in job config!",
    ]
    match = "(" + "|".join(error_messages) + ")"
    print(match)
    for jobfile in jobfile_list:
        caplog.clear()
        print(jobfile)
        with pytest.raises(ValueError, match=match):
            snijder.jobs.JobDescription(jobfile, "file")
        assert "Ignoring job config, parsing failed" in caplog.text
        assert "Invalid job config file" in caplog.text

    # test with a job configuration file not following the ini-style syntax:
    caplog.clear()
    with pytest.raises(SyntaxError, match="ERROR in JobDescription"):
        snijder.jobs.SnijderJobConfigParser(jobconfig="no-header", srctype="string")


def test_snijder_job_config_parser__read_jobfile(caplog, tmpdir):
    """Test the read_jobfile static method."""
    prepare_logging(caplog)

    # test with an invalid path for the job configuration file
    caplog.clear()
    jobfile = os.path.join(str(tmpdir), "non-existing-subdirectory", "job_file")
    with pytest.raises(IOError):
        snijder.jobs.SnijderJobConfigParser.read_jobfile(jobfile)
    assert "Full jobfile path:" in caplog.text

    # test with a job configuration file lacking file-system level read permissions
    caplog.clear()
    jobfile = tmpdir.join("snijder-unreadable-jobfile")
    print(jobfile)
    jobfile.write("[invalid]")  # put something into the file
    jobfile.chmod(0o0000)  # make file read-only
    with pytest.raises(IOError):
        snijder.jobs.SnijderJobConfigParser.read_jobfile(str(jobfile))
    jobfile.chmod(0o0600)  # restore read-write permissions
    assert str(jobfile) in caplog.text
    assert "Full jobfile path:" in caplog.text

    # test with an empty job configuration file
    caplog.clear()
    jobfile = tmpdir.join("snijder-empty-jobfile")
    jobfile.write("")  # put an empty string into the file to create it
    print(jobfile)
    with pytest.raises(IOError, match="Unable to read job config file"):
        snijder.jobs.SnijderJobConfigParser.read_jobfile(str(jobfile))
    assert str(jobfile) in caplog.text
    assert "Full jobfile path:" in caplog.text


def test_job_description(caplog, jobcfg_valid_delete):
    """Test the JobDescription class."""
    prepare_logging(caplog)

    job = snijder.jobs.JobDescription(jobcfg_valid_delete, srctype="string")

    caplog.clear()
    job["status"] = "changed"
    assert "Setting JobDescription" in caplog.text

    caplog.clear()
    job["type"] = "deletejobs"
    assert "Setting JobDescription" not in caplog.text


def test_job_description__get_category(caplog, jobcfg_valid_delete):
    """Test the JobDescription.get_category method."""
    prepare_logging(caplog)

    job = snijder.jobs.JobDescription(jobcfg_valid_delete, srctype="string")
    assert job.get_category() == job["user"]


def test_job_description__move_jobfile(caplog, tmp_path, jobcfg_valid_delete):
    """Test the JobDescription.move_jobfile() method."""
    prepare_logging(caplog)

    caplog.clear()
    job = snijder.jobs.JobDescription(jobcfg_valid_delete, srctype="string")
    assert job.fname is None
    assert "Finished initialization of JobDescription()." in caplog.text

    caplog.clear()
    job.move_jobfile(target="")
    assert "move_jobfile() doesn't make sense" in caplog.text

    # set up the spooldirs class variable
    caplog.clear()
    print("Using spooling directory: %s" % tmp_path)
    spooldirs = snijder.spooler.JobSpooler.setup_rundirs(str(tmp_path))
    assert "Created spool directory" in caplog.text
    print(spooldirs)
    snijder.jobs.JobDescription.spooldirs = spooldirs

    # create a job config file, parse it into a job object and call move_jobfile()
    caplog.clear()
    cfgfile = tmp_path / "jobfile.cfg"
    cfgfile.write_text(jobcfg_valid_delete)
    print("Created job config file for testing: %s" % str(cfgfile))
    job = snijder.jobs.JobDescription(str(cfgfile), srctype="file")
    assert "Finished initialization of JobDescription()." in caplog.text
    caplog.clear()
    job.move_jobfile("cur")
    assert "Moved job file" in caplog.text
    assert "/cur/" in caplog.text
    assert "Adding suffix to prevent overwriting file" not in caplog.text

    # now create the same jobfile again and try to move it once more:
    caplog.clear()
    cfgfile = tmp_path / "jobfile.cfg"
    cfgfile.write_text(jobcfg_valid_delete)
    print("Created job config file (again) for testing: %s" % str(cfgfile))
    job = snijder.jobs.JobDescription(str(cfgfile), srctype="file")
    assert "Finished initialization of JobDescription()." in caplog.text
    caplog.clear()
    job.move_jobfile("cur")
    assert "Moved job file" in caplog.text
    assert "/cur/" in caplog.text
    assert "Adding suffix to prevent overwriting file" in caplog.text


def test_abstract_job_config_parser(caplog, jobcfg_valid_delete):
    """Test the AbstractJobConfigParser class."""
    prepare_logging(caplog)

    caplog.clear()
    with pytest.raises(NotImplementedError, match="This is an abstract class"):
        snijder.jobs.AbstractJobConfigParser(jobcfg_valid_delete, srctype="string")
    assert "Read job configuration file / string." in caplog.text
    assert "Job description sections" in caplog.text
