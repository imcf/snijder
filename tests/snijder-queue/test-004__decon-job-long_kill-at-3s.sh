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
# 3) place the jobs from the inputs directory in the queue
# 4) switch to run mode
# 5) request a QM shutdown after 3 seconds
# 6) wait 5s for the QM to shut down, kill it the hard way otherwise
#
# pytest-equivalent: tests/pytest/test_spooler.py::test_killing_decon_jobs_at_3s
#
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

qm_request pause 1

submit_jobs "decon_job_"

qm_request run 3

qm_request shutdown

wait_for_qm_to_finish 5

msg_finished

