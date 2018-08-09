Tests to write
--------------

* valid job with non-existing input files
* format of queue status file (`var/snijder-queue/queue/status/hucore.json`)
* check if hucore runs actually produced output files
* using the jobfile containing absolute paths (`decon_it-3_user01_abspath.cfg`)

Other tasks
-----------

* clean up "var/snijder-queue/spool/" (verbosely!) after tests are run!!
* split tests into "integration" and "unit tests"
  * integration: full queue manager / spooler runs, parsing jobfiles etc.
  * unit tests: Python snippets testing specific functionality
