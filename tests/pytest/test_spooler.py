"""Tests for the snijder.spooler module."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=len-as-condition

# 'black' has priority over 'pylint:
# pylint: disable-msg=bad-continuation

from __future__ import print_function

import os
import sys
import time
import logging
import shutil

import snijder.logger
import snijder.queue
import snijder.spooler
import snijder.cmdline

import pathlib2

import pytest  # pylint: disable-msg=unused-import


### FUNCTIONS ###


def prepare_spooler(spooldir, gc3conf):
    """Helper function setting up a spooler instance.

    Parameters
    ----------
    spooldir : str or str-like
        The spooldir to use for the spooler instance.
    gc3conf : str or str-like
        The path to the gc3 configuration file to be used.

    Returns
    -------
    snijder.spooler.JobSpooler
    """
    queue = snijder.queue.JobQueue()
    spooler = snijder.spooler.JobSpooler(str(spooldir), queue, str(gc3conf))
    logging.info("Initialized JobSpooler")
    return spooler


def prepare_basedir_and_gc3conf(basedir, gc3conf_generator):
    """Helper function to prepare the SNIJDER basedir and a gc3 config file.

    The `basedir`, a sub-directory called `snijder` will be created and a gc3pie config
    file called `gc3pie_configuration.conf` will be placed therein.

    Parameters
    ----------
    basedir : Pathlib
        The path to be used for the basedir, this is intended to be used with the pytest
        fixture `tmp_path`.
    gc3conf_generator : function
        The function to be called for generating the gc3pie configuration.

    Returns
    -------
    (Pathlib, Pathlib)
        A tuple of Pathlib objects, the first being the `snijder_basedir` and the second
        being the `gc3conf`.
    """
    snijder_basedir = basedir / "snijder"
    snijder_basedir.mkdir()
    logging.info("Created SNIJDER base dir: %s", snijder_basedir)
    gc3conf = snijder_basedir / "gc3pie_configuration.conf"
    gc3conf.write_text(gc3conf_generator(str(snijder_basedir)))
    logging.info("Created gc3pie config file: %s", gc3conf)
    return (snijder_basedir, gc3conf)


def message_timeout(caplog, log_message, desc, timeout=0.005, sleep_for=0.000001):
    """Helper to wait for a specific log message for a given timeout.

    This helper is repeatedly checking the log for a message to show up before the given
    `timeout` has been reached, using a fixed delay between the subsequent checks.

    Parameters
    ----------
    caplog : pytest fixture
    log_message : str
        The log message to wait for.
    desc : str
        A description to use in this function's own log messages. MUST NOT be a
        substring of `log_message` as otherwise it will render the check useless!
    timeout : float, optional
        The maximum amount of time in seconds to wait for the log message to appear, by
        default 0.005.
    sleep_for : float, optional
        The amount of time that should be waited between two attempts of checking the
        log messages, by default 0.000001

    Returns
    -------
    bool
        True if the log message was found within the given timeout, False otherwise.
    """
    if desc in log_message:
        logging.error("Description MUST NOT be a substring of the log message!")
        desc = "FIX TEST DESCRIPTION"

    found_message = False
    elapsed_time = 0.0
    max_attempts = int(timeout / sleep_for)
    logging.warning("Waiting (<%s cycles) for %s log message.", max_attempts, desc)
    for i in range(max_attempts):
        if log_message in caplog.text:
            found_message = True
            elapsed_time = i * sleep_for
            logging.warning("Found %s log message after %.6fs", desc, elapsed_time)
            break
        # logging.debug("Log message not found, sleeping...")
        time.sleep(sleep_for)

    return found_message


def queue_length_timeout(queue, expected_length, timeout=0.1, sleep_for=0.000001):
    """Helper to wait for the queue to have a given length for a given timeout.

    This is useful when submitting a job with the `on_parsing` flag multiple times to
    the same queue, as sometimtes parsing and enqueueing is too fast and one of the
    subsequent submissions would be ignored as it has the same UID as one of the already
    enqueued jobs. This function waits for the queue to reach the expected length, but
    not longer than necessary.

    Parameters
    ----------
    queue : snijder.queue.JobQueue
        The spooler queue object to check.
    expected_length : int
        The expected number of jobs queued (queue length).
    timeout : float, optional
        The maximum amount of time in seconds to wait for the queue to reach the given
        length, by default 0.1.
    sleep_for : float, optional
        The amount of time that should be waited between two attempts of checking the
        current queue length, by default 0.000001.

    Returns
    -------
    bool
        True if the queue has reached the length within the timeout, False otherwise.
    """
    length_matching = False
    elapsed_time = 0.0
    max_attempts = int(timeout / sleep_for)
    logging.warning(
        "Waiting (<%s cycles of %.8fs) for queue to have length %s.",
        max_attempts,
        sleep_for,
        expected_length,
    )
    for i in range(max_attempts):
        if queue.num_jobs_queued() == expected_length:
            length_matching = True
            elapsed_time = i * sleep_for
            logging.warning(
                "Queue length matching %s after %.8fs (%s cycles)",
                expected_length,
                elapsed_time,
                i,
            )
            break
        time.sleep(sleep_for)

    return length_matching


def log_thread(thread, description):
    """Log a message about the status of a background thread.

    Parameters
    ----------
    thread : threading.Thread
        The thread to check if it's alive.
    description : str
        The description to use for the status in the log message.
    """
    status = "running"
    if not thread.is_alive():
        status = "STOPPED"
    logging.debug("Status of background thread (%s): %s", description, status)


def create_request_file(spooler, request):
    """Helper to create a spooler request file.

    Parameters
    ----------
    spooler : snijder.spooler.JobSpooler
        The spooler instance to communicate with.
    request : str
        A valid status request string.
    """
    request_file = pathlib2.Path(spooler.dirs["requests"]) / request
    request_file.touch()
    logging.debug("Created request file [%s]", request_file)


def queue_is_empty(spooler, timeout=0):
    """Helper function to check if the queue(s) of a spooler are empty.

    When the `timeout` parameter is omitted, a single check is performed only. If a
    `timeout` has been specified, the queue is checked repeatedly (with a delay of
    0.005 seconds) and the function returns `True` as soon as the queue is empty. In
    case the queue is still not empty after the `timeout` has elapsed, it returns
    `False`.

    Parameters
    ----------
    spooler : snijder.spooler.JobSpooler
        The spooler instance to check.
    timeout : float
        The maximum amount of time to wait until the queue is empty.
    """
    elapsed = 0.0
    sleep_for = 0.005
    max_attempts = int(timeout / sleep_for)
    logging.warning("Waiting (<%s cycles) for queue to be empty.", max_attempts)
    for i in range(max_attempts):
        if len(spooler.queue) == 0:
            elapsed = i * sleep_for
            logging.warning("Queue empty after %.3fs", elapsed)
            return True
        time.sleep(sleep_for)

    return len(spooler.queue) == 0


def submit_jobfile(spooler, jobfile):
    """Submit a job file to a spooler.

    Copy a given job file to the incoming spooling directory ("new") to submit it to a
    running spooler / queue.

    Parameters
    ----------
    spooler : snijder.spooler.JobSpooler
        The spooler instance to which the job file should be submitted to.
    jobfile : str
        The path to the job description file.

    Returns
    -------
    str
        The file name (full path) of the submitted job file.
    """
    new_dir = spooler.dirs["new"]
    logging.debug("Submitting [%s] to [%s]...", jobfile, new_dir)
    dest = os.path.basename(jobfile)
    dest = os.path.join(new_dir, dest)
    shutil.copy2(jobfile, dest)
    logging.debug("Copied jobfile to [%s].", dest)
    return dest


def submit_jobconfig(spooler, jobcfg, tmp_path):
    """Submit a job configuration string as a file to a spooler instance.

    Write the given job configuration into a file and submit it to the incoming spooling
    directory ("new") of a running spooler / queue.

    Parameters
    ----------
    spooler : snijder.spooler.JobSpooler
        The spooler instance to which the job file should be submitted to.
    jobcfg : str
        The job configuration as a string.
    tmp_path : Pathlib
        The path to a temporary (writable) directory, intended to be used with the
        pytest `tmp_path` fixture.

    Returns
    -------
    str
        The file name (full path) of the submitted job file.
    """
    jobfile = tmp_path / "jobfile.cfg"
    jobfile.write_text(jobcfg)
    dest = submit_jobfile(spooler, (str(jobfile)))

    return dest


### TESTS ###


def test_job_spooler_constructor(caplog, tmp_path, gc3conf_with_basedir):
    """Test the JobQueue class constructor."""
    _, gc3conf = prepare_basedir_and_gc3conf(tmp_path, gc3conf_with_basedir)
    spooler = prepare_spooler(tmp_path, gc3conf)
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


def test_job_spooler_invalid_status_request(caplog, tmp_path, gc3conf_with_basedir):
    """Test requesting an invalid status change to the spooler."""
    _, gc3conf = prepare_basedir_and_gc3conf(tmp_path, gc3conf_with_basedir)
    spooler = prepare_spooler(tmp_path, gc3conf)
    spooler.status = "invalid"
    assert "Invalid spooler status requested, ignoring" in caplog.text
    assert "Received spooler status change request" not in caplog.text


def test_setup_rundirs(caplog, tmp_path):
    """Test the setup_rundirs() method."""

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


def test_check_gc3conf(tmp_path, gc3conf_with_basedir):
    """Test check_gc3conf() with a config missing the 'spooldir' entry."""
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
    spooler = prepare_spooler(snijder_basedir, gc3conf)

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
    basedir, gc3conf = prepare_basedir_and_gc3conf(tmp_path, gc3conf_with_basedir)

    gc3resource_dir = basedir / "gc3" / "resource" / "shellcmd.d"
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
    prepare_spooler(basedir, gc3conf)
    assert "Resource dir unclean" in caplog.text
    assert "Inspecting gc3pie resource files for running processes." in caplog.text
    assert "Found process matching [pid:%s]" % str(os.getpid()) in caplog.text
    assert "No process found matching [pid:" in caplog.text
    assert "Removing file not related to a gc3 job: [file:" in caplog.text


def test_spooling_thread(caplog, snijder_spooler):
    """Start a spooler thread, check if it's alive, request a shutdown.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
    - check if the spooler has started spooling
    - request the spooler to shut down
    - check if shutdown succeeded
    """
    # # to check for any log message issued during startup use the following code:
    # caplog_setup = ""
    # for log in caplog.get_records(when="setup"):
    #     caplog_setup += log.getMessage()
    # assert "Creating GC3Pie engine using config file" in caplog_setup

    ### start spooling in a background thread
    snijder_spooler.thread.start()

    ### check if the spooler is spooling
    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    ### request spooler to shut down
    caplog.clear()
    log_thread(snijder_spooler.thread, "pre-join")
    snijder_spooler.spooler.shutdown()
    # wait max 2 seconds for the spooling thread to terminate:
    snijder_spooler.thread.join(timeout=2)

    ### check if the spooler shutdown succeeded
    log_thread(snijder_spooler.thread, "post-join")
    # with the thread-join above, the log message should be found immediately:
    assert message_timeout(caplog, "spooler cleanup completed", "spooler shutdown")
    log_thread(snijder_spooler.thread, "post-shutdown")
    assert not snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "shutdown"


def test_check_status_request(caplog, snijder_spooler):
    """Start a spooler thread and request a status change through a request-file.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
    - check if the spooler has started spooling
    - create request files to change the spooler status
        - "run" to "pause"
        - back from "pause" to "run"
        - request a "refresh" (will not change the status)
        - spooler "shutdown"
    - check if shutdown succeeded

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-001__startup-pause-run-shutdown.sh
    - tests/snijder-queue/test-002__shutdown-on-empty-queue.sh
    """
    ### start spooling in a background thread
    snijder_spooler.thread.start()

    ### check if the spooler is spooling
    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    ### create a request file switching to "pause" mode
    caplog.clear()
    create_request_file(snijder_spooler.spooler, "pause")
    assert message_timeout(caplog, "request: run -> pause", "pause request", 2)
    assert snijder_spooler.spooler.status == "pause"

    ### create a request file switching back to "run" mode
    caplog.clear()
    create_request_file(snijder_spooler.spooler, "run")
    assert message_timeout(caplog, "request: pause -> run", "run request", 2)
    assert snijder_spooler.spooler.status == "run"

    ### create a request file to "refresh" the queue status
    caplog.clear()
    create_request_file(snijder_spooler.spooler, "refresh")
    assert message_timeout(caplog, "status refresh request", "refresh status", 2)
    assert snijder_spooler.spooler.status == "run"

    ### create a request file to shut down the spooler
    caplog.clear()
    assert queue_is_empty(snijder_spooler.spooler)
    create_request_file(snijder_spooler.spooler, "shutdown")
    assert message_timeout(caplog, "request: run -> shutdown", "shutdown request", 2)
    # wait max 2 seconds for the spooling thread to terminate:
    snijder_spooler.thread.join(timeout=2)

    ### check if the spooler shutdown succeeded
    log_thread(snijder_spooler.thread, "post-join")
    # with the thread-join above, the log message should be found immediately:
    assert message_timeout(caplog, "spooler cleanup completed", "spooler shutdown")
    log_thread(snijder_spooler.thread, "post-shutdown")
    assert not snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "shutdown"


@pytest.mark.runjobs
def test_sleep_job(caplog, snijder_spooler, jobfile_valid_sleep):
    """Start a spooler thread and run a sleep job.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - switch spooler to "pause" mode
        - submit a sleep job
        - switch spooler to "run" mode
        - wait (just a couple of seconds) for spooler to complete the sleep job
        - spooler "shutdown"
    - check if shutdown succeeded

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-010__dummy-sleep-job.sh
    """
    ### start spooling in a background thread
    snijder_spooler.thread.start()

    ### check if the spooler is spooling
    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    snijder_spooler.spooler.pause()
    assert message_timeout(caplog, "request: run -> pause", "pause request", 2)

    queues = {"hucore": snijder_spooler.spooler.queue}
    dest = submit_jobfile(snijder_spooler.spooler, jobfile_valid_sleep)
    snijder.cmdline.process_jobfile(dest, queues)
    assert "Error reading job description file" not in caplog.text
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 1

    snijder_spooler.spooler.run()
    assert message_timeout(caplog, "request: pause -> run", "run request", 2)
    assert message_timeout(caplog, "Retrieving next job", "job selection", 2)
    assert message_timeout(caplog, "Adding job (type 'DummySleepApp')", "dispatch", 0.5)
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 1

    assert message_timeout(caplog, "'NEW' -> 'SUBMITTED'", "job submission", 2)
    assert message_timeout(caplog, "'SUBMITTED' -> 'RUNNING'", "job execution", 2)

    assert message_timeout(caplog, "'RUNNING' -> 'TERMINATING'", "job termination", 2)
    assert queue_is_empty(snijder_spooler.spooler, 2)

    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "shutdown request", 2)
    assert message_timeout(caplog, "spooler cleanup completed", "shutdown complete", 2)


@pytest.mark.runjobs
def test_remove_nonexisting_job(caplog, snijder_spooler, jobfile_valid_delete):
    """Start a spooler thread an submit a deletion request for a non-existing job.

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-011__remove-non-existing-job.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()

    queues = {"hucore": snijder_spooler.spooler.queue}
    dest = submit_jobfile(snijder_spooler.spooler, jobfile_valid_delete)
    snijder.cmdline.process_jobfile(dest, queues)
    assert "Error reading job description file" not in caplog.text
    assert message_timeout(caplog, "Received job deletion", "deletion-request", 0.1)

    assert message_timeout(
        caplog, "Trying to remove job", "request-processing", timeout=2, sleep_for=0.1
    )
    assert message_timeout(
        caplog,
        "Job not found, discarding the request",
        "request being discarded",
        timeout=2,
        sleep_for=0.1,
    )


@pytest.mark.runjobs
def test_multiple_decon_jobs(caplog, snijder_spooler, jobfile_valid_decon_user01):
    """Start a spooler thread and submit multiple deconvolution jobs.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - switch spooler to "pause" mode
        - submit three deconvolution jobs
        - switch spooler to "run" mode
        - check spooler to process the jobs, allowing up to 60s per job
        - check if queues are empty, then shutdown the spooler
    - check if shutdown succeeded

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-003__3-decon-jobs.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    ### switch spooler to "pause" for submitting the jobs
    snijder_spooler.spooler.pause()
    assert message_timeout(caplog, "request: run -> pause", "pause request", 2)

    queues = {"hucore": snijder_spooler.spooler.queue}

    # submit 3 jobs (actually the same job 3 times, using the "on_parsing" flag)
    for num_job in range(3):
        dest = submit_jobfile(snijder_spooler.spooler, jobfile_valid_decon_user01)
        snijder.cmdline.process_jobfile(dest, queues)
        assert queue_length_timeout(snijder_spooler.spooler.queue, num_job + 1)

    assert "Error reading job description file" not in caplog.text
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 0

    ### switch to "run", then check the jobs processing
    snijder_spooler.spooler.run()
    for num_jobs_queued in [2, 1, 0]:
        assert message_timeout(caplog, "Adding job (type 'HuDeconApp')", "dispatch", 2)
        assert message_timeout(caplog, "Instantiating a HuDeconApp", "app-instance", 2)
        assert snijder_spooler.spooler.queue.num_jobs_queued() == num_jobs_queued
        assert snijder_spooler.spooler.queue.num_jobs_processing() == 1

        assert message_timeout(caplog, "'NEW' -> 'SUBMITTED'", "job submission", 2)
        assert message_timeout(caplog, "'SUBMITTED' -> 'RUNNING'", "job execution", 2)

        # now is the "safest" point to clear the captured logs as the current step is
        # supposed to take multiple seconds (so it is less likely to clear log messages
        # that we are expecting later on)
        caplog.clear()

        # give the job up to 60 seconds to complete:
        assert message_timeout(caplog, "-> 'TERMINATING'", "job termination", 60, 0.2)
        assert message_timeout(caplog, "terminated successfully", "job success", 1)
        assert message_timeout(caplog, "to be removed: TERMINATED", "job cleanup", 1)

    ### check for empty queues
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 0
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 0

    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "shutdown request", 2)
    assert message_timeout(caplog, "spooler cleanup completed", "shutdown complete", 2)


@pytest.mark.runjobs
def test_killing_decon_jobs_at_3s(
    caplog, snijder_spooler, jobfile_valid_decon_user01_long_fixedts
):
    """Start a spooler thread, submit a long-running job and kill it after 3 seconds.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - switch spooler to "pause" mode
        - submit a long-running deconvolution job
        - switch spooler to "run" mode
        - wait for 3 seconds
        - request the spooler to shut down while the job is still running

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-004__decon-job-long_kill-at-3s.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    ### switch spooler to "pause" for submitting the jobs
    snijder_spooler.spooler.pause()
    assert message_timeout(caplog, "request: run -> pause", "pause request", 2, 0.01)

    queues = {"hucore": snijder_spooler.spooler.queue}

    dest = submit_jobfile(
        snijder_spooler.spooler, jobfile_valid_decon_user01_long_fixedts
    )
    snijder.cmdline.process_jobfile(dest, queues)

    assert "Error reading job description file" not in caplog.text
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 1
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 0

    ### switch to "run", then check the job
    snijder_spooler.spooler.run()
    assert message_timeout(caplog, "Adding job (type 'HuDeconApp')", "dispatch", 2, 0.1)
    assert message_timeout(caplog, "Instantiating a HuDeconApp", "app-instance", 2, 0.1)
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 0
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 1

    assert message_timeout(caplog, "'NEW' -> 'SUBMITTED'", "job submission", 2, 0.01)
    assert message_timeout(caplog, "'SUBMITTED' -> 'RUNNING'", "job execution", 2, 0.01)

    ### wait for 3 seconds
    time.sleep(3)

    ### request the spooler to shut down while the job is still running
    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "stop-request", 2, 0.1)
    assert message_timeout(caplog, "shutdown initiated", "shutdown-start", 1, 0.01)
    assert message_timeout(caplog, "Unfinished jobs", "remaining jobs", 0.1, 0.01)
    assert message_timeout(caplog, "<KILLING> [user01] HuDeconApp", "app-kill")
    assert message_timeout(caplog, "'RUNNING' -> 'TERMINATED'", "job-status", 2, 0.01)
    assert queue_is_empty(snijder_spooler.spooler)

    assert message_timeout(
        caplog,
        "Successfully terminated remaining jobs, none left.",
        "cleanup-success",
        2,
        0.01,
    )

    assert message_timeout(caplog, "spooler cleanup completed", "stop-complete", 2, 0.1)


@pytest.mark.runjobs
def test_add_remove_job(
    caplog,
    snijder_spooler,
    jobfile_valid_decon_user01_long_fixedts,
    jobfile_valid_delete,
):
    """Start a spooler thread, submit a job and deletion request for the same job.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - switch spooler to "pause" mode
        - submit a long-running deconvolution job
        - submit a deletion request for the previously submitted deconvolution job
        - switch spooler to "run" mode
        - check if the job is removed from the queue
        - request the spooler to shut down

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-008__add-and-remove-decon-job.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()

    ### switch spooler to "pause" for submitting the jobs
    snijder_spooler.spooler.pause()
    assert message_timeout(caplog, "request: run -> pause", "pause request", 2, 0.01)

    queues = {"hucore": snijder_spooler.spooler.queue}

    dest = submit_jobfile(
        snijder_spooler.spooler, jobfile_valid_decon_user01_long_fixedts
    )
    snijder.cmdline.process_jobfile(dest, queues)

    dest = submit_jobfile(snijder_spooler.spooler, jobfile_valid_delete)
    snijder.cmdline.process_jobfile(dest, queues)

    assert "Error reading job description file" not in caplog.text
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 1
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 0

    ### switch to "run", then check if the job got removed
    snijder_spooler.spooler.run()
    assert message_timeout(caplog, "Received a deletion request", "del-request", 0.5)
    assert queue_is_empty(snijder_spooler.spooler, timeout=0.1)

    ### request the spooler to shut down
    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "stop-request", 1, 0.1)
    assert message_timeout(caplog, "spooler cleanup completed", "stop-complete", 2, 0.1)


@pytest.mark.runjobs
def test_remove_running_job(
    caplog,
    snijder_spooler,
    jobfile_valid_decon_user01_long_fixedts,
    jobfile_valid_delete,
):
    """Start a spooler thread, submit a job and a deletion request after 2 seconds.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - submit a long-running deconvolution job
        - wait for 2 seconds
        - check if the job is being processed
        - submit a deletion request for the previously submitted deconvolution job
        - check if the job is removed from the queue and cleaned up
        - request the spooler to shut down

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-009__remove-running.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()

    queues = {"hucore": snijder_spooler.spooler.queue}

    dest = submit_jobfile(
        snijder_spooler.spooler, jobfile_valid_decon_user01_long_fixedts
    )
    snijder.cmdline.process_jobfile(dest, queues)

    assert message_timeout(caplog, "Instantiating a HuDeconApp", "job-start", 2, 0.1)
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 0
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 1
    logging.warning("job is processing...")
    time.sleep(1.1)

    logging.warning("submitting deletion request")
    dest = submit_jobfile(snijder_spooler.spooler, jobfile_valid_delete)
    snijder.cmdline.process_jobfile(dest, queues)

    assert message_timeout(caplog, "job deletion request", "del-request", 0.5, 0.01)
    assert message_timeout(caplog, "was killed or crahsed", "job-kill", 2, 0.01)
    assert message_timeout(caplog, "App has terminated", "app-termination", 0.5, 0.01)
    assert queue_is_empty(snijder_spooler.spooler, timeout=0.1)

    ### request the spooler to shut down
    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "stop-request", 1, 0.1)
    assert message_timeout(caplog, "spooler cleanup completed", "stop-complete", 2, 0.1)

    ### spooler should clean up the gc3 resource dir
    assert message_timeout(caplog, "Resource dir unclean", "unclean-resource", 2, 0.01)
    assert message_timeout(caplog, "No process found matching", "no-process", 0.5, 0.01)
    assert message_timeout(caplog, "Removing file not related", "file removal", 1, 0.01)


@pytest.mark.runjobs
def test_job_with_missing_data(caplog, snijder_spooler, jobcfg_missingdata, tmp_path):
    """Start a spooler thread, submit a job with missing input data.

    This test is doing the following tasks:
    - start a spooling instance in a background thread
        - submit a job config referencing some missing input data
        - check if the broken job gets removed from the queue (currently IT DOESN'T!)
        - request the spooler to shut down

    TODO: this needs to be adapted once issue #1 is fixed (meaning gc3pie is not longer
    silencing the exception and putting snijder into blind flight mode...)

    Replaces / supersedes the following old-style shell-based tests:
    - tests/snijder-queue/test-012__valid-jobfile-but-missing-data.sh
    """
    snijder_spooler.thread.start()

    assert message_timeout(caplog, "SNIJDER spooler started", "spooler startup")
    assert snijder_spooler.thread.is_alive()
    assert snijder_spooler.spooler.status == "run"

    queues = {"hucore": snijder_spooler.spooler.queue}

    logging.warning("submitting job with missing data")
    dest = submit_jobconfig(snijder_spooler.spooler, jobcfg_missingdata, tmp_path)
    snijder.cmdline.process_jobfile(dest, queues)

    assert message_timeout(caplog, "Instantiating a HuDeconApp", "job-start", 2, 0.1)
    assert snijder_spooler.spooler.queue.num_jobs_queued() == 0
    assert snijder_spooler.spooler.queue.num_jobs_processing() == 1
    logging.warning("job is processing...")
    time.sleep(3.1)

    # NOTE: this unfortunately is the current behaviour of gc3pie, it is logging a
    # message only, but not passing up the exception - so all we can do for now is to
    # watch the log output (relates to snijder issue #1)
    assert message_timeout(
        caplog, "UnrecoverableDataStagingError", "data-staging-error", 0.5, 0.01
    )

    ### request the spooler to shut down
    snijder_spooler.spooler.shutdown()
    assert message_timeout(caplog, "request: run -> shutdown", "stop-request", 1, 0.1)
    assert message_timeout(caplog, "spooler cleanup completed", "stop-complete", 2, 0.1)

    ### spooler should clean up the gc3 resource dir
    assert message_timeout(caplog, "Resource dir is clean", "clean-resource", 2, 0.01)
