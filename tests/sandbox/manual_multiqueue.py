import snijder
import snijder.queue
from snijder.jobs import process_jobfile
from snijder.logger import set_verbosity, set_gc3loglevel
from snijder.spooler import JobSpooler
from snijder.inotify import JobFileHandler

set_verbosity(2)

huqueue = snijder.queue.JobQueue()

spooler = JobSpooler('/tmp/tmp.k6CRyV6Abe', queue=huqueue, gc3conf='resources/config/gc3pie/localhost.conf')
spooler.queues
spooler.add_queue(queue=huqueue, queue_name='hucore')

twoqueue = snijder.queue.JobQueue()
spooler.add_queue(queue=twoqueue, queue_name='2ndqueue')

spooler.queues
twoqueue.statusfile

spooler.add_queue(queue=twoqueue, queue_name='3rdqueue')

for quid in spooler.queues:
    print spooler.queues[quid].statusfile

spooler.refresh()
