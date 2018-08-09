import sys
import time

import gc3libs

import pyinotify
import pprint

import snijder

import logging

loglevel = logging.WARN
gc3libs.configure_logger(loglevel, "qmgc3")
logw = gc3libs.log.warn
logi = gc3libs.log.info
logd = gc3libs.log.debug

fname = '/path/to/some/snijderjob.cfg'

job = snijder.JobDescription(fname, 'file')
