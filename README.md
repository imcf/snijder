# Snijder

Snijder is an acronym for "Single Node Inhomogeneous Job Dispatcher, Executor
and Reporter".

This project provides a Python package managing one or more job-queues for
multiple users in a simple, accessible way. Flexibility and maintainability
have priority over performance, as the targeted jobs will run in the range of
minutes to hours, so being able to process thousands of queue-requests per
second is just not important.

## Requirements

Snijder makes use of the gc3pie Python package dealing with job dispatching,
monitoring, data transfer and cluster queueing systems.

## Example

ToDo!
