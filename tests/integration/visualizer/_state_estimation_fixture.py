# SPDX-FileCopyrightText: Contributors to the Power Grid Model project <powergridmodel@lfenergy.org>
#
# SPDX-License-Identifier: MPL-2.0

"""Small state-estimation network for integration tests.

Based on the Power Grid Model workshop State Estimation Example.
"""

from power_grid_model import (
    AngleMeasurementType,
    AttributeType,
    ComponentType,
    DatasetType,
    LoadGenType,
    MeasuredTerminalType,
    initialize_array,
)


def make_state_estimation_input_data():
    # node
    node = initialize_array(DatasetType.input, ComponentType.node, 3)
    node[AttributeType.id] = [1, 2, 6]
    node[AttributeType.u_rated] = [10.5e3, 10.5e3, 10.5e3]

    # line
    line = initialize_array(DatasetType.input, ComponentType.line, 3)
    line[AttributeType.id] = [3, 5, 8]
    line[AttributeType.from_node] = [1, 2, 1]
    line[AttributeType.to_node] = [2, 6, 6]
    line[AttributeType.from_status] = [1, 1, 1]
    line[AttributeType.to_status] = [1, 1, 1]
    line[AttributeType.r1] = [0.25, 0.25, 0.25]
    line[AttributeType.x1] = [0.2, 0.2, 0.2]
    line[AttributeType.c1] = [10e-6, 10e-6, 10e-6]
    line[AttributeType.tan1] = [0.0, 0.0, 0.0]
    line[AttributeType.i_n] = [1000, 1000, 1000]

    # load
    sym_load = initialize_array(DatasetType.input, ComponentType.sym_load, 2)
    sym_load[AttributeType.id] = [4, 7]
    sym_load[AttributeType.node] = [2, 6]
    sym_load[AttributeType.status] = [1, 1]
    sym_load[AttributeType.type] = [LoadGenType.const_power, LoadGenType.const_power]
    sym_load[AttributeType.p_specified] = [20e6, 10e6]
    sym_load[AttributeType.q_specified] = [5e6, 2e6]

    # source
    source = initialize_array(DatasetType.input, ComponentType.source, 1)
    source[AttributeType.id] = [10]
    source[AttributeType.node] = [1]
    source[AttributeType.status] = [1]
    source[AttributeType.u_ref] = [1.0]

    # voltage sensor
    sym_voltage_sensor = initialize_array(DatasetType.input, ComponentType.sym_voltage_sensor, 3)
    sym_voltage_sensor[AttributeType.id] = [11, 12, 13]
    sym_voltage_sensor[AttributeType.measured_object] = [1, 2, 6]
    sym_voltage_sensor[AttributeType.u_sigma] = [1.0, 1.0, 1.0]
    sym_voltage_sensor[AttributeType.u_measured] = [10489.37, 9997.32, 10102.01]
    sym_voltage_sensor[AttributeType.u_angle_measured] = [0.0, 0.0, 0.0]

    # power sensor
    sym_power_sensor = initialize_array(DatasetType.input, ComponentType.sym_power_sensor, 5)
    sym_power_sensor[AttributeType.id] = [14, 15, 16, 17, 18]
    sym_power_sensor[AttributeType.measured_object] = [3, 5, 8, 4, 6]
    sym_power_sensor[AttributeType.measured_terminal_type] = [
        MeasuredTerminalType.branch_to,
        MeasuredTerminalType.branch_from,
        MeasuredTerminalType.branch_to,
        MeasuredTerminalType.load,
        MeasuredTerminalType.node,
    ]
    sym_power_sensor[AttributeType.power_sigma] = [1.0e3, 1.0e3, 1.0e3, 1.0e3, 1.0e3]
    sym_power_sensor[AttributeType.p_measured] = [-1.66e07, -3.36e06, -1.33e07, 20e6, -10e6]
    sym_power_sensor[AttributeType.q_measured] = [-3.82e06, -1.17e06, -2.88e06, 5e6, -2e6]

    # current sensor
    sym_current_sensor = initialize_array(DatasetType.input, ComponentType.sym_current_sensor, 3)
    sym_current_sensor[AttributeType.id] = [19, 20, 21]
    sym_current_sensor[AttributeType.measured_object] = [3, 5, 8]
    sym_current_sensor[AttributeType.measured_terminal_type] = [
        MeasuredTerminalType.branch_from,
        MeasuredTerminalType.branch_to,
        MeasuredTerminalType.branch_from,
    ]
    sym_current_sensor[AttributeType.angle_measurement_type] = [
        AngleMeasurementType.global_angle,
        AngleMeasurementType.local_angle,
        AngleMeasurementType.local_angle,
    ]
    sym_current_sensor[AttributeType.i_sigma] = [100, 100, 100]
    sym_current_sensor[AttributeType.i_angle_sigma] = [0.1, 0.1, 0.1]
    sym_current_sensor[AttributeType.i_measured] = [978.814, 806.486, 776.753]
    sym_current_sensor[AttributeType.i_angle_measured] = [-0.20864859135578062, 1.368, 1.349]

    # all
    input_data = {
        ComponentType.node: node,
        ComponentType.line: line,
        ComponentType.sym_load: sym_load,
        ComponentType.source: source,
        ComponentType.sym_voltage_sensor: sym_voltage_sensor,
        ComponentType.sym_power_sensor: sym_power_sensor,
        ComponentType.sym_current_sensor: sym_current_sensor,
    }
    return input_data
