from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPORT_PATH = ROOT / "exports" / "system_600_platform.json"


def load_platform_package(path: Path = DEFAULT_EXPORT_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Platform export not found: {path}. "
            "Run scripts/export_platform.py first."
        )

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def index_by_id(items: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed = {}

    for item in items:
        item_id = item.get("id")

        if not item_id:
            raise ValueError(f"{label} item is missing id: {item}")

        if item_id in indexed:
            raise ValueError(f"Duplicate {label} id found: {item_id}")

        indexed[item_id] = item

    return indexed


def make_check(rule: str, passed: bool, detail: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "passed": passed,
        "detail": detail,
    }


def module_has_port(module: dict[str, Any], port_id: str) -> bool:
    return any(port.get("id") == port_id for port in module.get("ports", []))


def get_permitted_module_sizes(platform_package: dict[str, Any]) -> list[int]:
    try:
        return platform_package["platform"]["module_sizes"]["permitted_widths_mm"]
    except KeyError as exc:
        raise KeyError(
            "Missing platform.module_sizes.permitted_widths_mm in platform export."
        ) from exc


def check_grid_size_sanity(
    module: dict[str, Any],
    platform_package: dict[str, Any],
) -> list[dict[str, Any]]:
    checks = []

    module_id = module.get("id", "UNKNOWN_MODULE")
    module_type = module.get("type")
    dimensions = module.get("dimensions_mm", {})
    grid = module.get("grid", {})
    permitted_sizes = get_permitted_module_sizes(platform_package)

    grid_aligned = grid.get("grid_aligned")

    checks.append(
        make_check(
            "grid_aligned",
            grid_aligned is True,
            (
                f"{module_id} declares grid.grid_aligned true."
                if grid_aligned is True
                else f"{module_id} must declare grid.grid_aligned true."
            ),
        )
    )

    width = dimensions.get("width")

    checks.append(
        make_check(
            "grid_width_sanity",
            width in permitted_sizes,
            (
                f"{module_id} width {width} mm is permitted."
                if width in permitted_sizes
                else f"{module_id} width {width} mm is not in permitted sizes: {permitted_sizes}."
            ),
        )
    )

    if module_type == "floor_cassette":
        length = dimensions.get("length")

        checks.append(
            make_check(
                "grid_length_sanity",
                length in permitted_sizes,
                (
                    f"{module_id} length {length} mm is permitted."
                    if length in permitted_sizes
                    else f"{module_id} length {length} mm is not in permitted sizes: {permitted_sizes}."
                ),
            )
        )

    return checks

def check_connection(
    wall_id: str,
    floor_id: str,
    interface_id: str,
    platform: dict[str, Any],
) -> dict[str, Any]:
    modules_by_id = index_by_id(platform.get("modules", []), "module")
    parts_by_id = index_by_id(platform.get("parts", []), "part")
    interfaces_by_id = index_by_id(platform.get("interfaces", []), "interface")

    checks = []

    wall = modules_by_id.get(wall_id)
    floor = modules_by_id.get(floor_id)
    interface = interfaces_by_id.get(interface_id)

    if wall is None:
        checks.append(
            make_check(
                "wall_exists",
                False,
                f"Wall module does not exist: {wall_id}",
            )
        )

    if floor is None:
        checks.append(
            make_check(
                "floor_exists",
                False,
                f"Floor module does not exist: {floor_id}",
            )
        )

    if interface is None:
        checks.append(
            make_check(
                "interface_exists",
                False,
                f"Interface does not exist: {interface_id}",
            )
        )

    if wall is None or floor is None or interface is None:
        return {
            "connection": {
                "wall": wall_id,
                "floor": floor_id,
                "interface": interface_id,
            },
            "compliant": False,
            "checks": checks,
        }

    from_module_type = interface.get("from_module_type")
    to_module_type = interface.get("to_module_type")

    checks.append(
        make_check(
            "type_match",
            wall.get("type") == from_module_type and floor.get("type") == to_module_type,
            (
                f"Interface {interface_id} expects {from_module_type} to {to_module_type}; "
                f"received {wall.get('type')} to {floor.get('type')}."
            ),
        )
    )

    wall_allows_interface = interface_id in wall.get("allowed_interfaces", [])
    floor_allows_interface = interface_id in floor.get("allowed_interfaces", [])

    checks.append(
        make_check(
            "interface_allowed_wall",
            wall_allows_interface,
            (
                f"{wall_id} lists {interface_id} in allowed_interfaces."
                if wall_allows_interface
                else f"{wall_id} does not list {interface_id} in allowed_interfaces."
            ),
        )
    )

    checks.append(
        make_check(
            "interface_allowed_floor",
            floor_allows_interface,
            (
                f"{floor_id} lists {interface_id} in allowed_interfaces."
                if floor_allows_interface
                else f"{floor_id} does not list {interface_id} in allowed_interfaces."
            ),
        )
    )

    required_ports = interface.get("required_ports", {})
    required_wall_port = required_ports.get("from")
    required_floor_port = required_ports.get("to")

    wall_port_present = bool(required_wall_port) and module_has_port(wall, required_wall_port)
    floor_port_present = bool(required_floor_port) and module_has_port(floor, required_floor_port)

    checks.append(
        make_check(
            "required_wall_port_present",
            wall_port_present,
            (
                f"{wall_id} provides required port {required_wall_port}."
                if wall_port_present
                else f"{wall_id} does not provide required port {required_wall_port}."
            ),
        )
    )

    checks.append(
        make_check(
            "required_floor_port_present",
            floor_port_present,
            (
                f"{floor_id} provides required port {required_floor_port}."
                if floor_port_present
                else f"{floor_id} does not provide required port {required_floor_port}."
            ),
        )
    )

    connection_methods = interface.get("connection_methods", [])

    if not connection_methods:
        checks.append(
            make_check(
                "connection_methods_exist",
                False,
                f"{interface_id} has no connection_methods defined.",
            )
        )
    else:
        for part_id in connection_methods:
            part_exists = part_id in parts_by_id

            checks.append(
                make_check(
                    "connection_method_exists",
                    part_exists,
                    (
                        f"Connection method {part_id} resolves to a part."
                        if part_exists
                        else f"Connection method {part_id} does not resolve to a part."
                    ),
                )
            )

    checks.extend(check_grid_size_sanity(wall, platform))
    checks.extend(check_grid_size_sanity(floor, platform))

    compliant = all(check["passed"] for check in checks)

    return {
        "connection": {
            "wall": wall_id,
            "floor": floor_id,
            "interface": interface_id,
        },
        "compliant": compliant,
        "checks": checks,
    }


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "Usage: python scripts/check_connection.py "
            "<WALL_ID> <FLOOR_ID> <INTERFACE_ID>"
        )
        print()
        print(
            "Example: python scripts/check_connection.py "
            "WALL_2400_2700_EXT_A FLOOR_2400_6000_STRUCT_A IF_WALL_TO_FLOOR_001"
        )
        return 2

    wall_id = sys.argv[1]
    floor_id = sys.argv[2]
    interface_id = sys.argv[3]

    try:
        platform = load_platform_package()
        result = check_connection(wall_id, floor_id, interface_id, platform)
    except Exception as exc:
        print(f"Connection check failed to run: {exc}")
        return 1

    print(json.dumps(result, indent=2))

    return 0 if result["compliant"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
