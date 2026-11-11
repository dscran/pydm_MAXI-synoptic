"""Sets how often the PyDM Tango plugin polls attributes that send no change events."""

from __future__ import annotations

import logging
import os

from pydm import data_plugins

logger = logging.getLogger(__name__)

POLL_PERIOD_VARIABLE = "PYDM_TANGO_POLL_PERIOD"
TANGO_PROTOCOL = "tango"


def apply_poll_period(poll_period: float | None) -> None:
    """Pass the poll period (in seconds) to the Tango plugin, unless the environment already sets one.

    The plugin reads the variable only once, when it is loaded, so this must run before any channel exists.
    """
    if poll_period is None:
        return
    if TANGO_PROTOCOL in data_plugins.plugin_modules:
        logger.warning(
            "tango_poll_period has no effect: the Tango plugin was loaded before this panel started"
        )
    from_environment = os.environ.get(POLL_PERIOD_VARIABLE)
    if from_environment is not None:
        logger.info(
            "Tango poll period: %s ms from %s; tango_poll_period from the YAML is ignored",
            from_environment,
            POLL_PERIOD_VARIABLE,
        )
        return
    poll_period_ms = round(poll_period * 1000)
    os.environ[POLL_PERIOD_VARIABLE] = str(poll_period_ms)
    logger.info("Tango poll period: %d ms from tango_poll_period in the YAML", poll_period_ms)
