#!/bin/bash
#
# function definitions to be included in various test scripts.


# NOTE: the init() function is called directly when this file is being sourced,
#       see the very bottom of the file!


######################### INIT #########################
init() {
    # Do some sanity checks and set global variables:
    #   * check if config file is there, read it
    #   * check if QM executable is there
    #
    # Upon successfull completion, a number of global variables is set:
    #   * CONFFILE
    #   * QM_BASEDIR
    #   * QM_EXEC
    #   * QM_OPTS

    cd "../.."  # switch back to the top-level directory

    CONFFILE="config/snijder-queue.conf"
    if ! [ -r "$CONFFILE" ] ; then
        error "Can't find config file, expected at '$CONFFILE'!"
        exit 254
    fi
    source "$CONFFILE"

    local QM_PY="bin/snijder-queue"
    if ! [ -f "$QM_PY" ] ; then
        error "Can't find queue manager executable!"
        exit 2
    fi

    # by reaching this point we know the config and the executable is there, so
    # we remember the directory and return to the previous one:
    QM_BASEDIR=$(pwd)
    cd - > /dev/null

    # the "-u" flag requests Python to run with unbuffered stdin/stdout, which is
    # required for testing to ensure the messages are always printed in the very
    # order in which the program(s) were sending them:
    QM_EXEC="python -u $QM_PY"

    # verbose mode can be enabled by exporting the $VERBOSE environment var:
    if [ -n "$VERBOSE" ] ; then
        local VERB="-vv"
    else
        local VERB="-v"
    fi

    QM_OPTS="--spooldir $SPOOLINGDIR --config $GC3CONF $VERB"
}
######################### INIT #########################



python_can_import() {
    # set +e
    # which python
    # echo $PYTHONPATH
    if python -c "import $1" 2> /dev/null ; then
        colr green "Found Python package '$1'."
        return 0
    else
        error "Can't import module '$1'!"
        return -1
    fi
    # set -e
}


check_python_packages() {
    # test if Python can import our required packages (gc3libs, snijder)
    if ! python_can_import "gc3libs" ; then
        MSG="\nMake sure to have the required virtualenv active, e.g.\n"
        MSG="$MSG\nsource /opt/snijder/venvs/gc3pie_2.5.0/bin/activate\n"
        colr yellow "$MSG"
        exit 255
    fi
    if ! python_can_import "snijder" ; then
        MSG="\nPlease adjust your PYTHONPATH accordingly, e.g.\n"
        MSG="$MSG\nexport PYTHONPATH=\"$(pwd)/src:\$PYTHONPATH\"\n"
        colr yellow "$MSG"
        exit 255
    fi
}


clean_all_spooldirs() {
    echo -ne '\033[01;31m'  # red
    set +e
    rm -vf "$SPOOLINGDIR/gc3/resource/shellcmd.d/"*
    rm -vf "$SPOOLINGDIR/spool/cur/"*
    rm -vf "$SPOOLINGDIR/spool/new/"*
    rm -vf "$SPOOLINGDIR/queue/requests/"*
    set -e
    echo -ne '\033[00m'  # black / white
}


check_spooldirs_clean() {
    # test if all relevant spooling directories are empty, EXIT otherwise!
    for DIR in new cur ; do
        if ! spooldir_is_empty "$DIR" ; then
            error "Unclean spooling directory '$DIR' found! Stopping."
            exit 1
        fi
    done
}


spooldir_is_empty() {
    # check if a given spool directory contains files
    if [ -z "$1" ] ; then
        error "No spooling dir specified to check!"
        exit 255
    fi
    DIR="../../$SPOOLINGDIR/spool/$1/"
    COUNT=$(ls "$DIR" | wc -l)
    if [ $COUNT -eq 0 ] ; then
        # echo "No jobs in '$1' spooling directory!"
        return 0
    else
        colr yellow "WARNING: found $COUNT jobfiles in '$1': $DIR"
        return 1
    fi
}


qm_is_running() {
    test $(pgrep --count --full "$QM_EXEC") -gt 0
}


hucore_is_running() {
    test $(pgrep --count --full "hucore.bin") -gt 0
}


qm_request() {
    # send a status change request to the queue manager, making sure the actual
    # process is still alive (EXIT otherwise!)
    # optionally wait for the amount of seconds given as $2 after the request
    colr yellow "Requesting QM status change to: $1"
    if ! qm_is_running ; then
        error "QM is not running (any more?) - stopping here!"
        exit 3
    fi
    touch "$SPOOLINGDIR/queue/requests/$1"
    _wait $2
}


prepare_qm() {
    # Tasks required to prepare a run of the QM that have to be done only once
    # per test-run (unlike the stuff in startup_qm(), which could be called
    # multiple times).
    #
    # change working the working directory to the base dir
    cd "$QM_BASEDIR"
    # check if the required python packages are available
    check_python_packages
    # set a global variable to determine this function was run:
    QM_RUN_PREPARED="yes"
}


startup_qm() {
    # Start a fresh instance of the QM, making sure no other one is running.
    #
    # first check if prepare_qm() has run, but do NOT call it from here as
    # startup_qm() could be called more than once in a single test-run, but
    # prepare_qm() should only be run if explicitly requested
    if [ -z "$QM_RUN_PREPARED" ] ; then
        error "Missing call to prepare_qm()!"
        exit 253
    fi
    if qm_is_running ; then
        MSG="QM seems to be running already! \n"
        MSG="$MSG  --> NOT starting another one to prevent unexpected behaviour."
        error $MSG
        exit 1
    fi
    colr green "**** Starting Queue Manager..."
    colr green $QM_EXEC $QM_OPTS
    $QM_EXEC $QM_OPTS &
    # remember the PID of the background process:
    QM_PID=$!
    # give the QM some time to start up
    sleep 1
    # test if the QM process is alive by sending a "refresh" request:
    qm_request refresh
    # give the QM some time to process the "refresh" request, so the followup
    # requests won't get mixed with this one:
    sleep 1
    colr green "QM process started."
}


submit_jobs() {
    # copy jobfiles with a given prefix into the spool/new directory to submit
    # them to a running queue manager
    # by default wait 0.5s after submitting all jobs unless specified
    # differently using the second parameter
    # by default wait 0.1s after EACH job being submitted before submitting
    # the next one, can be overridden via $3
    if [ -z "$1" ] ; then
        error "No jobfile prefix given for submission!"
        exit 4
    fi
    # we are expected to be in the snijder base dir, so use the full path:
    for jobfile in tests/snijder-queue/inputs/$SHORT/${1}*.cfg ; do
        cp -v $jobfile "$SPOOLINGDIR/spool/new"
        sleep ${3:-.1}
    done
    WAIT=${2:-.5}  # by default wait .5s unless specified as 2nd parameter
    _wait $WAIT
}


wait_for_hucore_to_finish() {
    # try to terminate any still-running hucore processes
    if hucore_is_running ; then
        if [ -n "$1" ] ; then
            colr yellow "WARNING: Found running HuCore processes!"
            _wait $1
        fi
        if hucore_is_running ; then
            colr yellow "WARNING: Found running HuCore processes, trying to kill them..."
            killall hucore.bin
        fi
    fi
}


wait_for_qm_to_finish() {
    # Wait a given number of seconds for the QM process to terminate,
    # otherwise try to shut it down (gracefully, using a shutdown request), or
    # try to kill it as a last resort.
    if qm_is_running ; then
        colr green "QM is still running..."
    fi
    for counter in $(seq 1 $1) ; do
        sleep 1
        if ! qm_is_running ; then
            colr green "QM process terminated."
            wait_for_hucore_to_finish
            return
        fi
    done
    if qm_is_running ; then
        colr yellow "WARNING: QM is STILL running after $1 seconds!"
        colr yellow "Trying to shut it down..."
        qm_request shutdown 1
    fi
    if qm_is_running ; then
        colr yellow "WARNING: QM doesn't listen to our shutdown request!"
        colr yellow "Trying to kill it..."
        pkill --signal HUP --full "$QM_EXEC"
        sleep 1
    fi
    if qm_is_running ; then
        error "QM doesn't react to HUP, giving up!"
    fi
    wait_for_hucore_to_finish 2
}


queue_is_empty() {
    # Test if the queue is empty, EXIT if the queue file doesn't exist!
    QFILE="$SPOOLINGDIR/queue/status/hucore.json"
    if [ -n "$1" ] ; then
        QFILE="$SPOOLINGDIR/queue/status/$1.json"
    fi
    # the queue file *HAS TO* exist, otherwise we terminate with an error:
    if ! [ -r "$QFILE" ] ; then
        error "Queue file '$QFILE' doesn't exist!"
        exit 100
    fi
    # cat "$SPOOLINGDIR/queue/status/hucore.json"
    QUEUED=$(grep '"status":' "$QFILE" | wc -l)
    if [ "$QUEUED" -eq 0 ] ; then
        # echo "Queue is empty!"
        return 0
    else
        # echo "--> $QUEUED jobs currently queued"
        return 1
    fi
}


shutdown_qm_on_empty_queue() {
    MSG="Waiting (${1}s max) for the queue to be finished / empty,"
    MSG="$MSG then shutting down the QM."
    colr green $MSG
    if ! qm_is_running ; then
        colr green "QM is not running, so we're done."
        return
    fi
    for counter in $(seq 1 $1) ; do
        if queue_is_empty ; then
            colr green "Queue is empty, trying to shut down the QM!"
            break
        fi
        sleep 1
    done
    if ! queue_is_empty ; then
        error "Queue still not empty after $1 secondes!"
    fi
    qm_request shutdown
    wait_for_qm_to_finish 5
}

msg_finished() {
    echo "************************* TEST FINISHED! *************************"
}


msg_sep() {
    # print a separator to stout and stderr
    SEP="######################################################################"
    echo
    echo $SEP
    echo $SEP >&2
    echo
}


colr() {
    # helper functions to colorize output
    # TODO: check if connected to a console, print non-colored otherwise
    local -A color
    color[red]='\033[01;31m'
    color[green]='\033[01;32m'
    color[yellow]='\033[01;33m'
    local blackwhite='\033[00m'
    echo -ne "${color[$1]}"
    shift
    echo -e "$*"
    echo -ne "$blackwhite"
}

error() {
    colr red "============================ ERROR ============================"
    colr red "$*"
    colr red "============================ ERROR ============================"
}


_wait() {
    if [ -z "$1" ] ; then
        return
    fi
    if [ "$1" == "0" ] ; then
        return
    fi
    echo "Waiting $1 seconds..."
    sleep $1
}


parse_shortname() {
    SHORT=$(basename $0 | sed 's,__.*,,')
    echo $SHORT
}

strip_c() {
    # strip away the color codes generated above so the control chars don't end
    # up in the log files (from https://unix.stackexchange.com/questions/111899)
    sed -u '''
        s/\x1B\[\([0-9]\{1,2\}\(;[0-9]\{1,2\}\)\?\)\?[mGK]//g
    '''
}

strip_rt() {
    # strips away various hashes that are runtime-specific, to make the result
    # better comparable among subsequent individual runs
    sed -u '''
        s/uid:[0-9a-f]\{7\}/UID_STRIPPED/g
        s/[0-9a-f]\{40\}/UID_STRIPPED/g
        s/App@[0-9a-f]\{12\}/App@APPID_STRIPPED/g
        s/[0-9]\{10\}\.[0-9]\{1,6\}/TIMESTAMP_STRIPPED/g
        s/  cpu: [0-9\.]*s  /  CPUTIME_STRIPPED  /
        s/  wall: [0-9\.]*s  /  WALLTIME_STRIPPED  /
        s/  max_mem: [0-9]*kB  /  MAXMEM_STRIPPED  /
        s/unclean: \[['"'"'0-9]*\]/unclean: \[RSC_STRIPPED\]/g
    ''' | strip_c
}



######################### INIT #########################
# run the init function immediately while we're sourced:
init
######################### INIT #########################
