"""Tests for the snijder.queue module."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=len-as-condition

from __future__ import print_function

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
