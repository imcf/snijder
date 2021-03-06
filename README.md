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

[![Code style: black][img_codestyle_black]](https://github.com/psf/black)

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

To set up _Snijder_ you need to create a base directory where all the spooling /
queueing will take place, then you're good to clone the repository:

```bash
sudo apt install python-pyinotify

SPOOL_BASE="/opt/spool"  # adapt as you like, e.g. "/scratch/spool" or similar

mkdir -pv "$SPOOL_BASE/snijder"
mkdir -pv "$SPOOL_BASE/gc3/resourcedir"

cd $BASE_DIR
git clone https://github.com/imcf/snijder.git


if [ -z "$VIRTUAL_ENV" ] ; then
    source $BASE_DIR/venvs/gc3pie_2.5.0/bin/activate
fi

pip install --upgrade psutil

# TEMPORARY SETUP using a symlink:
cd $VIRTUAL_ENV/lib/python2.7
ln -s $BASE_DIR/snijder/src/snijder
```

For testing purposes, there is a symlink provided to an example configuration in the
`config/` directory. If you need to use a different configuration, simply remove the
link and/or replace the file.

## Example

The testing scripts mentioned below also serve as a very nice example to see
_Snijder_ in action. To run the spooler / queue manager manually, use the
following command (from within the Python virtualenv created above):

```bash
if [ -z "$VIRTUAL_ENV" ] ; then
    source $BASE_DIR/venvs/gc3pie_2.5.0/bin/activate
fi
cd $BASE_DIR/snijder

bin/snijder-queue --spooldir $SPOOL_BASE/snijder --config config/gc3pie/localhost.conf -v
```

From there on you're ready to submit jobs through the configured spooling
directories, e.g. like so:

```bash
cp -v tests/snijder-queue/jobfiles/decon_it-3_user01.cfg $SPOOL_BASE/snijder/spool/new/
```

## Testing

To run the tests provided in `tests/snijder-queue` you need some sample input
files which are not part of this repository, as they are large binary files. See
the next section on how to get them.

### HuCore Test Images

The test images for deconvolution are a set of images which can be downloaded
from the [SVI website](https://svi.nl/DemoImages) (requires registration).
Simply place them in `resources/sample_data/hucore/` to run the tests.

### Running the tests

Once the sample images are there, you can just launch the test runner. Make sure
to have the Python virtualenv activated that was created above, then:

```bash
cd $BASE_DIR/snijder
tests/snijder-queue/run_tests.sh
```

## Contributing

Please see the details in the [Development And Contribution
Guide](CONTRIBUTING.md).

[img_snijder_logo]: https://raw.githubusercontent.com/imcf/snijder/master/resources/artwork/snijder-logo-blue-64.png
[img_codestyle_black]: https://img.shields.io/badge/code%20style-black-000000.svg
