"""Tests for the snijder.jobs module."""

from __future__ import print_function

import os
import glob
import pprint

import snijder.jobs
import snijder.logger

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
