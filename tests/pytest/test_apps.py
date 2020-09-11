"""Tests for the snijder.apps module."""

# pylint: disable-msg=invalid-name

from __future__ import print_function

import snijder.apps
import snijder.apps.hucore

import pytest  # pylint: disable-msg=unused-import


def prepare_logging(caplog):
    """Helper function to set up logging appropriately."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


def test_abstractapp_constructor():
    """Test the AbstractApp constructor.

    The constructor is expected to raise a TypeError, as this class is not supposed to
    be instantiated itself, but rather to be inherited from.
    """
    with pytest.raises(TypeError, match="Refusing to instantiate class 'AbstractApp'"):
        snijder.apps.AbstractApp(job=None, appconfig=dict())


def test_hucoreapp_constructor():
    """Test the HuCoreApp constructor.

    The constructor is expected to raise a TypeError, as this class is not supposed to
    be instantiated itself, but rather to be inherited from.
    """
    with pytest.raises(TypeError, match="Not instantiating the virtual class"):
        snijder.apps.hucore.HuCoreApp(job=None, output_dir="")
