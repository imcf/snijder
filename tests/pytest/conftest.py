"""Module-wide fixtures for testing snijder."""

# pylint: disable-msg=fixme
# pylint: disable-msg=invalid-name

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name

from __future__ import print_function

import os
import textwrap

import pytest


### FUNCTIONS ###

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


def gc3conf_path(name):
    """Helper function to locate a gc3pie configuration file.

    Parameters
    ----------
    name : str
        The name of the gc3pie configuration file WITHOUT suffix.

    Returns
    -------
    str
        The (relative) path to the gc3pie configuration file.
    """
    file_path = os.path.join("tests", "resources", "config", "gc3pie", name + ".conf")
    print("Generated gc3pie configuration file path: %s" % file_path)
    return file_path


def generate_gc3conf(basedir):
    """Helper function to generate a gc3config with a specific `snijder_basedir`.

    Parameters
    ----------
    basedir : str
        The value to be used for the `snijder_basedir` entry.

    Returns
    -------
    str
        A gc3pie configuration as a string.
    """
    # NOTE: the generated string requires several places to be an actual "%" (percent
    # character), but as we need to inject the basedir via string mapping the "real"
    # percent chars have to be doubled!
    config = textwrap.dedent("""
        # Very simple configuration for dispatching jobs on the local machine.

        [DEFAULT]
        # The `DEFAULT` section is entirely optional; if present, its values can
        # be used to interpolate values in other sections, using the `%%(name)s` syntax.
        # See documentation of the `SafeConfigParser` object at:
        #   http://docs.python.org/library/configparser.html
        debug = 0
        snijder_basedir = %s


        # Auth sections: [auth/name]
        [auth/noauth]
        type = none

        [resource/localhost]
        enabled = yes
        type = shellcmd
        auth = noauth
        transport = local
        time_cmd = /usr/bin/time
        max_cores = 2
        max_cores_per_job = 2
        max_memory_per_core = 2 GB
        max_walltime = 2 hours
        architecture = x64_64
        spooldir = %%(snijder_basedir)s/gc3/spool
        resourcedir = %%(snijder_basedir)s/gc3/resource/shellcmd.d
    """)
    return config % basedir


### FIXTURES ###

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


@pytest.fixture(scope="module")
def jobfile_valid_decon_fixedtimestamp():
    """A valid jobfile for a deconvolution job with a fixed timestamp.

    This job description will always result in the same job UID as all components
    including the timestamp are fixed before parsing time.
    """
    file_path = jobfile_path("decon_it-999_user01_fixed-timestamp_c682dcd.cfg")
    return file_path


@pytest.fixture(scope="module")
def jobfile_valid_decon_user01():
    """A valid jobfile for a deconvolution job for `user01`."""
    file_path = jobfile_path("decon_it-3_user01.cfg")
    return file_path


@pytest.fixture(scope="module")
def jobfile_valid_decon_user02():
    """A valid jobfile for a deconvolution job for `user02`."""
    file_path = jobfile_path("decon_it-3_user02.cfg")
    return file_path


@pytest.fixture(scope="module")
def gc3conf_path_localhost():
    """A path to a gc3pie configuration file for localhost."""
    file_path = gc3conf_path("localhost")
    return file_path


@pytest.fixture(scope="module")
def gc3conf_with_basedir():
    """Wrapper fixture returning the gc3conf generator function.

    This is used as a parameterization-workaround, as fixtures can't (easily) have
    parameters that will be evaluated at calling time. Like this, the fixture simply
    returns the function and therefore can be "called" by the test.
    """
    return generate_gc3conf
