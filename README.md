# Snijder

Snijder is an acronym for "Single Node Inhomogeneous Job Dispatcher, Executor
and Reporter".

This project provides a Python package managing one or more job-queues for
multiple users in a simple, accessible way. Flexibility and maintainability
have priority over performance, as the targeted jobs will run in the range of
minutes to hours, so being able to process thousands of queue-requests per
second is just not important here.

Initially it was created to replace the queue manager of the [Huygens Remote
Manager (HRM)](http://huygens-rm.org/) but Snijder is independent of that
project and is actually used for other tasks as well.

## Requirements

Snijder makes use of the [GC3Pie](https://github.com/imcf/gc3pie) Python
package dealing with job dispatching, monitoring, data transfer and cluster
queueing systems.

## Example

ToDo!

## Testing

The scripts in `tests/snijder` require some sample input files which are not
part of this repository, as they are large binary files. Here's how to get
them:

### HuCore Test Images - `var/sample_data/hucore/`

The test images for deconvolution are currently the basic set of images which
can be downloaded from the [SVI website](https://svi.nl/DemoImages) (requires
registration). Simply place them in
