#!/bin/bash

set -e
# remember path prefix as called, source functions
PFX=$(dirname $0)
cd $PFX
source "functions.inc.sh"
set +e

for TEST in test-*__*.sh ; do
    set -e
    if ! spooldir_cur_is_empty ; then
        echo "ERROR, unclean spooling directory found! Stopping."
        exit 1
    fi
    # parse the "short" test name (basically the number):
    SHORT=$(echo $TEST | sed 's,__.*,,')
    RES="results/$SHORT"
    rm -rf $RES
    mkdir -p $RES
    set +e
    echo "++++++++++++++++++++ Running $SHORT ($TEST) ++++++++++++++++++++"
    STDOUT="$RES/stdout"
    STDERR="$RES/stderr"
    EXITVAL="$RES/exitval"
    bash $TEST >$STDOUT 2>$STDERR
    RET=$?
    echo $RET > $EXITVAL
    echo "Test '$SHORT' finished (exit code: $RET, results in '$PFX/$RES')."
    echo
done
