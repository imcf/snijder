"""Tests for the snijder.logger module."""

from __future__ import print_function

import logging

import snijder.logger

import pytest  # pylint: disable-msg=unused-import

import gc3libs


def test_set_verbosity():
    """Test the set_verbosity() method."""
    snijder.logger.set_verbosity(0)
    assert snijder.logger.LOGGER.level == logging.WARNING

    snijder.logger.set_verbosity(1)
    assert snijder.logger.LOGGER.level == logging.INFO

    snijder.logger.set_verbosity(2)
    assert snijder.logger.LOGGER.level == logging.DEBUG


def test_set_gc3loglevel():
    """Test the set_gc3loglevel() method."""
    snijder.logger.set_gc3loglevel("error")
    assert gc3libs.log.level == logging.ERROR

    snijder.logger.set_gc3loglevel("debug")
    assert gc3libs.log.level == logging.DEBUG
