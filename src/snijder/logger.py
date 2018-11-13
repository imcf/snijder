# -*- coding: utf-8 -*-
"""
Logging helper module.
"""

import logging
import gc3libs

__all__ = ["logw", "logi", "logd", "loge", "logc"]

# we set a default loglevel and add some shortcuts for logging:
LOGLEVEL = logging.WARN
LOGGER_NAME = "snijder"

logger = logging.getLogger(LOGGER_NAME)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('gc3.gc3libs: %(levelname)s: %(message)s')
# _formatter = logging.Formatter('%(name)s [%(levelname)s]: %(message)s')
_handler.setFormatter(_formatter)
logger.addHandler(_handler)
logger.setLevel(LOGLEVEL)

gc3libs.log = logger
gc3libs.log.level = LOGLEVEL

logw = gc3libs.log.warn
logi = gc3libs.log.info
logd = gc3libs.log.debug
loge = gc3libs.log.error
logc = gc3libs.log.critical


def set_loglevel(level):
    """Convenience function to adjust the loglevel."""
    mapping = {
        'debug'    : logging.DEBUG,
        'info'     : logging.INFO,
        'warn'     : logging.WARN,
        'error'    : logging.ERROR,
        'critical' : logging.CRITICAL
    }
    logger.setLevel(mapping[level])


def set_verbosity(verbosity):
    """Convenience function to set loglevel from commandline arguments."""
    loglevel = logging.WARN - (verbosity * 10)
    logger.setLevel(loglevel)
