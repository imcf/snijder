"""Tests for the snijder.jobs module."""

from __future__ import print_function

import os
import glob
import pprint

import snijder.jobs
import snijder.logger

import pytest  # pylint: disable-msg=unused-import


def set_snijder_debug_logging():
    snijder.logger.set_loglevel("debug")


def test_select_queue_for_job(caplog):
    caplog.set_level("DEBUG")
    set_snijder_debug_logging()
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
    caplog.set_level("DEBUG")

    # test with an invalid source type
    caplog.clear()
    with pytest.raises(TypeError):
        snijder.jobs.SnijderJobConfigParser(jobconfig="", srctype="invalid")

    # test with an empty job configuration
    caplog.clear()
    with pytest.raises(SyntaxError):
        snijder.jobs.SnijderJobConfigParser(jobconfig="", srctype="string")
    assert "Read job configuration file / string." in caplog.text

    # locate the provided sample job configuration files:
    jobfile_path = os.path.join("tests", "snijder-queue", "jobfiles")
    jobfile_list = glob.glob(jobfile_path + '/*.cfg')
    jobfile_list.sort()
    print("Found %s job config files in [%s]." % (len(jobfile_list), jobfile_path))
    assert jobfile_list

    for jobfile in jobfile_list:
        print("----------------- parsing %s -----------------" % jobfile)
        job = snijder.jobs.JobDescription(jobfile, 'file')
        print(" - Parsing worked without errors on '%s'." % jobfile)
        pprint.pprint(job)
