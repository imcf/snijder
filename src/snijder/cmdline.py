# -*- coding: utf-8 -*-

"""Command line related functions (main loop, argument parsing, ...)"""

import os
import argparse

import snijder
import snijder.queue
from snijder.jobs import process_jobfile
from snijder.logger import set_verbosity, set_gc3loglevel
from snijder.spooler import JobSpooler
from snijder.inotify import JobFileHandler


def parse_arguments():
    """Parse command line arguments."""
    argparser = argparse.ArgumentParser(description=__doc__)
    argparser.add_argument(
        "-s",
        "--spooldir",
        required=True,
        help='spooling directory for jobfiles (e.g. "run/spool/")',
    )
    argparser.add_argument(
        "-c",
        "--config",
        required=False,
        default=None,
        help="GC3Pie config file (default: ~/.gc3/gc3pie.conf)",
    )
    argparser.add_argument(
        "-r",
        "--resource",
        required=False,
        help="GC3Pie resource name, see documentation for details",
    )
    argparser.add_argument(
        "-v",
        "--verbosity",
        dest="verbosity",
        action="count",
        help="increase log level (may be repeated)",
        default=0,
    )
    gc3log = argparser.add_mutually_exclusive_group()
    gc3log.add_argument(
        "--gc3debug",
        action="store_true",
        help='set the logging for gc3libs to "DEBUG" level',
    )
    gc3log.add_argument(
        "--gc3info",
        action="store_true",
        help='set the logging for gc3libs to "INFO" level',
    )
    try:
        return argparser.parse_args()
    except IOError as err:
        argparser.error(str(err))


def manage_queue():
    """Main loop of the SNIJDER Queue Manager."""
    args = parse_arguments()

    # set the loglevel as requested on the commandline
    set_verbosity(args.verbosity)
    if args.gc3debug:
        set_gc3loglevel("debug")
    elif args.gc3info:
        set_gc3loglevel("info")

    # TODO:
    # [x] init spooldirs as staticmethod of spooler
    # [x] remember files in 'cur' directory
    # [x] let spooler then set the JobDescription class variable
    # [ ] let spooler then set the status file of each queue
    # [ ] then check existing files in the 'cur' dir if they belong to any of
    #     our queues, warn otherwise
    # [ ] then process files in the 'new' dir as new ones
    jobqueues = dict()
    jobqueues["hucore"] = snijder.queue.JobQueue()

    try:
        job_spooler = JobSpooler(args.spooldir, jobqueues["hucore"], args.config)
    except RuntimeError as err:
        print "\nERROR instantiating the job spooler: %s\n" % err
        return False

    # select a specific resource if requested on the cmdline:
    if args.resource:
        job_spooler.engine.select_resource(args.resource)

    for qname, queue in jobqueues.iteritems():
        status = os.path.join(job_spooler.dirs["status"], qname + ".json")
        queue.statusfile = status

    # process jobfiles already existing during our startup:
    for jobfile in job_spooler.dirs["newfiles"]:
        fname = os.path.join(job_spooler.dirs["new"], jobfile)
        process_jobfile(fname, jobqueues)

    retval = True
    try:
        file_handler = JobFileHandler(jobqueues, job_spooler.dirs)
        # NOTE: spool() is blocking, as it contains the main spooling loop!
        job_spooler.spool()
    except Exception as err:  # pylint: disable=W0703
        print "\nThe Snijder Queue Manager terminated with an ERROR: %s\n" % err
        retval = False
    finally:
        print "Cleaning up. Remaining jobs:"
        print jobqueues["hucore"].queue
        file_handler.shutdown()

    return retval
