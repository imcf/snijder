"""Tests for the snijder.queue module."""

# pylint: disable-msg=invalid-name
# pylint: disable-msg=len-as-condition

from __future__ import print_function

import snijder.queue
import snijder.logger

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
