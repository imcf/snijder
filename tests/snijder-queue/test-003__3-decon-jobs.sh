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
# 2) switch to pause mode
# 3) place three deconvolution jobs in the queue
# 4) switch to run mode
# 5) shutdown QM when queue is empty, latest after 5 min
#
# pytest-equivalent: tests/pytest/test_spooler.py::test_multiple_decon_jobs
#
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

qm_request pause 2

submit_jobs "decon_job_"

qm_request run 1

shutdown_qm_on_empty_queue 300

msg_finished

