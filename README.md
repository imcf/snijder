# ![Snijder logo][img_snijder_logo] Snijder

_Snijder_ is an acronym for "**S**ingle **N**ode **I**nhomogeneous **J**ob
**D**ispatcher, **E**xecutor and **R**eporter".

This project provides a Python package managing one or more job-queues for
multiple users in a simple, accessible way. Flexibility and maintainability
have priority over performance, as the targeted jobs will run in the range of
minutes to hours, so being able to process thousands of queue-requests per
second is just not important here.

Initially it was created to replace the queue manager of the [Huygens Remote
Manager (HRM)](http://huygens-rm.org/) but from a technical perspective
_Snijder_ is completely independent of that project and is actually used for
other tasks as well.


## Requirements

_Snijder_ makes use of the [GC3Pie](https://github.com/imcf/gc3pie) Python
package dealing with job dispatching, monitoring, data transfer and cluster
queueing systems. Unfortunately, the latest release (2.4.2) contains a few bugs
which prevent _Snijder_ from operating correctly. Therefore it is recommended to
set up GC3Pie from its `master` branch, following the instructions for [manual
installation](http://gc3pie.readthedocs.io/en/master/users/install.html#manual-installation).


## Example

ToDo!


## Testing

The scripts in `tests/snijder-queue` require some sample input files which are
not part of this repository, as they are large binary files. Here's how to get
them:

### HuCore Test Images - `resources/sample_data/hucore/`

The test images for deconvolution are a set of images which can be downloaded
from the [SVI website](https://svi.nl/DemoImages) (requires registration).
Simply place them in `resources/sample_data/hucore/` to run the tests.


## Project Structure

The directory layout tries to follow the suggestions about clean Python project
structuring found in the following online resources:

* [Open Sourcing a Python Project the Right Way](https://jeffknupp.com/blog/2013/08/16/open-sourcing-a-python-project-the-right-way/)
* [Structuring Your Project](http://python-guide-pt-br.readthedocs.io/en/latest/writing/structure/)
* [Structure of a Python Project](http://www.patricksoftwareblog.com/structure-of-a-python-project/)
* [Repository Structure and Python](https://www.kennethreitz.org/essays/repository-structure-and-python)
* [A Project Skeleton](https://learnpythonthehardway.org/book/ex46.html)
* [SO: What is the best project structure for a Python application?](http://stackoverflow.com/questions/193161/what-is-the-best-project-structure-for-a-python-application)


[img_snijder_logo]: https://raw.githubusercontent.com/imcf/snijder/master/resources/artwork/snijder-logo-blue-240.png