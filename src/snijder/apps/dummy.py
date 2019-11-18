"""Dummy app that just issues a 'sleep', intended for testing."""

import os

from . import AbstractApp


class DummySleepApp(AbstractApp):
    """Dummy sleep class inheriting from AbstractApp."""

    def __init__(self, job, output_dir):
        """Set up the sleep job.

        Parameters
        ----------
        job : snijder.jobs.JobDescription
        output_dir : str
        """
        gc3_output_dir = os.path.join(output_dir, "results_%s" % job["uid"])
        appconfig = dict(
            arguments=["/bin/sleep", "1.6"],
            inputs=[],
            outputs=[],
            output_dir=gc3_output_dir,
        )
        # combine stdout & stderr:
        appconfig.update(stderr="stdout.txt", stdout="stdout.txt")
        super(DummySleepApp, self).__init__(job, appconfig)
