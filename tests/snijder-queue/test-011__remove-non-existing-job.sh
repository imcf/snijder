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
# 2) submit a request to remove a non-existing job from the queue
# 3) wait for 2 seconds to give the QM some time to process it
# 3) shutdown QM when queue is empty, latest after 10s
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

submit_jobs "remove_job_" 2

shutdown_qm_on_empty_queue 10

msg_finished

