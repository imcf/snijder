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

To set up _Snijder_ you need to create a base directory where all the spooling /
queueing will take place, then you're good to clone the repository:

```bash
sudo apt install python-pyinotify

SPOOL_BASE="/opt/spool"  # adapt as you like, e.g. "/scratch/spool" or similar
mkdir -pv "$SPOOL_BASE/snijder"
mkdir -pv "$SPOOL_BASE/gc3/resourcedir"

cd /opt/snijder
git clone https://github.com/imcf/snijder.git
```

For testing you can simply use the configuration files provided with the repo,
to enable them just run these commands:

```bash
cd /opt/snijder/snijder
ln -s resources/config
```

## Example

The testing scripts also serve as a very nice example to see _Snijder_ in
action. To launch them, simply call the corresponding wrapper script from within
the base directory like so:

```bash
cd /opt/snijder/snijder
tests/snijder-queue/run_tests.sh
```

## Testing

The scripts in `tests/snijder-queue` require some sample input files which are
not part of this repository, as they are large binary files. Here's how to get
them:

### HuCore Test Images - `resources/sample_data/hucore/`

The test images for deconvolution are a set of images which can be downloaded
from the [SVI website](https://svi.nl/DemoImages) (requires registration).
Simply place them in `resources/sample_data/hucore/` to run the tests.

## Contributing

Please see the details in the [Development And Contribution
Guide](CONTRIBUTING.md).

[img_snijder_logo]: https://raw.githubusercontent.com/imcf/snijder/master/resources/artwork/snijder-logo-blue-64.png