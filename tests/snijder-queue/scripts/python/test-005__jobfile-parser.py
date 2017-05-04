#!/usr/bin/env python

"""Simple tests for the jobfile parsing of the snijder class."""

import os
import sys
# the package is supposed to be 4 levels up in the directory hierarchy:
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..' * 4))

import glob
import pprint

import snijder.jobs

# the reload statement is here so we can use the script in subsequent calls
# during an interactive single IPython session:
reload(snijder.jobs)


print '\n>>>>>> Testing CORRECT job description files:\n'
jobfile_list = glob.glob('jobfiles/*.cfg')
jobfile_list.sort()
for jobfile in jobfile_list:
    print "----------------- parsing %s -----------------" % jobfile
    job = snijder.jobs.JobDescription(jobfile, 'file')
    print " - Parsing worked without errors on '%s'." % jobfile
    pprint.pprint(job)


print '\n>>>>>> Testing INVALID job description files:'
jobfile_list = glob.glob('jobfiles/invalid/*.cfg')
jobfile_list.sort()
for jobfile in jobfile_list:
    print "----------------- parsing %s -----------------" % jobfile
    try:
        job = snijder.jobs.JobDescription(jobfile, 'file')
    except ValueError as err:
        print(" - Got the excpected ValueError from '%s':\n   %s\n" %
              (jobfile, err))
