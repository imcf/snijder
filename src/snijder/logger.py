# -*- coding: utf-8 -*-
"""
Logging helper module.
"""

import logging
import gc3libs

__all__ = ["logw", "logi", "logd", "loge", "logc"]

LOGLEVEL = logging.WARN

ROOT_LOGGER = logging.getLogger()
LOG_FORMATTER = logging.Formatter('%(name)s [%(levelname)s] %(message)s')
LOG_HANDLER = logging.StreamHandler()
LOG_HANDLER.setFormatter(LOG_FORMATTER)
ROOT_LOGGER.addHandler(LOG_HANDLER)

LOGGER = logging.getLogger('snijder')
LOGGER.setLevel(LOGLEVEL)

gc3libs.log = logging.getLogger('gc3libs')
gc3libs.log.level = logging.WARN

logw = LOGGER.warn                                  # pylint: disable=C0103
logi = LOGGER.info                                  # pylint: disable=C0103
logd = LOGGER.debug                                 # pylint: disable=C0103
loge = LOGGER.error                                 # pylint: disable=C0103
logc = LOGGER.critical                              # pylint: disable=C0103

LEVEL_MAPPING = {
    'debug'    : logging.DEBUG,
    'info'     : logging.INFO,
    'warn'     : logging.WARN,
    'error'    : logging.ERROR,
    'critical' : logging.CRITICAL
}


def set_loglevel(level):
    """Convenience function to adjust the loglevel.

    Parameters
    ----------
    level : str
        A string matching one of the keys from the _MAPPING dict.
    """
    LOGGER.setLevel(LEVEL_MAPPING[level])


def set_verbosity(verbosity):
    """Convenience function to set loglevel from commandline arguments.

    Parameters
    ----------
    verbosity : int
        An int between 0 and 2, indicating the logging verbosity level.
    """
    loglevel = logging.WARN - (verbosity * 10)
    LOGGER.setLevel(loglevel)


def set_gc3loglevel(level):
    """Set the logging level for gc3libs.

    Parameters
    ----------
    level : str
        A string matching one of the keys from the _MAPPING dict.
    """
    gc3libs.log.level = LEVEL_MAPPING[level]
