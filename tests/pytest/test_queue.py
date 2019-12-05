"""Tests for the snijder.queue module."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=len-as-condition

# 'black' has priority over 'pylint:
# pylint: disable-msg=bad-continuation

from __future__ import print_function

import logging
import json

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
    assert queue.num_jobs_queued() == 1

    # now try to add the same job (-> same UID) again, an exception should be raised
    with pytest.raises(ValueError, match="already in this queue"):
        queue.append(job_fixed)

    # now try to get the job back from the queue
    from_queue = queue.next_job()
    assert "Retrieving next job" in caplog.text
    print(from_queue["uid"])
    assert from_queue["uid"] == job_fixed["uid"]
    assert "Removing empty queue" in caplog.text
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

    # add it again, then remove it (without assigning it to the processing list by
    # calling next_job() before)
    caplog.clear()
    queue.append(job_fixed)
    queue.remove(job_fixed["uid"])
    assert "Removing job from queue" in caplog.text
    assert "Empty queue!" in caplog.text


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


def test_process_deletion_list(caplog, jobfile_valid_decon_fixedtimestamp):
    """Test the process_deletion_list() method."""
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    # parse the jobfile and append the job to the queue
    caplog.clear()
    job = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    print(job["uid"])
    queue.append(job)

    # place the job's UID on the deletion list
    assert len(queue.deletion_list) == 0
    queue.deletion_list.append(job["uid"])
    assert len(queue.deletion_list) == 1
    queue.process_deletion_list()
    assert len(queue.deletion_list) == 0
    assert "Received a deletion request for job" in caplog.text
    assert "Status of job to be removed: queued" in caplog.text
    assert "Removing job from queue" in caplog.text
    assert "Job successfully removed from the queue" in caplog.text
    assert "Job not found, discarding the request" not in caplog.text
    assert "No job removed, invalid uid or other queue's job." not in caplog.text

    # try with an unknown UID
    caplog.clear()
    assert len(queue.deletion_list) == 0
    queue.deletion_list.append("zzzz")
    assert len(queue.deletion_list) == 1
    queue.process_deletion_list()
    assert len(queue.deletion_list) == 0
    assert "Received a deletion request for job" in caplog.text
    assert "Job not found, discarding the request" in caplog.text
    assert "No job removed, invalid uid or other queue's job." in caplog.text
    assert "Status of job to be removed: queued" not in caplog.text
    assert "Removing job from queue" not in caplog.text
    assert "Job successfully removed from the queue" not in caplog.text


def test_set_jobstatus(caplog, jobfile_valid_decon_fixedtimestamp):
    """Test the set_jobstatus() method."""
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    # parse the jobfile and append the job to the queue
    caplog.clear()
    job = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    print(job["uid"])
    assert queue.num_jobs_queued() == 0
    queue.append(job)
    assert queue.num_jobs_queued() == 1

    # change the status to "TERMINATED", which will also remove the job from the queue
    queue.set_jobstatus(job, "TERMINATED")
    assert "Changing job-status" in caplog.text
    assert "[status:TERMINATED]" in caplog.text
    assert "Removing job from queue" in caplog.text
    assert queue.num_jobs_queued() == 0
    assert queue.num_jobs_processing() == 0


def test_queue_details_json(
    caplog,
    tmp_path,
    jobfile_valid_decon_fixedtimestamp,
    jobfile_valid_decon_user01,
    jobfile_valid_decon_user02,
):
    """Test the queue_details_json() method."""
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    # assign a statusfile
    statusfile = tmp_path / "test_queue_details.json"
    queue.statusfile = str(statusfile)

    # parse the jobfiles and append the jobs to the queue
    caplog.clear()
    job_fixed = snijder.jobs.JobDescription(jobfile_valid_decon_fixedtimestamp, "file")
    job1 = snijder.jobs.JobDescription(jobfile_valid_decon_user01, "file")
    job2 = snijder.jobs.JobDescription(jobfile_valid_decon_user02, "file")
    logging.info("job_fixed UID: %s", job_fixed["uid"])
    logging.info("job1 UID: %s", job1["uid"])
    logging.info("job2 UID: %s", job2["uid"])

    queue.append(job_fixed)
    queue.append(job1)
    queue.append(job2)
    assert queue.num_jobs_queued() == 3
    assert queue.num_jobs_processing() == 0

    # call next_job() so one of the jobs will be assigned to the "processing" jobs
    processing_job = queue.next_job()
    assert queue.num_jobs_queued() == 2
    assert queue.num_jobs_processing() == 1
    assert processing_job["uid"] == job_fixed["uid"]

    details = queue.queue_details_json()
    logging.debug("JSON encoded queue details:\n%s", details)

    # now parse the JSON formatted string back into a Python object
    parsed_json = json.loads(details)
    jobs = parsed_json["jobs"]

    # NOTE: jobs in the queue details are in this order: first any jobs from the
    # `processing` list, then the jobs as returned by `joblist()`

    # job_fixed is therefore the first one
    assert jobs[0]["id"] == job_fixed["uid"]
    assert jobs[0]["username"] == job_fixed["user"]
    assert jobs[0]["queued"] == job_fixed["timestamp"]

    # followed by job2
    assert jobs[1]["id"] == job2["uid"]
    assert jobs[1]["username"] == job2["user"]
    assert jobs[1]["queued"] == job2["timestamp"]

    # and finally job1
    assert jobs[2]["id"] == job1["uid"]
    assert jobs[2]["username"] == job1["user"]
    assert jobs[2]["queued"] == job1["timestamp"]

    logging.info("Re-parsed queue details from JSON.")


def test_queue_details_hr(
    caplog, jobfile_valid_decon_user01, jobfile_valid_decon_user02
):
    """Test the queue_details_hr() method."""
    prepare_logging(caplog)

    # create the queue
    queue = snijder.queue.JobQueue()

    job1 = snijder.jobs.JobDescription(jobfile_valid_decon_user01, "file")
    job2 = snijder.jobs.JobDescription(jobfile_valid_decon_user02, "file")

    queue.append(job1)
    queue.append(job2)
    queue.next_job()

    # in log level "warn" the method should return `None`
    snijder.logger.set_loglevel("warn")
    caplog.clear()
    queue.queue_details_hr()
    assert "queue status" not in caplog.text

    # in log level "info" the method should return a short queue summary
    snijder.logger.set_loglevel("info")
    caplog.clear()
    queue.queue_details_hr()
    assert "jobs retrieved for processing" in caplog.text
    assert "jobs queued (not yet retrieved)" in caplog.text
    assert "user01 (user01@mail.xy)" in caplog.text

    # now create five more jobs and add them to see the queue truncation
    caplog.clear()
    for _ in range(5):
        job = snijder.jobs.JobDescription(jobfile_valid_decon_user01, "file")
        queue.append(job)
    queue.queue_details_hr()
    assert "[ showing first 5 jobs (total: 6) ]" in caplog.text
