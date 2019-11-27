"""Tests for the snijder.queue module."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=len-as-condition

from __future__ import print_function

import logging

import snijder.queue
import snijder.logger
import snijder.jobs

import pytest  # pylint: disable-msg=unused-import


def prepare_logging(caplog):
    """Helper function to set up logging appropriately."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


def test_job_queue(caplog):
    """Test the JobQueue class."""
    prepare_logging(caplog)
    print("Test the JobQueue class...")

    caplog.clear()
    queue = snijder.queue.JobQueue()
    assert len(queue) == 0
    assert "num_jobs_processing" in caplog.text
    assert "num_jobs_queued" in caplog.text
    assert "len(JobQueue)" in caplog.text

    # `statusfile` hasn't been set yet, so it should be `None`
    assert queue.statusfile is None

    # queue is empty, so next_job() should return `None`
    assert queue.next_job() is None


def test_job_queue_append_nextjob_remove(caplog, jobfile_valid_decon_fixedtimestamp):
    """Test the append(), next_job() and remove() methods."""
    prepare_logging(caplog)
    print("Test the JobQueue class...")

    # create the queue
    queue = snijder.queue.JobQueue()

    # parse the jobfile and append the job to the queue
    caplog.clear()
    job_fixed = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    print(job_fixed["uid"])
    queue.append(job_fixed)
    assert "Adding a new queue" in caplog.text
    assert "Setting JobDescription 'status' to 'queued'" in caplog.text
    assert "num_jobs_queued = 1" in caplog.text

    # now try to add the same job (-> same UID) again, an exception should be raised
    with pytest.raises(ValueError, match="already in this queue"):
        queue.append(job_fixed)

    # now try to get the job back from the queue
    from_queue = queue.next_job()
    assert "Retrieving next job" in caplog.text
    print(from_queue["uid"])
    assert from_queue["uid"] == job_fixed["uid"]
    assert "now empty, removing it" in caplog.text
    assert r"Current contents of all queues: {}" in caplog.text

    # try to remove the job from the queue
    caplog.clear()
    print("current queue.jobs: %s" % queue.jobs)
    queue.remove(job_fixed["uid"])
    assert "Trying to remove job" in caplog.text
    assert "Status of job to be removed: queued" in caplog.text
    assert "not found, discarding the request" not in caplog.text
    assert len(queue) == 0

    # try to remove it again
    caplog.clear()
    assert queue.remove(job_fixed["uid"]) is None
    assert "not found, discarding the request" in caplog.text


def test_job_queue_remove_unqueued(caplog, jobfile_valid_decon_fixedtimestamp):
    """Test the queue behaviour if a non-queued job is requested to be removed.

    If all goes well it should not happen that a job is registered in the (global)
    queue's joblist `queue.jobs` without being listed on one of the sub-queues. This
    test is checking the queue's behaviour if such a job is trying to be removed.
    """
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    caplog.clear()
    # first we have to add a job to the queue's joblist by accessing the `jobs`
    # attribute directly (which should not be done)
    fake_job = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    fake_job["uid"] = "zzzz"
    queue.jobs[fake_job["uid"]] = fake_job
    print("current queue.jobs: %s" % queue.jobs)
    # now trying to remove it should yield None and a corresponding log message
    assert queue.remove(fake_job["uid"]) is None
    assert "Can't find job" in caplog.text
    print("current queue.jobs: %s" % queue.jobs)
    assert len(queue) == 0
    assert len(queue.jobs) == 0


def test_job_queue_rotation(
    caplog,
    jobfile_valid_decon_fixedtimestamp,
    jobfile_valid_decon_user01,
    jobfile_valid_decon_user02,
):
    """Test the queue rotation (round robin) behaviour in `next_job()`.

    First add two jobs for `user01` and one job for `user02` to the queue, then fetch a
    job from the queue using `next_job()`. As a result the (sub-) queue of `user01`
    has to be at the last position in the (global) queue.
    """
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    # prepare the jobs
    job_fixed = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    job1 = snijder.jobs.JobDescription(jobfile_valid_decon_user01, "file")
    job2 = snijder.jobs.JobDescription(jobfile_valid_decon_user02, "file")
    logging.info(job1)
    logging.info(job2)
    assert job1["uid"] != job2["uid"]

    caplog.clear()
    # now add jobs from more than one category (~user) to the queue, check if it is
    # rotating correctly when retrieving them back:
    queue.append(job_fixed)
    assert len(queue) == 1
    assert queue.categories[0] == "user01"
    queue.append(job1)
    assert len(queue) == 2
    queue.append(job2)
    assert len(queue) == 3
    assert queue.categories[1] == "user02"
    for cat in queue.categories:
        logging.warning("queue of [%s]: %s", cat, queue.queue[cat])
    assert len(queue.queue["user01"]) == 2
    assert len(queue.queue["user02"]) == 1
    queue.next_job()
    assert len(queue.queue["user01"]) == 1
    assert len(queue.queue["user02"]) == 1
    assert queue.categories[0] == "user02"
    assert queue.categories[1] == "user01"
    for cat in queue.categories:
        logging.warning("queue of [%s]: %s", cat, queue.queue[cat])
