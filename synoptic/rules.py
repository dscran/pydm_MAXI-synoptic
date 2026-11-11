"""Rules that change SVG elements from channel values.

A color rule sets the fill of one element. A state rule shows one of several elements. Both are plain
functions, registered with a decorator. The framework decides when a value is unknown, so a rule
function only ever gets a usable value.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from numbers import Integral, Real
from typing import Any, Callable, Iterable, Protocol

from pydm.widgets.channel import PyDMChannel
from qtpy.QtCore import QObject

logger = logging.getLogger(__name__)

UNKNOWN_COLOR = "#6b7480"
INVALID_SEVERITY = 3

REGISTRY: list[ColorRule | StateRule] = []


class RuleView(Protocol):
    """What a rule needs from the SVG view."""

    def set_fill(self, element_id: str, color: str) -> None: ...
    def set_hatched(self, element_id: str, is_hatched: bool) -> None: ...
    def set_visible(self, element_id: str, is_visible: bool) -> None: ...


@dataclass(frozen=True)
class ColorRule:
    """Sets the fill of `target` to the color that `callback` returns for a number."""

    channel: str
    target: str
    callback: Callable[[float], str]

    @property
    def element_ids(self) -> frozenset[str]:
        return frozenset({self.target})

    def can_use(self, value: Any) -> bool:
        is_number = isinstance(value, Real) and not isinstance(value, bool)
        return is_number and not math.isnan(value)

    def show(self, view: RuleView, value: float) -> bool:
        """Show the look for a usable value. Returns False if the callback gave no usable result."""
        color = self.callback(value)
        if not isinstance(color, str):
            logger.error("Color rule for %s returned %r instead of a color", self.target, color)
            return False
        view.set_fill(self.target, color)
        view.set_hatched(self.target, False)
        return True

    def show_unknown(self, view: RuleView) -> None:
        view.set_fill(self.target, UNKNOWN_COLOR)
        view.set_hatched(self.target, True)


@dataclass(frozen=True)
class StateRule:
    """Shows the one element of `assets` that `callback` returns for a boolean, or `unknown`."""

    channel: str
    assets: frozenset[str]
    unknown: str
    callback: Callable[[bool], str]

    @property
    def element_ids(self) -> frozenset[str]:
        return self.assets | {self.unknown}

    def can_use(self, value: Any) -> bool:
        # The Tango plugin sends a DevBoolean as the int 0 or 1
        return isinstance(value, Integral) and value in (0, 1)

    def show(self, view: RuleView, value: bool) -> bool:
        """Show the asset for a usable value. Returns False if the callback gave no declared asset."""
        asset = self.callback(bool(value))
        if asset not in self.assets:
            logger.error(
                "State rule for channel %r returned %r, not one of %s",
                self.channel,
                asset,
                sorted(self.assets),
            )
            return False
        self._show_only(view, asset)
        return True

    def show_unknown(self, view: RuleView) -> None:
        self._show_only(view, self.unknown)

    def _show_only(self, view, shown_id):
        for element_id in self.element_ids:
            view.set_visible(element_id, element_id == shown_id)


def color_rule(channel: str, target: str) -> Callable:
    """Register a function `value -> color` that sets the fill of the SVG element `target`."""

    def register(callback):
        REGISTRY.append(ColorRule(channel, target, callback))
        return callback

    return register


def state_rule(channel: str, assets: Iterable[str], unknown: str) -> Callable:
    """Register a function `bool -> asset id` that shows one of `assets`, or `unknown` without a value."""

    def register(callback):
        REGISTRY.append(StateRule(channel, frozenset(assets), unknown, callback))
        return callback

    return register


def registered_rules() -> list[ColorRule | StateRule]:
    return list(REGISTRY)


def bands(value: float, limits: Iterable[tuple[float, str]], above: str) -> str:
    """Return the result of the first `(upper, result)` in `limits` with `value <= upper`, else `above`."""
    for upper, result in limits:
        if value <= upper:
            return result
    return above


class RuleBinding(QObject):
    """Applies one rule to a view, from the connection state, value and severity of its channel.

    Give it the view as `parent` if the view is a widget: Qt then stops calling the binding as soon as
    the view is destroyed.
    """

    def __init__(self, rule: ColorRule | StateRule, view: RuleView, parent: QObject | None = None):
        super().__init__(parent)
        self.rule = rule
        self._view = view
        self._is_connected = False
        self._value = None
        self._severity = None
        self._channel = None
        self._apply()

    def connect(self, address: str) -> None:
        """Start receiving the channel at `address`."""
        self._channel = PyDMChannel(
            address=address,
            connection_slot=self.connection_changed,
            value_slot=self.value_changed,
            severity_slot=self.severity_changed,
        )
        self._channel.connect()

    def disconnect(self) -> None:
        """Release the channel. Call this when the view is destroyed."""
        if self._channel is not None:
            # Qt disconnects the slots of a destroyed object by itself
            self._channel.disconnect(destroying=True)
            self._channel = None

    def connection_changed(self, is_connected: bool) -> None:
        self._is_connected = bool(is_connected)
        if not self._is_connected:
            # A value from before the disconnect says nothing about the state after reconnecting
            self._value = None
        self._apply()

    def value_changed(self, value: Any) -> None:
        self._value = value
        self._apply()

    def severity_changed(self, severity: int) -> None:
        self._severity = severity
        self._apply()

    def is_unknown(self) -> bool:
        if not self._is_connected or self._severity == INVALID_SEVERITY:
            return True
        return self._value is None or not self.rule.can_use(self._value)

    def _apply(self):
        if self.is_unknown() or not self._show_value():
            self.rule.show_unknown(self._view)

    def _show_value(self):
        try:
            return self.rule.show(self._view, self._value)
        except Exception:
            logger.exception("Rule for channel %r failed for value %r", self.rule.channel, self._value)
            return False
