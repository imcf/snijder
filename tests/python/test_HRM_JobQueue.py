#!/usr/bin/env python

"""Simple test script for the HRM Queue Manager class.

Run it from this directory after setting your PYTHONPATH accordingly:

export PYTHONPATH=$PYTHONPATH:../../lib/python/
python test_HRM_JobQueue.py
"""

try:
    import HRM
except ImportError:
    raise SystemExit(__doc__)

# the reload statement is here so we can us the script in subsequent calls
# during a single IPython session:
reload(HRM)

jobs = list(xrange(7))

jobfile = '../jobfiles/sandbox/deconvolution_job.cfg'
for i in xrange(7):
    jobs[i] = HRM.JobDescription(jobfile, 'file')

jobs[0]['uid'] = 'u000_aaa'
jobs[0]['user'] = 'u000'
jobs[1]['uid'] = 'u000_bbb'
jobs[1]['user'] = 'u000'
jobs[2]['uid'] = 'u000_ccc'
jobs[2]['user'] = 'u000'

jobs[3]['uid'] = 'u111_ddd'
jobs[3]['user'] = 'u111'
jobs[4]['uid'] = 'u111_eee'
jobs[4]['user'] = 'u111'
jobs[5]['uid'] = 'u111_fff'
jobs[5]['user'] = 'u111'
jobs[6]['uid'] = 'u111_ggg'
jobs[6]['user'] = 'u111'

def remove_print(uid):
    job = jq.remove(uid)
    print "remove('%s'): %s (joblist: %s)" % (uid, job['uid'], jq.joblist())

def next_print():
    uid = jq.next_job()['uid']
    print "next_job(): %s (joblist: %s)" % (uid, jq.joblist())

jq = HRM.JobQueue()

print("\n******** adding jobs to queue: ********")
print "jq.joblist:", jq.joblist()
for job in jobs:
    jq.append(job)
    print "jq.joblist:", jq.joblist()
jq.queue_details_hr()

print("\n\n******** retrieving jobs from queue for processing: ********")
print "jq.joblist:", jq.joblist()
for job in jobs:
    print "next: '%s' (joblist: %s)" % (jq.next_job()['uid'], jq.joblist())
print "jq.joblist:", jq.joblist()
jq.queue_details_hr()


# create a new job queue
jq = HRM.JobQueue()

print("\n\n******** adding jobs to queue: ********")
print "jq.joblist:", jq.joblist()
for job in jobs:
    jq.append(job)
    print "jq.joblist:", jq.joblist()
jq.queue_details_hr()

print("\n\n******** removing jobs from queue: ********")
print "jq.joblist:", jq.joblist()
remove_print('u000_aaa')
remove_print('u000_bbb')
next_print()
remove_print('u111_ggg')
next_print()
remove_print('u111_eee')
remove_print('u111_fff')
print("\n----- no queued jobs should be left (but some processing) ----")
print "jq.joblist:", jq.joblist()
jq.queue_details_hr()

print("\n\n******** trying to removing jobs from the empty queue: ********")
print jq.remove('aaa')
