#!/bin/bash

# exit on any error:
set -e

# remember path prefix as called, source functions
PFX=$(dirname $0)
source "$PFX/functions.inc.sh"

SHORT=$(parse_shortname)

########## TEST DESCRIPTION ##########
# intended behaviour:
# 1) start the QM (in 'run' mode)
# 3) place the "decon_job" from the inputs directory in the queue
# 4) request queue status
# 5) place the "remove_job" from the inputs directory in the queue
# 6) request queue status
# 7) shutdown QM when queue is empty (should be IMMEDIATE!), latest after 5 SECONDS
#
# pytest-equivalent: tests/pytest/test_spooler.py::test_remove_running_job
#
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

submit_jobs "decon_job_"

qm_request refresh 2

msg_sep

submit_jobs "remove_job_" 1

msg_sep

qm_request refresh .6

msg_sep

shutdown_qm_on_empty_queue 5

msg_finished

