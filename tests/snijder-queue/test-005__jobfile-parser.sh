#!/bin/bash

# exit on any error:
set -e

# remember path prefix as called, source functions
PFX=$(dirname $0)
source "$PFX/functions.inc.sh"

echo
colr yellow 'Test has been superseded / replaced by pytest:
- tests/pytest/test_jobs.py::test_snijder_job_config_parser_valid_jobfiles
- tests/pytest/test_jobs.py::test_snijder_job_config_parser_invalid_jobfiles
'

msg_finished

