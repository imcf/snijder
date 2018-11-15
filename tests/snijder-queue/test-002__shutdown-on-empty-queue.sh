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
# 3) switch to run mode
# 4) refresh the queue (currently triggers generation of status file)
# 5) shutdown QM on empty queue (should be immediate), latest after 10s
########## TEST DESCRIPTION ##########


prepare_qm

startup_qm

qm_request pause 1

qm_request run 1

qm_request refresh 1

shutdown_qm_on_empty_queue 10

msg_finished

