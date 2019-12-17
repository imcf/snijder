"""Module-wide fixtures for testing snijder."""

# pylint: disable-msg=fixme
# pylint: disable-msg=invalid-name

# TODO: pylint for Python2 complains about redefining an outer scope when using
# pytest fixtures, this is supposed to be fixed in newer versions, so it should
# be checked again after migration to Python3 (see pylint issue #1535):
# pylint: disable-msg=redefined-outer-name

from __future__ import print_function

import os
import logging
import textwrap
import threading

import snijder

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


def generate_gc3conf(basedir):
    """Helper function to generate a gc3config with a specific `snijder_basedir`.

    Parameters
    ----------
    basedir : str or str-like
        The value to be used for the `snijder_basedir` entry.

    Returns
    -------
    unicode
        A gc3pie configuration as a unicode-string.
    """
    # NOTE: the generated string requires several places to be an actual "%" (percent
    # character), but as we need to inject the basedir via string mapping the "real"
    # percent chars have to be doubled!
    config = textwrap.dedent(
        u"""
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
    """
    )
    return config % str(basedir)


### FIXTURES ###


@pytest.fixture(autouse=True)
def debug_logging(caplog):
    """Auto-use fixture setting the log level(s)."""
    caplog.set_level("DEBUG")
    snijder.logger.set_loglevel("debug")


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
def jobfile_valid_sleep():
    """A valid jobfile for a (dummy) sleep job for `user01`."""
    file_path = jobfile_path("dummy_sleep_user01.cfg")
    return file_path


@pytest.fixture(scope="module")
def gc3conf_with_basedir():
    """Wrapper fixture returning the gc3conf generator function.

    This is used as a parameterization-workaround, as fixtures can't (easily) have
    parameters that will be evaluated at calling time. Like this, the fixture simply
    returns the function and therefore can be "called" by the test.
    """
    return generate_gc3conf


@pytest.fixture(scope="function")
def snijder_spooler(caplog, tmp_path):
    """Fixture providing a spooler in a background thread.

    The fixture sets up a new spooler instance with its own `spooldir` and `gc3conf` and
    prepares a background thread for running the main spooler loop. It returns a proxy
    object that gives access to the spooler configuration, the instance and the thread
    object.

    NOTE 1: the fixture is using the `yield` statement to allow for some teardown code.
    Most notably it will check if the spooling thread has terminated, or will request it
    to do so otherwise.

    NOTE 2: the thread will not be started automatically, this has to be done explicitly
    by calling `thread.start()` on the proxy object.
    """

    class SpoolerProxy(object):

        """Proxy providing access to the spooler instance, the thread and related stuff.

        Instance Attributes
        -------------------
        basedir: str
            The path that was used as `spooldir` parameter for the spooler.
        gc3conf: str
            The gc3pie config file that was used as `gc3conf` parameter for the spooler.
        spooler: snijder.spooler.JobSpooler
            The spooler instance.
        thread: threading.Thread
            The background thread for the spooling loop.
        """

        def __init__(self, basedir, gc3conf, spooler, thread):
            self.basedir = basedir
            self.gc3conf = gc3conf
            self.spooler = spooler
            self.thread = thread

    basedir = tmp_path / "snijder"
    basedir.mkdir()
    logging.info("Created SNIJDER base dir: %s", basedir)

    gc3conf = basedir / "gc3pie_configuration.conf"
    gc3conf.write_text(generate_gc3conf(str(basedir)))
    logging.info("Created gc3pie config file: %s", gc3conf)

    spooler = snijder.spooler.JobSpooler(
        str(basedir), snijder.queue.JobQueue(), str(gc3conf)
    )
    thread = threading.Thread(target=spooler.spool)
    thread.daemon = True

    proxy = SpoolerProxy(basedir, gc3conf, spooler, thread)

    yield proxy

    if proxy.thread.is_alive():
        logging.warning("Spooler thread still alive, trying to shut it down...")
        spooler.shutdown()
        thread.join(timeout=2)
        assert "QM shutdown: spooler cleanup completed." in caplog.text


@pytest.fixture(scope="module")
def joblist(jobfile_valid_decon_user01):
    """Provide a list of job objects with defined usernames and job UIDs.

    The list will have seven jobs in total, three of user 'u000' (UID suffixes from
    'aaa' to 'ccc') and four of user 'u111' (UID suffixes 'ddd' to 'ggg').
    """
    jobs = list(xrange(7))

    for i in xrange(7):
        jobs[i] = snijder.jobs.JobDescription(jobfile_valid_decon_user01, "file")

    jobs[0]["uid"] = "u000_aaa"
    jobs[0]["user"] = "u000"
    jobs[1]["uid"] = "u000_bbb"
    jobs[1]["user"] = "u000"
    jobs[2]["uid"] = "u000_ccc"
    jobs[2]["user"] = "u000"

    jobs[3]["uid"] = "u111_ddd"
    jobs[3]["user"] = "u111"
    jobs[4]["uid"] = "u111_eee"
    jobs[4]["user"] = "u111"
    jobs[5]["uid"] = "u111_fff"
    jobs[5]["user"] = "u111"
    jobs[6]["uid"] = "u111_ggg"
    jobs[6]["user"] = "u111"

    return jobs
