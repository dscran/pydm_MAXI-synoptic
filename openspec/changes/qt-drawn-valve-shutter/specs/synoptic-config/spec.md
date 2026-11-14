# Spec Delta

## MODIFIED Requirements

### Requirement: Signal configuration
The configuration SHALL be a JSON object that maps each signal name of the panel to the full channel address of its Tango attribute, for example `"maxi_vac_pressure": "tango://maxi-ctrl:10000/maxi/vac/chamber_gauge/pressure"`. The signal names are the simulator's attribute names: one per value slot, plus `valve_state` and `shutter_open`. Each address is used unchanged.

#### Scenario: Signal used by several widgets
- **WHEN** `maxi_vac_pressure` is set to an address
- **THEN** the chamber pressure label, the chamber pressure plot and the `MAXICHAMBER` colour all use that address

#### Scenario: Address without a database
- **WHEN** a signal is set to `tango://localhost:45678/maxi/sim/1/valve_state#dbase=no`
- **THEN** the panel reads that attribute from the simulator without a Tango database

#### Scenario: Old valve signal
- **WHEN** a configuration has `valve_open` but no `valve_state`
- **THEN** the panel does not start and reports that `valve_state` is missing
