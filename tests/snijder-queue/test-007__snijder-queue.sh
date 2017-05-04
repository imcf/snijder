#!/bin/bash

# exit on any error:
set -e

# remember path prefix as called, source functions
PFX=$(dirname $0)
source "$PFX/functions.inc.sh"

SHORT=$(parse_shortname)
PYSCRIPT="scripts/python/$(basename $0 | sed 's,.sh$,.py,')"

########## TEST DESCRIPTION ##########
# intended behaviour:
# 1) launches the Python script that does the JobQueue testing
########## TEST DESCRIPTION ##########

ls $PYSCRIPT
python $PYSCRIPT

msg_finished

