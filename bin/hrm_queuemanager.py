#!/usr/bin/env python
# -*- coding: utf-8 -*-#

"""
Prototype of a GC3Pie-based job spooler engine.
"""

# stdlib imports
import sys
import os
import argparse

# pylint: disable=wrong-import-position
import HRM
import HRM.queue
from HRM.jobs import process_jobfile
from HRM.logger import set_verbosity
from HRM.spooler import JobSpooler
from HRM.inotify import JobFileHandler


def parse_arguments():
    """Parse command line arguments."""
    argparser = argparse.ArgumentParser(description=__doc__)
    add_arg = argparser.add_argument  # just for readability of the next lines
    add_arg('-s', '--spooldir', required=True,
            help='spooling directory for jobfiles (e.g. "run/spool/")')
    add_arg('-c', '--config', required=False, default=None,
            help='GC3Pie config file (default: ~/.gc3/gc3pie.conf)')
    add_arg('-r', '--resource', required=False,
            help='GC3Pie resource name')
    add_arg('-v', '--verbosity', dest='verbosity',
            action='count', default=0)
    try:
        return argparser.parse_args()
    except IOError as err:
        argparser.error(str(err))


def main():
    """Main loop of the HRM Queue Manager."""
    args = parse_arguments()

    # set the loglevel as requested on the commandline
    set_verbosity(args.verbosity)

    # TODO:
    # [x] init spooldirs as staticmethod of spooler
    # [x] remember files in 'cur' directory
    # [x] let spooler then set the JobDescription class variable
    # [ ] let spooler then set the status file of each queue
    # [ ] then check exisiting files in the 'cur' dir if they belong to any of
    #     our queues, warn otherwise
    # [ ] then process files in the 'new' dir as new ones
    jobqueues = dict()
    jobqueues['hucore'] = HRM.queue.JobQueue()

    job_spooler = JobSpooler(args.spooldir, jobqueues['hucore'], args.config)
    # select a specific resource if requested on the cmdline:
    if args.resource:
        job_spooler.engine.select_resource(args.resource)

    for qname, queue in jobqueues.iteritems():
        status = os.path.join(job_spooler.dirs['status'], qname + '.json')
        queue.statusfile = status

    # process jobfiles already existing during our startup:
    for jobfile in job_spooler.dirs['newfiles']:
        fname = os.path.join(spool_dirs['new'], jobfile)
        process_jobfile(fname, jobqueues, spool_dirs)


    file_handler = JobFileHandler(jobqueues, job_spooler.dirs)

    try:
        # NOTE: spool() is blocking, as it contains the main spooling loop!
        job_spooler.spool()
    finally:
        print 'Cleaning up. Remaining jobs:'
        print jobqueues['hucore'].queue
        file_handler.shutdown()

if __name__ == "__main__":
    sys.exit(main())
