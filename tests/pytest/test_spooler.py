"""Tests for the snijder.spooler module."""

from __future__ import print_function

import logging

import snijder.logger
import snijder.queue
import snijder.spooler

import pytest  # pylint: disable-msg=unused-import


def prepare_logging(caplog):
    """Helper function to set up logging appropriately."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


def test_job_spooler_constructor(caplog, tmp_path, gc3conf_path_localhost):
    """Test the JobQueue class."""
    prepare_logging(caplog)

    queue = snijder.queue.JobQueue()

    spooler = snijder.spooler.JobSpooler(str(tmp_path), queue, gc3conf_path_localhost)
    assert spooler.status == "run"
    assert spooler.apps == list()
    assert spooler.dirs.keys() == [
        "status",
        "cur",
        "curfiles",
        "newfiles",
        "done",
        "new",
        "requests",
    ]
    assert "PRE-SUBMITTED JOBS" not in caplog.text
    assert "Created JobSpooler." in caplog.text


def test_setup_rundirs(caplog, tmp_path):
    """Test the setup_rundirs() method."""
    prepare_logging(caplog)

    # test where one of the runtime directories already exists but is read-only
    caplog.clear()
    base = tmp_path / "exists_ro"
    cur_ro = base / "spool" / "cur"
    cur_ro.mkdir(parents=True)
    cur_ro.chmod(0o0500)
    logging.info(str(cur_ro))
    with pytest.raises(OSError, match="exists, but it is not writable"):
        snijder.spooler.JobSpooler.setup_rundirs(str(base))

    # test where the runtime directories can't be created
    caplog.clear()
    non_existing_ro = tmp_path / "not_there"
    non_existing_ro.mkdir(parents=True)
    non_existing_ro.chmod(0o0500)
    with pytest.raises(OSError, match="Error creating Queue Manager runtime directory"):
        snijder.spooler.JobSpooler.setup_rundirs(str(non_existing_ro))

    # test with pre-existing files in "spool/new"
    caplog.clear()
    base = tmp_path / "newfiles"
    spool_new = base / "spool" / "new"
    spool_new.mkdir(parents=True)
    fake_file_name = "not_a_real_one.jobfile"
    fake_file = spool_new / fake_file_name
    fake_file.write_text(u"empty")
    run_dirs = snijder.spooler.JobSpooler.setup_rundirs(str(base))
    assert "PRE-SUBMITTED JOBS" in caplog.text
    assert "contains files that were already submitted prior" in caplog.text
    assert "- file: %s" % fake_file_name in caplog.text
    assert run_dirs["newfiles"] == [fake_file_name]


    # test with pre-existing files in "spool/cur"
    caplog.clear()
    base = tmp_path / "curfiles"
    spool_cur = base / "spool" / "cur"
    spool_cur.mkdir(parents=True)
    fake_file_name = "not_a_real_one.jobfile"
    fake_file = spool_cur / fake_file_name
    fake_file.write_text(u"empty")
    run_dirs = snijder.spooler.JobSpooler.setup_rundirs(str(base))
    assert "PREVIOUS JOBS" in caplog.text
    assert "contains files from a previous session" in caplog.text
    assert "- file: %s" % fake_file_name in caplog.text
    assert run_dirs["curfiles"] == [fake_file_name]
