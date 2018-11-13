#!/bin/bash

set -e
# remember path prefix as called, source functions
PFX=$(dirname $0)
cd $PFX
source "functions.inc.sh"
set +e


if [ -z "$VIRTUAL_ENV" ] ; then
    GC3VER=2.5.0
    GC3BASE=/opt/gc3pie
    GC3HOME=$GC3BASE/gc3pie_$GC3VER
    source $GC3HOME/bin/activate
fi


RES_BASE="results"

# by default all tests will be run, only if the special variable "RUN_TESTS" is
# set or list of tests is specified as commandline parameters, we limit the
# tests to the ones specified there, e.g. usable like this:
# > RUN_TESTS="test-001__* test-002__*" ./run_tests.sh
# > ./run_tests.sh "test-001__* test-002__*"
if [ -n "$1" ] ; then
    RUN_TESTS="$1"
fi
if [ -z "$RUN_TESTS" ] ; then
    RUN_TESTS=test-*__*.sh
fi

for TEST in $RUN_TESTS ; do
    set -e
    # parse the "short" test name (basically the number):
    SHORT=$(echo $TEST | sed 's,__.*,,')
    RES="$RES_BASE/$SHORT"
    rm -rf $RES
    mkdir -p $RES
    set +e
    colr "yellow" "+++++++++++++++++ Running $SHORT ($TEST) +++++++++++++++++"
    clean_all_spooldirs
    STDOUT="$RES/stdout.log"
    STDOUT_STRIPPED="$RES/stdout-stripped.log"
    STDERR="$RES/stderr.log"
    STDERR_STRIPPED="$RES/stderr-stripped.log"
    EXITVAL="$RES/exitval"

    # now we call the actual test script - with a few special settings:
    #   * use 'stdbuf' to disable buffering, so output order is consistent
    #   * redirect stdout to a file AND a subprocess filtering (stripping)
    #     variable data that is run-specific AND to the console
    #   * redirect stderr to a file AND a filter pipe
    #   * NOTE the different number of 'tee' targets for STDOUT (3: file,
    #     subprocess, stdout=console) and STDERR (2: file and stdout=pipe)
    stdbuf --input=0 --output=0 --error=0 bash $TEST \
        1> >(tee $STDOUT >(strip_runtime_strings > ${STDOUT_STRIPPED})) \
        2> >(tee $STDERR | strip_runtime_strings > ${STDERR_STRIPPED})

    RET=$?
    echo $RET > $EXITVAL

    # clean up after the run:
    clean_all_spooldirs
    # TODO: check for running QM process and terminate it!

    echo
    colr yellow "Test '$SHORT' finished."
    if [ $RET -gt 0 ] ; then
        MSG="*** ERROR ***  exit code: $RET  *** ERROR ***"
        MSG="============================= $MSG ============================="
        colr red "$MSG"
        colr yellow "> showing stderr log ($STDERR):"
        cat "$STDERR"
        colr yellow "> end of stderr log ($STDERR)"
        colr red "$MSG"
    else
        colr green "> exit code: $RET"
        colr green "> results in '$PFX/$RES'"
    fi
    echo
done
