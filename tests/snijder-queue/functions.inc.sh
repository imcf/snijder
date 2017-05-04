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

    cd "$PFX/../.."

    CONFFILE="config/snijder-queue.conf"
    if ! [ -r "$CONFFILE" ] ; then
        echo "ERROR: can't find config file, expected at '$CONFFILE'!"
        exit 254
    fi
    source "$CONFFILE"

    local QM_PY="bin/snijder-queue"
    if ! [ -f "$QM_PY" ] ; then
        echo "ERROR: can't find queue manager executable!"
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
        echo "Found Python package '$1'."
        return 0
    else
        echo "ERROR: can't import module '$1'!"
        return -1
    fi
    # set -e
}


check_python_packages() {
    # test if Python can import our required packages (gc3libs, snijder)
    if ! python_can_import "gc3libs" ; then
        echo "Make sure to have the required virtualenv active, e.g."
        GC3VER=2.4.2
        GC3BASE=/opt/gc3pie
        GC3HOME=$GC3BASE/gc3pie_$GC3VER
        echo -e "\nsource $GC3HOME/bin/activate\n"
        exit 255
    fi
    if ! python_can_import "snijder" ; then
        echo "Please adjust your PYTHONPATH accordingly, e.g."
        cd ../..
        echo -e "\nexport PYTHONPATH=\"$(pwd)/lib/python:\$PYTHONPATH\"\n"
        exit 255
    fi
}


clean_all_spooldirs() {
    set +e
    rm -vf /data/gc3_resourcedir/shellcmd.d/*
    rm -vf "../../$SPOOLINGDIR/spool/cur/"*
    rm -vf "../../$SPOOLINGDIR/spool/new/"*
    rm -vf "../../$SPOOLINGDIR/queue/requests/"*
    set -e
}


check_spooldirs_clean() {
    # test if all relevant spooling directories are empty, EXIT otherwise!
    for DIR in new cur ; do
        if ! spooldir_is_empty "$DIR" ; then
            echo "ERROR: unclean spooling directory '$DIR' found! Stopping."
            exit 1
        fi
    done
}


spooldir_is_empty() {
    # check if a given spool directory contains files
    if [ -z "$1" ] ; then
        echo "ERROR No spooling dir specified to check!"
        exit 255
    fi
    DIR="../../$SPOOLINGDIR/spool/$1/"
    COUNT=$(ls "$DIR" | wc -l)
    if [ $COUNT -eq 0 ] ; then
        # echo "No jobs in '$1' spooling directory!"
        return 0
    else
        echo "WARNING: found $COUNT jobfiles in '$1': $DIR"
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
    echo "Requesting QM status change to: $1"
    if ! qm_is_running ; then
        echo "ERROR: QM is not running! Stopping here."
        exit 3
    fi
    touch "$SPOOLINGDIR/queue/requests/$1"
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
        echo "ERROR: missing call to prepare_qm()."
        exit 253
    fi
    if qm_is_running ; then
        echo
        echo "****************************************************************"
        echo " ERROR: Queue Manager seems to be running already!"
        echo "  --> NOT starting another one to prevent unexpected behaviour."
        echo "****************************************************************"
        echo
        exit 1
    fi
    echo "**** Starting Queue Manager..."
    echo $QM_EXEC $QM_OPTS
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
    echo "QM process started."
}


submit_jobs() {
    # copy jobfiles with a given prefix into the spool/new directory to submit
    # the to a running queue manager
    if [ -z "$1" ] ; then
        echo "ERROR: no jobfile prefix given for submission!"
        exit 4
    fi
    # we are expected to be in the snijder base dir, so use the full path:
    for jobfile in tests/snijder-queue/inputs/$SHORT/${1}*.cfg ; do
        cp -v $jobfile "$SPOOLINGDIR/spool/new"
        sleep .1
    done

}


wait_for_hucore_to_finish() {
    # try to terminate any still-running hucore processes
    if hucore_is_running ; then
        if [ -n "$1" ] ; then
            echo "WARNING: Found running HuCore processes, waiting..."
            sleep $1
        fi
        if hucore_is_running ; then
            echo "==============================================================="
            echo "WARNING: Found running HuCore processes, trying to kill them..."
            echo "==============================================================="
            killall hucore.bin
        fi
    fi
}


wait_for_qm_to_finish() {
    # Wait a given number of seconds for the QM process to terminate,
    # otherwise try to shut it down (gracefully, using a shutdown request), or
    # try to kill it as a last resort.
    if qm_is_running ; then
        echo "QM is running..."
    fi
    for counter in $(seq 1 $1) ; do
        sleep 1
        if ! qm_is_running ; then
            echo "QM process terminated."
            wait_for_hucore_to_finish
            return
        fi
    done
    if qm_is_running ; then
        echo "WARNING: QM is STILL running after $1 seconds!"
        echo "Trying to shut it down..."
        qm_request shutdown
        sleep 1
    fi
    if qm_is_running ; then
        echo "WARNING: QM doesn't listen to our shutdown request!"
        echo "Trying to kill it..."
        pkill --signal HUP --full "$QM_EXEC"
        sleep 1
    fi
    if qm_is_running ; then
        echo "ERROR: QM doesn't react to HUP, giving up!!"
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
        echo "ERROR: queue file '$QFILE' doesn't exist!"
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
    if ! qm_is_running ; then
        echo "WARNING: QM is not running!"
        return
    fi
    for counter in $(seq 1 $1) ; do
        if queue_is_empty ; then
            echo "Queue is empty, trying to shut down the QM!"
            break
        fi
        sleep 1
    done
    if ! queue_is_empty ; then
        echo "==============================================================="
        echo "ERROR: Queue still not empty after $1 secondes!"
        echo "==============================================================="
    fi
    qm_request shutdown
    wait_for_qm_to_finish 5
}

msg_finished() {
    echo "************************* TEST FINISHED! *************************"
}


echo_red() {
    local blw='\033[00m'     # black-white
    local bred='\033[01;31m' # bold red
    echo -e "${bred}$*${blw}"
}


echo_green() {
    local blw='\033[00m'     # black-white
    local bgrn='\033[01;32m' # bold green
    echo -e "${bgrn}$*${blw}"
}


echo_yellow() {
    local blw='\033[00m'     # black-white
    local bylw='\033[01;33m' # bold yellow
    echo -e "${bylw}$*${blw}"
}



parse_shortname() {
    SHORT=$(basename $0 | sed 's,__.*,,')
    echo $SHORT
}

strip_runtime_strings() {
    # strips away various hashes that are runtime-specific, to make the result
    # better comparable among subsequent individual runs
    sed -u '''
        s/[0-9a-f]\{40\}/UID_STRIPPED/g
        s/App@[0-9a-f]\{12\}/App@APPID_STRIPPED/g
        s/[0-9]\{10\}\.[0-9]\{1,6\}/TIMESTAMP_STRIPPED/g
        s/cpu time: [0-9\.]*s ]]/CPUTIME_STRIPPED ]]/
        s/wall time: [0-9\.]*s ]]/WALLTIME_STRIPPED ]]/
        s/max memory: [0-9]*kB ]]/MAXMEM_STRIPPED ]]/
    '''
}



######################### INIT #########################
# run the init function immediately while we're sourced:
init
######################### INIT #########################
