"""Tests for the snijder.spooler module."""

# pylint: disable-msg=invalid-name

from __future__ import print_function

import os
import sys
import logging

import snijder.logger
import snijder.queue
import snijder.spooler

import pytest  # pylint: disable-msg=unused-import


### FUNCTIONS ###

def prepare_logging(caplog):
    """Helper function to set up logging appropriately."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


def prepare_spooler(caplog, spooldir, gc3conf):
    """Helper function setting up a spooler instance.

    Parameters
    ----------
    caplog : pytest caplog fixture
    spooldir : str or str-like
        The spooldir to use for the spooler instance.
    gc3conf : str or str-like
        The path to the gc3 configuration file to be used.

    Returns
    -------
    snijder.spooler.JobSpooler
    """
    prepare_logging(caplog)
    queue = snijder.queue.JobQueue()
    spooler = snijder.spooler.JobSpooler(str(spooldir), queue, str(gc3conf))
    logging.info("Initialized JobSpooler")
    return spooler


### TESTS ###

def test_job_spooler_constructor(caplog, tmp_path, gc3conf_path_localhost):
    """Test the JobQueue class constructor."""
    spooler = prepare_spooler(caplog, tmp_path, gc3conf_path_localhost)
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

    caplog.clear()
    spooler.status = "run"
    assert "Received spooler status change request" not in caplog.text

    spooler.status = "pause"
    assert "Received spooler status change request" in caplog.text

    spooler.status = "refresh"
    assert "Received spooler queue status refresh request" in caplog.text


def test_job_spooler_invalid_status_request(caplog, tmp_path, gc3conf_path_localhost):
    """Test requesting an invalid status change to the spooler."""
    spooler = prepare_spooler(caplog, tmp_path, gc3conf_path_localhost)
    spooler.status = "invalid"
    assert "Invalid spooler status requested, ignoring" in caplog.text
    assert "Received spooler status change request" not in caplog.text


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


def test_check_gc3conf(caplog, tmp_path, gc3conf_with_basedir):
    """Test check_gc3conf() with a config missing the 'spooldir' entry."""
    prepare_logging(caplog)
    config = gc3conf_with_basedir(tmp_path)
    # remove the "spooldir" entry
    config = config.replace("spooldir = ", "xnospooldir = ")
    logging.debug("Generated gc3pie config without 'spooldir' entry:\n%s", config)

    gc3conf = tmp_path / "gc3conf_localhost_nospooldir.conf"
    gc3conf.write_text(config)
    logging.info("Created gc3pie config file: %s", gc3conf)

    with pytest.raises(AttributeError, match="Unable to parse spooldir for resource"):
        snijder.spooler.JobSpooler.check_gc3conf(str(gc3conf))


def test_setup_engine_and_status(caplog, tmp_path, gc3conf_with_basedir):
    """Set up a spooler with a pre-existing basedir and check the engine status."""
    snijder_basedir = tmp_path / "snijder"
    snijder_basedir.mkdir()
    logging.info("Created SNIJDER base dir: %s", snijder_basedir)
    gc3conf = snijder_basedir / "gc3conf_localhost.conf"
    gc3conf.write_text(gc3conf_with_basedir(str(snijder_basedir)))
    logging.info("Created gc3pie config file: %s", gc3conf)

    gc3resource_dir = snijder_basedir / "gc3" / "resource" / "shellcmd.d"
    assert not os.path.exists(str(gc3resource_dir))

    # now create the spooler, this will initialize the gc3 engine
    spooler = prepare_spooler(caplog, snijder_basedir, gc3conf)

    assert "Inspecting gc3pie resource files for running processes." in caplog.text
    assert os.path.exists(str(gc3resource_dir))
    assert spooler.dirs["status"].startswith(str(snijder_basedir))
    assert spooler.gc3cfg["conffile"].startswith(str(gc3conf))
    assert spooler.status == "run"

    # request the spooler's engine status, this will trigger some log messages as well
    caplog.clear()
    assert spooler.engine_status()["total"] == 0
    assert (
        "Engine: NEW:0  SUBM:0  RUN:0  TERM'ing:0  TERM'ed:0  "
        "UNKNWN:0  STOP:0  (total:0)"
    ) in caplog.text


def test_setup_engine_unclean_resourcedir(caplog, tmp_path, gc3conf_with_basedir):
    """Test setting up a spooler with an unclean gc3resource_dir."""
    snijder_basedir = tmp_path / "snijder"
    snijder_basedir.mkdir()
    logging.info("Created SNIJDER base dir: %s", snijder_basedir)
    gc3conf = snijder_basedir / "gc3conf_localhost.conf"
    gc3conf.write_text(gc3conf_with_basedir(str(snijder_basedir)))
    logging.info("Created gc3pie config file: %s", gc3conf)

    gc3resource_dir = snijder_basedir / "gc3" / "resource" / "shellcmd.d"
    assert not os.path.exists(str(gc3resource_dir))
    gc3resource_dir.mkdir(parents=True)
    assert os.path.exists(str(gc3resource_dir))

    # create a fake PID file using *our* PID (i.e. the one of the pytest process)
    fake_pid_file = gc3resource_dir / str(os.getpid())
    fake_pid_file.touch()

    # create a non-PID file
    non_pid_file = gc3resource_dir / "this-should-not-be-a-valid-PID"
    non_pid_file.touch()

    # create a PID file with a value that (hopefully) doesn't correspond to a valid PID
    negative_pid_file = gc3resource_dir / str(sys.maxint)
    negative_pid_file.touch()

    # now create the spooler, this will initialize the gc3 engine
    prepare_spooler(caplog, snijder_basedir, gc3conf)
    assert "Resource dir unclean" in caplog.text
    assert "Inspecting gc3pie resource files for running processes." in caplog.text
    assert "Process matching resource pid '%s' found" % str(os.getpid()) in caplog.text
    assert "No running process matching pid" in caplog.text
    assert "doesn't seem to be from an existing gc3 job" in caplog.text
