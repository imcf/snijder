#!/bin/bash

# exit on any error:
set -e

# remember path prefix as called, source functions
PFX=$(dirname $0)
source "$PFX/functions.inc.sh"

SHORT=$(parse_shortname)

########## TEST DESCRIPTION ##########
# intended behaviour:
# 1) start the QM
# 2) submit a job with a valid jobfile but non-existing inputfiles
#    -> the job should automatically be removed from the queue again
# 3) shutdown QM when queue is empty, latest after 5 seconds
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

submit_jobs "decon_job_"

shutdown_qm_on_empty_queue 5

msg_finished

