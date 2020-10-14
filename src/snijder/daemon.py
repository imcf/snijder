"""Functions related to building a daemon.

This mostly groups functions that are turning exceptions into a log message and then
continue operation, as for known cases it is mostly undesired to have a daemon stop in
these situations.
"""

from .jobs import JobDescription

from . import logi, logd, logw, logc, loge  # pylint: disable-msg=unused-import


DEFAULT_QUEUE_MAPPING = {
    # jobtype "hucore"
    "hucore": {
        # tasktype "decon"
        "decon": "hucore",
        # tasktype "preview"
        "preview": "hucore",
    },
    #
    # jobtype "dummy"
    "dummy": {
        # tasktype "sleep"
        "sleep": "hucore"
    },
}
"""dict: The default mapping translating jobtype and tasktype to a queue name.

In the current implementation, all combinations of job- and tasktype will map to the
same (only) queue ``hucore``. This needs to be adapted once the multi-queue logic has
been implemented.
"""


def select_queue_for_job(job, mapping=None):
    """Select a queue for a job, depending on its job- and tasktype.

    Inspect the keys ``type`` and ``tasktype`` of the given job and map them to a
    defined queue name.

    Parameters
    ----------
    job : JobDescription
    mapping : dict, optional
        A mapping translating jobtype and tasktype to a queue name, by default ``None``
        which gets expanded to :attr:`DEFAULT_QUEUE_MAPPING`.

    Returns
    -------
    str
        A string to be used as the identifier of a queue.
    """
    if mapping is None:
        mapping = DEFAULT_QUEUE_MAPPING
    if job["type"] not in mapping:
        logc("No queue found for jobtype '%s'!", job["type"])
        return None

    jobtype = mapping[job["type"]]
    if job["tasktype"] not in jobtype:
        logc("No queue found for tasktype '%s'!", job["tasktype"])
        return None

    queuetype = jobtype[job["tasktype"]]
    logd(
        "Selected queue for jobtype (%s) and tasktype (%s): %s",
        job["type"],
        job["tasktype"],
        queuetype,
    )
    return queuetype


def process_jobfile(fname, queues, mapping=None):
    """Parse a jobfile and add it to its destination queue.

    Parameters
    ----------
    fname : str
        The name of the job file to parse.
    queues : dict
        Containing the :class:`~snijder.queue.JobQueue` objects for the different
        queues, having the keys match the possible return values of a call to
        :func:`select_queue_for_job`.
    mapping : dict, optional
        A mapping being passed on to :func:`select_queue_for_job`, by default ``None``.
    """
    try:
        job = JobDescription(fname, "file")
    except IOError as err:
        logw("Error reading job description file (%s), skipping.", err)
        # there is nothing to add to the queue and the IOError indicates
        # problems accessing the file, so we simply return silently:
        return

    except (SyntaxError, ValueError) as err:
        # jobfile was already moved out of the way by the constructor of the
        # JobDescription object, so we simply stop here and return:
        return

    if job["type"] == "deletejobs":
        logw("Received job deletion request(s)!")
        # TODO: append only to specific queue!
        for queue in queues.itervalues():
            for delete_id in job["ids"]:
                queue.deletion_list.append(delete_id)
        # we're finished, so move the jobfile and return:
        job.move_jobfile("done")
        return
    selected_queue = select_queue_for_job(job, mapping)
    if selected_queue not in queues:
        logc("Selected queue does not exist: %s", selected_queue)
        job.move_jobfile("done")
        return

    job.move_jobfile("cur")
    try:
        queues[selected_queue].append(job)
    except ValueError as err:
        loge("Adding the new job from [%s] failed:\n    %s", fname, err)
