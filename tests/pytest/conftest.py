"""Module-wide fixtures for testing snijder."""

# pylint: disable-msg=fixme

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name

from __future__ import print_function

import os

import pytest


def jobfile_path(name, category="valid"):
    """Helper function to locate a job configuration file.

    Parameters
    ----------
    name : str
        The name of the job configuration file.
    category : str, optional
        One of ["valid", "invalid"], by default "valid"

    Returns
    -------
    str
        The (relative) path to the job configuration file.
    """
    file_path = os.path.join("tests", "resources", "jobfiles", category, name)
    print("Generated job configuration file path: %s" % file_path)
    return file_path


@pytest.fixture(scope="module")
def jobcfg_valid_delete():
    """A valid job configuration string for a `deletejobs` job."""
    config = (
        u"[snijderjob]\n"
        u"version = 7\n"
        u"username = user01\n"
        u"useremail = user01@mail.xy\n"
        u"jobtype = deletejobs\n"
        u"timestamp = 1435827755.2494\n"
        u"\n"
        u"[deletejobs]\n"
        u"ids = bfbe38a1c35ec1e8ad7eb881f0258f8ce15d2721\n"
    )

    return config
