# -*- coding: utf-8 -*-
"""
Queue class module for SNIJDER.

Classes
-------

JobQueue()
    Job handling and scheduling.
"""

import itertools
import json
import pprint
from collections import deque

import gc3libs

from . import logi, logd, logw, logc, loge          # pylint: disable=W0611
from .logger import LOGGER, LEVEL_MAPPING


class JobQueue(object):
    """Class to store a list of jobs that need to be processed.

    An instance of this class can be used to keep track of lists of jobs of
    different categories (e.g. individual users). The instance will contain a
    scheduler so that it is possible for the caller to simply request the next
    job from this queue without having to care about priorities or anything
    else.
    """

    def __init__(self):
        """Initialize an empty job queue.

        Instance Variables
        ------------------
        statusfile : str (default=None)
            file name used to write the JSON formatted queue status to
        categories : deque
            categories (users), used by the scheduler
        jobs : dict(JobDescription)
            holding job descriptions (key: UID)
        processing : list
            UID's of jobs being processed currently
        queue : dict(deque)
            queues of each category (user)
        deletion_list : list
            UID's of jobs to be deleted from the queue (NOTE: this list may
            contain UID's from other queues as well!)
        status_changed : bool
            Flag indicating whether the queue status has changed since the
            status file has been written the last time and the status has been
            reported to the log files.
        """
        self._statusfile = None
        self.categories = deque('')
        self.jobs = dict()
        self.processing = list()
        self.queue = dict()
        self.deletion_list = list()
        self.status_changed = False

    def __len__(self):
        """Get the total number of jobs in all queues (incl. processing)."""
        jobsproc = self.num_jobs_processing()
        jobstotal = self.num_jobs_queued() + jobsproc
        logd("len(JobQueue) = %s (%s processing)", jobstotal, jobsproc)
        return jobstotal

    @property
    def statusfile(self):
        """Get the 'statusfile' attribute."""
        return self._statusfile

    @statusfile.setter
    def statusfile(self, statusfile):
        """Set the file used to place the (JSON formatted) queue status in.

        Parameters
        ----------
        statusfile : str
        """
        logi("Setting job queue status report file: %s", statusfile)
        self._statusfile = statusfile

    def num_jobs_queued(self):
        """Get the number of queued jobs (waiting for retrieval)."""
        numjobs = 0
        for queue in self.queue.values():
            numjobs += len(queue)
        logd("num_jobs_queued = %s", numjobs)
        return numjobs

    def num_jobs_processing(self):
        """Get the number of currently processing jobs."""
        numjobs = len(self.processing)
        logd("num_jobs_processing = %s", numjobs)
        return numjobs

    def append(self, job):
        """Add a new job to the queue.
    
        Parameters
        ----------
        job : JobDescription
            The job to be added to the queue.
        """
        category = job.get_category()
        uid = job['uid']
        if uid in self.jobs:
            raise ValueError("Job with [uid:%.7s] already in this queue!" % uid)
        logi("Enqueueing job [uid:%.7s] into category '%s'.", uid, category)
        self.jobs[uid] = job  # store the job in the global dict
        if category not in self.categories:
            logi("Adding a new queue for '%s' to the JobQueue.", category)
            self.categories.append(category)
            self.queue[category] = deque()
            logd("Current queue categories: %s", self.categories)
        # else:
        #     # in case there are already jobs of this category, we don't touch
        #     # the scheduler / priority queue:
        #     logd("JobQueue already contains a queue for '%s'.", category)
        self.queue[category].append(uid)
        self.set_jobstatus(job, 'queued')
        self.status_changed = True

    def _is_queue_empty(self, category):
        """Clean up if a queue of a given category is empty.

        Returns
        -------
        status : bool
            True if the queue was empty and removed, False otherwise.
        """
        if self.queue[category]:
            return False

        logd("Queue for category '%s' now empty, removing it.", category)
        self.categories.remove(category)  # remove it from the categories list
        del self.queue[category]    # delete the category from the queue dict
        return True

    def next_job(self):
        """Return the next job description for processing.

        Picks the next that should be processed from that queue that has the
        topmost position in the categories queue. After selecting the job, the
        categories queue is shifted one to the left, meaning that the category
        of the just picked job is then at the last position in the categories
        queue.
        This implements a very simple round-robin (token based) scheduler that
        is going one-by-one through the existing categories.

        Returns
        -------
        job : JobDescription
        """
        if not self.categories:
            return None
        category = self.categories[0]
        jobid = self.queue[category].popleft()
        # put it into the list of currently processing jobs:
        self.processing.append(jobid)
        logi("Retrieving next job: category '%s', [uid:%.7s].", category, jobid)
        if not self._is_queue_empty(category):
            # push the current category to the last position in the queue:
            self.categories.rotate(-1)
        logd("Current queue categories: %s", self.categories)
        logd("Current contents of all queues: %s", self.queue)
        self.status_changed = True
        return self.jobs[jobid]

    def remove(self, uid, update_status=True):
        """Remove a job with a given UID from the queue.

        Take a job UID and remove the job from the list of currently processing
        jobs or its category's queue, cleaning up the queue if necessary.

        Parameters
        ----------
        uid : str
            UID of job to remove
        update_status : bool (optional, default=True)
            update the queue status file after a job has been successfully
            removed - set to 'False' to avoid unnecessary status updates e.g.
            in case of bulk deletion requests

        Returns
        -------
        job : JobDescription
            The JobDescription dict of the job that was removed (on success).
        """
        logd("Trying to remove job [uid:%.7s].", uid)
        if uid not in self.jobs:
            logi("Job [uid:%.7s] not found, discarding the request.", uid)
            return None

        job = self.jobs[uid]   # remember the job for returning it later
        category = job.get_category()
        logi("Status of job to be removed: %s", job['status'])
        del self.jobs[uid]     # remove the job from the jobs dict
        self.status_changed = True
        if category in self.queue and uid in self.queue[category]:
            logd("Removing job [uid:%.7s] from queue '%s'.", uid, category)
            self.queue[category].remove(uid)
            self._is_queue_empty(category)
        elif uid in self.processing:
            logd("Removing job [uid:%.7s] from currently processing jobs.", uid)
            self.processing.remove(uid)
        else:
            logw("Can't find job [uid:%.7s] in any of our queues!", uid)
            return None

        # logd("Current jobs: %s", self.jobs)
        # logd("Current queue categories: %s", self.cats)
        # logd("Current contents of all queues: %s", self.queue)
        if update_status:
            logd(self.update_status())
        return job

    def process_deletion_list(self):
        """Remove jobs from this queue that are on the deletion list."""
        for uid in self.deletion_list:
            logi("Job [uid:%.7s] was requested for deletion", uid)
            self.deletion_list.remove(uid)
            removed = self.remove(uid, update_status=False)
            if removed is None:
                logd("No job removed, invalid uid or other queue's job.")
            else:
                logi("Job successfully removed from the queue.")
        # updating the queue status file is only done now:
        logd(self.update_status())

    def set_jobstatus(self, job, status):
        """Update the status of a job and trigger related actions.

        Parameters
        ----------
        job : JobDescription
            The job to be updated
        status : str
            The new status.
        """
        logd("Changing status of job [uid:%.7s] to %s", job['uid'], status)
        job['status'] = status
        self.status_changed = True
        if status == gc3libs.Run.State.TERMINATED:  # pylint: disable=E1101
            self.remove(job['uid'])
        logd(self.update_status())

    def update_status(self):
        """Update the queue status information (JSON and logs)

        Returns
        -------
        str
            The JSON-formatted dict as returned by queue_details_json().
        """
        if not self.status_changed:
            return None
        self.status_changed = False
        self.queue_details_hr()
        return self.queue_details_json()

    def queue_details_json(self):
        """Generate a JSON representation of the queue details.

        Returns
        -------
        str
            A JSON-formatted dict with the details of the current queue status
            in the following form:

        details = { "jobs" :
            [
                {
                    "username" : "user00",
                    "status"   : "N/A",
                    "queued"   : 1437152020.751692,
                    "file"     : [ "data/example.h5" ],
                    "start"    : "N/A",
                    "progress" : "N/A",
                    "pid"      : "N/A",
                    "id"       : "8cd0d80f36dd8f7655bde8679b192f526f9541bb",
                    "jobType"  : "hucore",
                    "server"   : "N/A"
               },
            ]
        }
        """
        def format_job(job):
            """Helper function to assemble the job dict."""
            fjob = {
                "id"      : job['uid'],
                "file"    : job['infiles'],
                "username": job['user'],
                "jobType" : job['type'],
                "status"  : job['status'],
                "server"  : 'N/A',
                "progress": 'N/A',
                "pid"     : 'N/A',
                "start"   : 'N/A',
                "queued"  : job['timestamp'],
            }
            return fjob

        joblist = self.queue_details()
        formatted = []
        for jobid in self.processing:
            job = self.jobs[jobid]
            formatted.append(format_job(job))
        for job in joblist:
            formatted.append(format_job(job))
        details = {'jobs' : formatted}
        queue_json = json.dumps(details, indent=4)
        if self.statusfile is not None:
            with open(self.statusfile, 'w') as fout:
                fout.write(queue_json)
        return queue_json

    def queue_details_hr(self):
        """Log a human readable representation of the queue details.

        Depending on the requested log level, print a simplified version of the
        current queue to the log. If debug logging is enabled, an extensive
        representation with all the details is logged as well.
        """
        # the information assembling and string formatting below is very
        # time-consuming, so we check the current log level first and return if
        # we wouldn't log anything anyway:
        if LOGGER.level > LEVEL_MAPPING['info']:
            return

        msg = list()
        msg.append("%s queue status %s" % ("=" * 25, "=" * 25))
        msg.append("--- jobs retrieved for processing")
        if not self.processing:
            msg.append("None.")
        for jobid in self.processing:
            job = self.jobs[jobid]
            msg.append("%s (%s): [uid:%.7s] - %s [%s]" %
                       (job['user'], job['email'], job['uid'],
                        job['infiles'], job['status']))
        msg.append("%s queue status %s" % ("-" * 25, "-" * 25))

        msg.append("--- jobs queued (not yet retrieved)")
        joblist = self.queue_details()
        if not joblist:
            msg.append("None.")
        for job in joblist[:5]:
            msg.append("%s (%s): [uid:%.7s] - %s [%s]" %
                        (job['user'], job['email'], job['uid'],
                        job['infiles'], job['status']))
        if len(joblist) > 5:
            msg.append(" [ showing first 5 jobs (total: %s) ]" % len(joblist))
        msg.append("%s queue status %s" % ("=" * 25, "=" * 25))

        logi('queue_details_hr():\n%s', '\n'.join(msg))
        if LOGGER.level > LEVEL_MAPPING['debug']:
            return

        logd('QUEUE STATUS\n'
             '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n'
             "statusfile: %s\n"
             "categories: %s\n"
             "jobs: %s\n"
             "processing: %s\n"
             "queue: %s\n"
             "deletion_list: %s\n"
             '^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^',
             pprint.pformat(self._statusfile),
             pprint.pformat(self.categories),
             pprint.pformat(self.jobs),
             pprint.pformat(self.processing),
             pprint.pformat(self.queue),
             pprint.pformat(self.deletion_list))

    def queue_details(self):
        """Generate a list with the current queue details."""
        return [self.jobs[jobid] for jobid in self.joblist()]

    def joblist(self):
        """Generate a list with job ids respecting the current queue order.

        For now this simply interleaves all queues from all users, until we
        have implemented a more sophisticated scheduling. However, as the plan
        is to have a dynamic scheduling mechanism, the order of the jobs in
        the queue will be subject to constant change - and therefore the
        queue details will in the best case give an estimate of which jobs
        will be run next.

        Example
        -------
        Given the following queue status:
            self.queue = {
                'user00': deque(['u00_j0', 'u00_j1', 'u00_j2', 'u00_j3']),
                'user01': deque(['u01_j0', 'u01_j1', 'u01_j2']),
                'user02': deque(['u02_j0', 'u02_j1'])
            }

        will result in a list of job dicts in the following order:
            ['u02_j0', 'u01_j0', 'u00_j0',
             'u02_j1', 'u01_j1', 'u00_j1'
             'u01_j2', 'u00_j2'
             'u00_j3']

        where each of the dicts will be of this format:
            {'ver': '5',
             'infiles': ['tests/jobfiles/sandbox/faba128.h5'],
             'exec': '/usr/local/bin/hucore',
             'timestamp': 1437123471.579627,
             'user': 'user00',
             'template': 'decon_faba128_it-3_q-0.5.hgsb',
             'type': 'hucore',
             'email': 'user00@mail.xy',
             'uid': '2f53d7f50c22285a92c7fcda74994a69f72e1bf1'}

        """
        joblist = []
        # if the queue is empty, we return immediately with an empty list:
        if len(self) == 0:                          # pylint: disable=C1801
            logd('Empty queue!')
            return joblist
        # put queues into a list of lists, respecting the current queue order:
        queues = [self.queue[category] for category in self.categories]
        # turn into a zipped list of the queues of all users, padding with
        # 'None' to compensate the different queue lengths:
        queues = [x for x in itertools.izip_longest(*queues)]
        # with the example values, this results in the following:
        # [('u02_j0', 'u01_j0', 'u00_j0'),
        #  ('u02_j1', 'u01_j1', 'u00_j1'),
        #  (None,     'u01_j2', 'u00_j2'),
        #  (None,     None,     'u00_j3')]

        # now flatten the tuple-list and fill with the job details:
        joblist = [jobid
                   for roundlist in queues
                   for jobid in roundlist
                   if jobid is not None]
        return joblist
