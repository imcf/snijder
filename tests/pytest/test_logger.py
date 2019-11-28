"""Tests for the snijder.logger module."""

from __future__ import print_function

import logging

import snijder.logger

import pytest  # pylint: disable-msg=unused-import


def test_set_verbosity():
    """Test the set_verbosity() method."""
    snijder.logger.set_verbosity(0)
    assert snijder.logger.LOGGER.level == logging.WARNING

    snijder.logger.set_verbosity(1)
    assert snijder.logger.LOGGER.level == logging.INFO

    snijder.logger.set_verbosity(2)
    assert snijder.logger.LOGGER.level == logging.DEBUG
