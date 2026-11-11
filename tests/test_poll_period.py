import os
import logging

import pytest
from pydm import data_plugins

from synoptic.poll_period import POLL_PERIOD_VARIABLE, apply_poll_period


@pytest.fixture(autouse=True)
def clean_state(monkeypatch, caplog):
    monkeypatch.delenv(POLL_PERIOD_VARIABLE, raising=False)
    monkeypatch.setattr(data_plugins, "plugin_modules", {})
    caplog.set_level(logging.INFO)


def test_poll_period_from_yaml(monkeypatch, caplog):
    # monkeypatch restores the environment after the test, also for variables set by the code under test
    monkeypatch.setenv(POLL_PERIOD_VARIABLE, "placeholder")
    monkeypatch.delenv(POLL_PERIOD_VARIABLE)
    apply_poll_period(0.5)
    assert os.environ[POLL_PERIOD_VARIABLE] == "500"
    assert "500 ms" in caplog.text
    assert "WARNING" not in caplog.text


def test_environment_variable_wins(monkeypatch, caplog):
    monkeypatch.setenv(POLL_PERIOD_VARIABLE, "2000")
    apply_poll_period(0.5)
    assert os.environ[POLL_PERIOD_VARIABLE] == "2000"
    assert "2000 ms" in caplog.text
    assert "ignored" in caplog.text


def test_no_poll_period_in_yaml(caplog):
    apply_poll_period(None)
    assert POLL_PERIOD_VARIABLE not in os.environ
    assert caplog.text == ""


def test_plugin_already_loaded(monkeypatch, caplog):
    monkeypatch.setenv(POLL_PERIOD_VARIABLE, "placeholder")
    monkeypatch.delenv(POLL_PERIOD_VARIABLE)
    monkeypatch.setitem(data_plugins.plugin_modules, "tango", object())
    apply_poll_period(0.5)
    assert "WARNING" in caplog.text
    assert "no effect" in caplog.text
