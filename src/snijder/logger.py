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

LOGGER = logging.getLogger(LOGGER_NAME)
LOG_HANDLER = logging.StreamHandler()
LOG_FORMATTER = logging.Formatter('%(name)s [%(levelname)s] %(message)s')
LOG_HANDLER.setFormatter(LOG_FORMATTER)
LOGGER.addHandler(LOG_HANDLER)
LOGGER.setLevel(LOGLEVEL)

gc3libs.log = LOGGER
gc3libs.log.level = LOGLEVEL

logw = LOGGER.warn                                  # pylint: disable=C0103
logi = LOGGER.info                                  # pylint: disable=C0103
logd = LOGGER.debug                                 # pylint: disable=C0103
loge = LOGGER.error                                 # pylint: disable=C0103
logc = LOGGER.critical                              # pylint: disable=C0103


def set_loglevel(level):
    """Convenience function to adjust the loglevel."""
    mapping = {
        'debug'    : logging.DEBUG,
        'info'     : logging.INFO,
        'warn'     : logging.WARN,
        'error'    : logging.ERROR,
        'critical' : logging.CRITICAL
    }
    LOGGER.setLevel(mapping[level])


def set_verbosity(verbosity):
    """Convenience function to set loglevel from commandline arguments."""
    loglevel = logging.WARN - (verbosity * 10)
    LOGGER.setLevel(loglevel)
