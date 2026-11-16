import json
import logging
import sys

import pytest

from maxi_synoptic import cli

PANEL_FILES = ["--stylesheet", str(cli.STYLE_SHEET), str(cli.UI_FILE)]


@pytest.fixture
def sim_signals():
    return json.loads(cli.BUNDLED_CONFIGS["sim"].read_text())


@pytest.fixture
def write_config(tmp_path):
    def write(content):
        path = tmp_path / "panel.json"
        path.write_text(content if isinstance(content, str) else json.dumps(content))
        return path

    return write


def macros_of(argv):
    return json.loads(argv[argv.index("-m") + 1])


def config_errors_of(args):
    with pytest.raises(cli.ConfigError) as failure:
        cli.pydm_argv(args)
    return failure.value.errors


# Configuration selection


def test_default_configuration():
    default_signals = json.loads(cli.BUNDLED_CONFIGS["default"].read_text())
    assert cli.config_path("default") == cli.RESOURCES_DIR / "default.json"
    assert macros_of(cli.pydm_argv([])).items() >= default_signals.items()


def test_bundled_simulator_configuration(sim_signals):
    assert cli.config_path("sim") == cli.RESOURCES_DIR / "sim.json"
    assert macros_of(cli.pydm_argv(["--config", "sim"])).items() >= sim_signals.items()


def test_relative_path_from_current_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert cli.config_path("other.json") == tmp_path / "other.json"
    assert cli.config_path("./configs/other") == tmp_path / "configs" / "other"


def test_absolute_path():
    assert cli.config_path("/etc/maxi/panel.json") == cli.Path("/etc/maxi/panel.json")


def test_unknown_bundled_name():
    (error,) = config_errors_of(["--config", "simulator"])
    assert "'simulator' is not a bundled configuration" in error
    assert "default" in error and "sim" in error


def test_missing_file(tmp_path):
    (error,) = config_errors_of(["--config", str(tmp_path / "none.json")])
    assert "none.json" in error


# Configuration check


def test_missing_signal(write_config, sim_signals):
    del sim_signals["shutter_open"]
    (error,) = config_errors_of(["--config", str(write_config(sim_signals))])
    assert "'shutter_open' is missing" in error


def test_old_valve_signal(write_config, sim_signals):
    sim_signals["valve_open"] = sim_signals.pop("valve_state")
    (error,) = config_errors_of(["--config", str(write_config(sim_signals))])
    assert "'valve_state' is missing" in error


def test_several_errors_together(write_config, sim_signals):
    del sim_signals["shutter_open"], sim_signals["valve_state"]
    sim_signals["detector_temp"] = 12
    errors = config_errors_of(["--config", str(write_config(sim_signals))])
    assert len(errors) == 3
    assert any("'shutter_open'" in error for error in errors)
    assert any("'valve_state'" in error for error in errors)
    assert any("'detector_temp'" in error and "12" in error for error in errors)


def test_invalid_json_names_file_and_line(write_config, sim_signals):
    text = json.dumps(sim_signals, indent=2).replace('#dbase=no"\n}', '#dbase=no",\n}')
    path = write_config(text)
    (error,) = config_errors_of(["--config", str(path)])
    assert str(path) in error
    # the line of the trailing comma: "{" and one line per signal
    assert f"line {len(sim_signals) + 1}:" in error


def test_not_an_object(write_config):
    (error,) = config_errors_of(["--config", str(write_config(["maxi_vac_pressure"]))])
    assert "JSON object" in error


def test_wrong_address_is_not_checked(write_config, sim_signals):
    sim_signals["maxi_vac_pressure"] = "tango://localhost:45678/no/such/device/pressure#dbase=no"
    argv = cli.pydm_argv(["--config", str(write_config(sim_signals))])
    assert macros_of(argv)["maxi_vac_pressure"] == sim_signals["maxi_vac_pressure"]


# Unused signals warn


def test_unused_signal_warns(write_config, sim_signals, caplog):
    sim_signals["spare_gauge"] = "tango://localhost:45678/maxi/sim/1/spare#dbase=no"
    with caplog.at_level(logging.WARNING, logger=cli.__name__):
        argv = cli.pydm_argv(["--config", str(write_config(sim_signals))])
    assert argv[-1] == str(cli.UI_FILE)
    assert [record.getMessage() for record in caplog.records if "spare_gauge" in record.getMessage()]


def test_bundled_configurations_have_no_unused_signals(caplog):
    with caplog.at_level(logging.WARNING, logger=cli.__name__):
        for name in cli.BUNDLED_CONFIGS:
            cli.pydm_argv(["--config", name])
    assert caplog.records == []


# Panel command


def test_pydm_command_line(sim_signals):
    argv = cli.pydm_argv(["--config", "sim"])
    assert argv[0] == "pydm"
    assert argv[-3:] == PANEL_FILES


def test_signal_used_only_in_calc_channel_is_needed():
    assert {"diode_amplification", "diode_encoder", "shutter_panel_mode"} <= cli.panel_signals()
    assert not any(name.endswith(cli.CALC_SUFFIX) for name in cli.panel_signals())


def test_calc_macros_have_encoded_hash(sim_signals):
    macros = macros_of(cli.pydm_argv(["--config", "sim"]))
    assert macros["valve_state_calc"] == sim_signals["valve_state"].replace("#", "%23")
    assert macros["shutter_open_calc"] == sim_signals["shutter_open"].replace("#", "%23")
    assert "#" not in macros["valve_state_calc"]


def test_pydm_options_pass_through():
    argv = cli.pydm_argv(["--config", "sim", "--hide-nav-bar", "--log_level", "DEBUG"])
    assert argv[1:4] == ["--hide-nav-bar", "--log_level", "DEBUG"]


def test_help_goes_to_pydm():
    assert "--help" in cli.pydm_argv(["--help"])


@pytest.mark.parametrize("option", [["-m", "config=sim"], ["--macro", '{"maxi_vac_pressure": "x"}']])
def test_macro_option_is_an_error(option, capsys):
    with pytest.raises(SystemExit):
        cli.pydm_argv(option)
    assert "--config" in capsys.readouterr().err


def test_main_starts_pydm(monkeypatch):
    started_with = []
    monkeypatch.setattr(sys, "argv", ["maxi-synoptic", "--config", "sim"])
    monkeypatch.setattr(cli, "pydm_main", lambda: started_with.append(list(sys.argv)))
    cli.main()
    assert started_with == [cli.pydm_argv(["--config", "sim"])]


def test_main_reports_configuration_errors(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["maxi-synoptic", "--config", "simulator"])
    monkeypatch.setattr(cli, "pydm_main", lambda: pytest.fail("PyDM must not start"))
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert "simulator" in str(stop.value.code)


# Tango plugin check


def test_missing_tango_plugin(monkeypatch):
    real_find_spec = cli.importlib.util.find_spec

    def find_spec(name, *args):
        return None if name == cli.TANGO_PLUGIN_MODULE else real_find_spec(name, *args)

    monkeypatch.setattr(cli.importlib.util, "find_spec", find_spec)
    monkeypatch.setattr(sys, "argv", ["maxi-synoptic", "--config", "sim"])
    monkeypatch.setattr(cli, "pydm_main", lambda: pytest.fail("PyDM must not start"))
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert "Tango data plugin" in str(stop.value.code)
    assert "dschick/pydm" in str(stop.value.code)
