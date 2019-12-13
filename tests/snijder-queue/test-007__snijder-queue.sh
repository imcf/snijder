#!/bin/bash

# exit on any error:
set -e

# remember path prefix as called, source functions
PFX=$(dirname $0)
source "$PFX/functions.inc.sh"

echo
colr yellow 'Test has been superseded / replaced by pytest:
- tests/pytest/test_queue.py::test_joblist
- tests/pytest/test_queue.py::test_add_remove_jobs
- tests/pytest/test_queue.py::test_add_duplicate_jobs
'

msg_finished

