# ![Snijder logo][img_snijder_logo] Snijder

The _Snijder_ project provides a Python package managing one or more job-queues
for multiple users in a simple, accessible way. Flexibility and maintainability
have priority over performance, as the targeted jobs will run in the range of
minutes to hours, so being able to process thousands of queue-requests per
second is just not important here.

_Snijder_ is an acronym for
* **`S`** ingle
* **`N`** ode
* **`I`** nhomogeneous
* **`J`** ob
* **`D`** ispatcher,
* **`E`** xecutor and
* **`R`** eporter

Initially it was created to replace the queue manager of the [Huygens Remote
Manager (HRM)](http://huygens-rm.org/) but from a technical perspective
_Snijder_ is completely independent of that project and is actually used for
other tasks as well.


## Under The Hood

_Snijder_ makes use of the [GC3Pie](https://github.com/imcf/gc3pie) Python
package dealing with job dispatching, monitoring, data transfer and cluster
queueing systems.

## Installation

### GC3Pie Setup

To install GC3Pie a few additional packages are required. On Debian / Ubuntu
systems, simply run this command to prepare the installation:

```bash
sudo apt install \
    gcc \
    make \
    git \
    time \
    python-virtualenv \
    python-dev \
    libffi-dev \
    libssl-dev
```

Then follow the instructions below to set up GC3Pie in a directory structure
underneath `/opt/snijder`. 

First, make sure the base directory is there and writable to the installatoin
user. Run the following commands as `root` or use `sudo`, depending on your
preferences:

```bash
BASE_DIR="/opt/snijder"
SNIJDER_USER="snijder"
SNIJDER_GROUP="snijder"

mkdir -pv $BASE_DIR
chown $SNIJDER_USER:$SNIJDER_GROUP $BASE_DIR
```

Then, as the above configured `$SNIJDER_USER` run:

```bash
BASE_DIR="/opt/snijder"
GC3VER="2.5.0"
GC3HOME="$BASE_DIR/venvs/gc3pie_$GC3VER"

virtualenv --system-site-packages $GC3HOME
source $GC3HOME/bin/activate

pip install --upgrade pip
pip install --upgrade pycli prettytable docutils

CURDIR=$(pwd)

cd $BASE_DIR
git clone https://github.com/uzh/gc3pie.git gc3pie.git

cd gc3pie.git
git checkout -b tag-$GC3VER tags/v$GC3VER
env CC=gcc ./setup.py install

cd $CURDIR
```

### Snijder Setup

* clone the snijder repo
* create a base directory for all spooling stuff:
  ```bash
  SPOOL_BASE="/opt/spool"  # adapt as you like, e.g. "/scratch/spool" or similar
  mkdir -pv "$SPOOL_BASE/snijder"
  mkdir -pv "$SPOOL_BASE/gc3/resourcedir"
  cd /opt
  git clone https://github.com/imcf/snijder.git
  cd snijder
  ln -s resources/config
  ```

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


[img_snijder_logo]: https://raw.githubusercontent.com/imcf/snijder/master/resources/artwork/snijder-logo-blue-64.png