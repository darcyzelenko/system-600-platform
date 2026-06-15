from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

from check_connection import (
    check_connection,
    index_by_id,
    load_platform_package,
    make_check,
)


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Design file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"Design file is empty or invalid YAML: {path}")

    if not isinstance(data, dict):
        raise ValueError(f"Design file must contain a YAML object: {path}")

    return data


def index_by_field(items: list[dict[str, Any]], field_name: str, label: str) -> dict[str, dict[str, Any]]:
    indexed = {}

    for item in items:
        item_id = item.get(field_name)

        if not item_id:
            raise ValueError(f"{label} item is missing {field_name}: {item}")

        if item_id in indexed:
            raise ValueError(f"Duplicate {label} {field_name} found: {item_id}")

        indexed[item_id] = item

    return indexed


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def distance_to_grid(value: float, grid_increment: float) -> float:
    remainder = abs(value) % grid_increment
    return min(remainder, grid_increment - remainder)


def get_interface(interface_id: str, platform: dict[str, Any]) -> dict[str, Any] | None:
    interfaces_by_id = index_by_id(platform.get("interfaces", []), "interface")
    return interfaces_by_id.get(interface_id)


def get_module(type_id: str, platform: dict[str, Any]) -> dict[str, Any] | None:
    modules_by_id = index_by_id(platform.get("modules", []), "module")
    return modules_by_id.get(type_id)


def validate_instance_exists(
    connection: dict[str, Any],
    instances_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    checks = []

    wall_instance_id = connection.get("wall_instance")
    floor_instance_id = connection.get("floor_instance")

    checks.append(
        make_check(
            "wall_instance_exists",
            wall_instance_id in instances_by_id,
            (
                f"Wall instance {wall_instance_id} exists."
                if wall_instance_id in instances_by_id
                else f"Wall instance {wall_instance_id} does not exist."
            ),
        )
    )

    checks.append(
        make_check(
            "floor_instance_exists",
            floor_instance_id in instances_by_id,
            (
                f"Floor instance {floor_instance_id} exists."
                if floor_instance_id in instances_by_id
                else f"Floor instance {floor_instance_id} does not exist."
            ),
        )
    )

    return checks


def get_grid_thresholds(
    interface: dict[str, Any],
    platform: dict[str, Any],
) -> tuple[int | None, int | None, list[dict[str, Any]]]:
    checks = []

    primary_grid = (
        platform
        .get("platform", {})
        .get("grid", {})
        .get("primary_increment_mm")
    )

    max_offset = (
        interface
        .get("geometric_rules", {})
        .get("max_offset_from_grid_mm")
    )

    if primary_grid is None:
        checks.append(
            make_check(
                "grid_threshold_available",
                False,
                "Cannot evaluate grid alignment because platform.grid.primary_increment_mm is missing.",
            )
        )

    if max_offset is None:
        checks.append(
            make_check(
                "grid_offset_threshold_available",
                False,
                "Cannot evaluate grid alignment because interface.geometric_rules.max_offset_from_grid_mm is missing.",
            )
        )

    return primary_grid, max_offset, checks


def check_grid_alignment(
    wall_instance: dict[str, Any],
    floor_instance: dict[str, Any],
    interface: dict[str, Any],
    platform: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = []

    primary_grid, max_offset, threshold_checks = get_grid_thresholds(interface, platform)
    checks.extend(threshold_checks)

    if primary_grid is None or max_offset is None:
        return checks

    for role, instance in [
        ("wall", wall_instance),
        ("floor", floor_instance),
    ]:
        instance_id = instance.get("instance_id", f"UNKNOWN_{role.upper()}")

        for axis in ["x_mm", "y_mm"]:
            value = instance.get(axis)

            if not is_number(value):
                checks.append(
                    make_check(
                        f"grid_alignment_{role}_{axis}",
                        False,
                        f"{instance_id} has no numeric {axis} value.",
                    )
                )
                continue

            offset = distance_to_grid(value, primary_grid)
            passed = offset <= max_offset

            checks.append(
                make_check(
                    f"grid_alignment_{role}_{axis}",
                    passed,
                    (
                        f"{instance_id} {axis}={value} mm is within {offset} mm of the "
                        f"{primary_grid} mm grid, allowed offset {max_offset} mm."
                    ),
                )
            )

    return checks


def check_edge_distance(
    connection: dict[str, Any],
    floor_instance: dict[str, Any],
    floor_module: dict[str, Any],
    interface: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = []

    min_edge_distance = (
        interface
        .get("geometric_rules", {})
        .get("minimum_edge_distance_mm")
    )

    if min_edge_distance is None:
        return [
            make_check(
                "edge_distance_threshold_available",
                False,
                "Cannot evaluate edge distance because interface.geometric_rules.minimum_edge_distance_mm is missing.",
            )
        ]

    connection_point = connection.get("connection_point_mm")

    if not isinstance(connection_point, dict):
        return [
            make_check(
                "edge_distance",
                False,
                "Cannot evaluate edge distance because connection_point_mm is missing.",
            )
        ]

    point_x = connection_point.get("x")
    point_y = connection_point.get("y")

    if not is_number(point_x) or not is_number(point_y):
        return [
            make_check(
                "edge_distance",
                False,
                "Cannot evaluate edge distance because connection_point_mm.x and connection_point_mm.y must be numeric.",
            )
        ]

    floor_x = floor_instance.get("x_mm")
    floor_y = floor_instance.get("y_mm")

    if not is_number(floor_x) or not is_number(floor_y):
        return [
            make_check(
                "edge_distance",
                False,
                f"Cannot evaluate edge distance because floor instance {floor_instance.get('instance_id')} has non-numeric x_mm or y_mm.",
            )
        ]

    dimensions = floor_module.get("dimensions_mm", {})
    floor_width = dimensions.get("width")
    floor_length = dimensions.get("length")

    if not is_number(floor_width) or not is_number(floor_length):
        return [
            make_check(
                "edge_distance",
                False,
                f"Cannot evaluate edge distance because floor type {floor_module.get('id')} has non-numeric width or length.",
            )
        ]

    local_x = point_x - floor_x
    local_y = point_y - floor_y

    distances = [
        local_x,
        floor_width - local_x,
        local_y,
        floor_length - local_y,
    ]

    nearest_edge_distance = min(distances)
    passed = all(distance >= min_edge_distance for distance in distances)

    checks.append(
        make_check(
            "edge_distance",
            passed,
            (
                f"Connection point is {nearest_edge_distance} mm from nearest floor cassette edge; "
                f"minimum required edge distance is {min_edge_distance} mm."
            ),
        )
    )

    return checks


def check_tolerance_envelope(
    connection: dict[str, Any],
    interface: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = []

    tolerance_strategy = interface.get("tolerance_strategy", {})

    required_thresholds = {
        "x": "adjustment_x_mm",
        "y": "adjustment_y_mm",
        "z": "adjustment_z_mm",
    }

    declared_offset = connection.get("declared_offset_mm")

    if not isinstance(declared_offset, dict):
        return [
            make_check(
                "tolerance_envelope",
                False,
                "Cannot evaluate tolerance envelope because declared_offset_mm is missing.",
            )
        ]

    for axis, threshold_key in required_thresholds.items():
        allowed = tolerance_strategy.get(threshold_key)
        value = declared_offset.get(axis)

        if allowed is None:
            checks.append(
                make_check(
                    f"tolerance_envelope_{axis}",
                    False,
                    f"Cannot evaluate {axis}-axis tolerance because interface.tolerance_strategy.{threshold_key} is missing.",
                )
            )
            continue

        if not is_number(value):
            checks.append(
                make_check(
                    f"tolerance_envelope_{axis}",
                    False,
                    f"Cannot evaluate {axis}-axis tolerance because declared_offset_mm.{axis} is missing or non-numeric.",
                )
            )
            continue

        passed = abs(value) <= allowed

        checks.append(
            make_check(
                f"tolerance_envelope_{axis}",
                passed,
                (
                    f"Declared {axis}-axis offset is {value} mm; "
                    f"allowed tolerance is +/- {allowed} mm."
                ),
            )
        )

    return checks


def run_geometric_checks(
    connection: dict[str, Any],
    wall_instance: dict[str, Any],
    floor_instance: dict[str, Any],
    floor_module: dict[str, Any],
    interface: dict[str, Any],
    platform: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = []

    checks.extend(
        check_grid_alignment(
            wall_instance=wall_instance,
            floor_instance=floor_instance,
            interface=interface,
            platform=platform,
        )
    )

    checks.extend(
        check_edge_distance(
            connection=connection,
            floor_instance=floor_instance,
            floor_module=floor_module,
            interface=interface,
        )
    )

    checks.extend(
        check_tolerance_envelope(
            connection=connection,
            interface=interface,
        )
    )

    return checks


def check_design(
    design: dict[str, Any],
    platform: dict[str, Any],
) -> dict[str, Any]:
    instances = design.get("instances", [])
    connections = design.get("connections", [])

    instances_by_id = index_by_field(instances, "instance_id", "instance")

    connection_results = []

    for connection in connections:
        connection_id = connection.get("connection_id", "UNKNOWN_CONNECTION")
        wall_instance_id = connection.get("wall_instance")
        floor_instance_id = connection.get("floor_instance")
        interface_id = connection.get("interface")

        checks = []
        checks.extend(validate_instance_exists(connection, instances_by_id))

        wall_instance = instances_by_id.get(wall_instance_id)
        floor_instance = instances_by_id.get(floor_instance_id)

        if wall_instance is None or floor_instance is None:
            connection_results.append(
                {
                    "connection": {
                        "connection_id": connection_id,
                        "wall_instance": wall_instance_id,
                        "floor_instance": floor_instance_id,
                        "interface": interface_id,
                    },
                    "compliant": False,
                    "checks": checks,
                }
            )
            continue

        wall_type_id = wall_instance.get("type_id")
        floor_type_id = floor_instance.get("type_id")

        static_result = check_connection(
            wall_id=wall_type_id,
            floor_id=floor_type_id,
            interface_id=interface_id,
            platform=platform,
        )

        checks.extend(static_result["checks"])

        interface = get_interface(interface_id, platform)
        floor_module = get_module(floor_type_id, platform)

        if interface is None:
            checks.append(
                make_check(
                    "interface_resolves_for_geometry",
                    False,
                    f"Cannot run geometric checks because interface {interface_id} does not exist.",
                )
            )
        elif floor_module is None:
            checks.append(
                make_check(
                    "floor_type_resolves_for_geometry",
                    False,
                    f"Cannot run geometric checks because floor type {floor_type_id} does not exist.",
                )
            )
        else:
            checks.extend(
                run_geometric_checks(
                    connection=connection,
                    wall_instance=wall_instance,
                    floor_instance=floor_instance,
                    floor_module=floor_module,
                    interface=interface,
                    platform=platform,
                )
            )

        connection_results.append(
            {
                "connection": {
                    "connection_id": connection_id,
                    "wall_instance": wall_instance_id,
                    "wall_type": wall_type_id,
                    "floor_instance": floor_instance_id,
                    "floor_type": floor_type_id,
                    "interface": interface_id,
                },
                "compliant": all(check["passed"] for check in checks),
                "checks": checks,
            }
        )

    return {
        "design": design.get("id", "UNKNOWN_DESIGN"),
        "name": design.get("name"),
        "compliant": all(result["compliant"] for result in connection_results),
        "connections": connection_results,
    }


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_design.py <DESIGN_YAML_PATH>")
        print()
        print("Example: python scripts/check_design.py designs/SAMPLE_DESIGN_PASS_001.yaml")
        return 2

    design_path = Path(sys.argv[1])

    try:
        platform = load_platform_package()
        design = load_yaml(design_path)
        result = check_design(design, platform)
    except Exception as exc:
        print(f"Design check failed to run: {exc}")
        return 1

    print(json.dumps(result, indent=2))

    return 0 if result["compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
