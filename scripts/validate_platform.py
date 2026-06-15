from pathlib import Path
import sys
import yaml


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if data is None:
        raise ValueError(f"{path} is empty or invalid YAML.")

    return data


def load_all_yaml(folder: Path):
    items = []

    if not folder.exists():
        return items

    for path in folder.rglob("*.yaml"):
        data = load_yaml(path)
        items.append((path, data))

    return items


def collect_parts():
    part_ids = set()

    for path, data in load_all_yaml(ROOT / "parts"):
        for part in data.get("parts", []):
            part_ids.add(part["id"])

    return part_ids


def collect_interfaces():
    interface_ids = set()
    interfaces = []

    for path, data in load_all_yaml(ROOT / "interfaces"):
        for interface in data.get("interfaces", []):
            interface_ids.add(interface["id"])
            interfaces.append(interface)

    return interface_ids, interfaces


def collect_rules():
    rule_ids = set()

    for path, data in load_all_yaml(ROOT / "rules"):
        for rule in data.get("rules", []):
            rule_ids.add(rule["id"])

    return rule_ids


def collect_evidence():
    evidence_ids = set()

    for path, data in load_all_yaml(ROOT / "evidence"):
        if isinstance(data, dict) and "id" in data:
            evidence_ids.add(data["id"])

    return evidence_ids


def collect_modules():
    modules = []

    for path, data in load_all_yaml(ROOT / "modules"):
        if not isinstance(data, dict):
            raise ValueError(f"Module file is not a YAML object: {path}")

        if "id" not in data:
            raise ValueError(f"Module file is missing top-level id: {path}")

        modules.append(data)

    return modules


def validate_module_grid_dimensions(module, platform):
    errors = []

    permitted = platform["module_sizes"]["permitted_widths_mm"]
    module_id = module["id"]
    module_type = module.get("type")
    dimensions = module.get("dimensions_mm", {})

    width = dimensions.get("width")

    if width is None:
        errors.append(f"{module_id} has no dimensions_mm.width defined.")
    elif width not in permitted:
        errors.append(
            f"{module_id} width {width} mm is not permitted. "
            f"Permitted widths: {permitted}"
        )

    if module_type == "floor_cassette":
        length = dimensions.get("length")

        if length is None:
            errors.append(f"{module_id} has no dimensions_mm.length defined.")
        elif length not in permitted:
            errors.append(
                f"{module_id} length {length} mm is not permitted. "
                f"Permitted lengths: {permitted}"
            )

    grid = module.get("grid", {})

    if grid.get("grid_aligned") is not True:
        errors.append(f"{module_id} grid.grid_aligned must be true.")

    return errors


def validate_lifting_capacity(module, platform):
    mass = module.get("mass_kg")
    lifting_points = module.get("lifting_points", [])
    safety_factor = platform["handling"]["lifting_safety_factor"]

    if mass is None:
        return [f"{module['id']} has no mass_kg defined."]

    if not lifting_points:
        return [f"{module['id']} has no lifting points defined."]

    available_capacity = sum(lp.get("load_rating_kg", 0) for lp in lifting_points)
    required_capacity = mass * safety_factor

    if available_capacity < required_capacity:
        return [
            f"{module['id']} fails lifting capacity: "
            f"available {available_capacity} kg, required {required_capacity} kg."
        ]

    return []


def validate_references(module, known_ids, field_name, label):
    errors = []

    for item_id in module.get(field_name, []):
        if item_id not in known_ids:
            errors.append(
                f"{module['id']} references undefined {label}: {item_id}"
            )

    return errors


def module_has_port(module, port_id):
    return any(port.get("id") == port_id for port in module.get("ports", []))


def validate_interface_connection_methods(interface, part_ids):
    errors = []

    for part_id in interface.get("connection_methods", []):
        if part_id not in part_ids:
            errors.append(
                f"{interface['id']} references undefined connection part: {part_id}"
            )

    return errors


def validate_interface_wiring(interface, modules):
    errors = []

    interface_id = interface["id"]
    from_module_type = interface.get("from_module_type")
    to_module_type = interface.get("to_module_type")
    required_ports = interface.get("required_ports", {})

    from_port = required_ports.get("from")
    to_port = required_ports.get("to")

    if not from_module_type:
        errors.append(f"{interface_id} has no from_module_type defined.")
        return errors

    if not to_module_type:
        errors.append(f"{interface_id} has no to_module_type defined.")
        return errors

    if not from_port:
        errors.append(f"{interface_id} has no required_ports.from defined.")
        return errors

    if not to_port:
        errors.append(f"{interface_id} has no required_ports.to defined.")
        return errors

    from_modules = [
        module for module in modules
        if module.get("type") == from_module_type
    ]

    to_modules = [
        module for module in modules
        if module.get("type") == to_module_type
    ]

    if not from_modules:
        errors.append(
            f"{interface_id} expects from_module_type {from_module_type}, "
            f"but no matching modules exist."
        )

    if not to_modules:
        errors.append(
            f"{interface_id} expects to_module_type {to_module_type}, "
            f"but no matching modules exist."
        )

    for module in from_modules:
        module_id = module["id"]

        if interface_id not in module.get("allowed_interfaces", []):
            errors.append(
                f"{module_id} is type {from_module_type} but does not list "
                f"{interface_id} in allowed_interfaces."
            )

        if not module_has_port(module, from_port):
            errors.append(
                f"{module_id} is type {from_module_type} but does not provide "
                f"required interface port: {from_port}"
            )

    for module in to_modules:
        module_id = module["id"]

        if interface_id not in module.get("allowed_interfaces", []):
            errors.append(
                f"{module_id} is type {to_module_type} but does not list "
                f"{interface_id} in allowed_interfaces."
            )

        if not module_has_port(module, to_port):
            errors.append(
                f"{module_id} is type {to_module_type} but does not provide "
                f"required interface port: {to_port}"
            )

    return errors


def main():
    errors = []

    try:
        platform = load_yaml(ROOT / "system" / "platform.yaml")

        part_ids = collect_parts()
        interface_ids, interfaces = collect_interfaces()
        rule_ids = collect_rules()
        evidence_ids = collect_evidence()
        modules = collect_modules()

        for module in modules:
            errors.extend(validate_module_grid_dimensions(module, platform))
            errors.extend(validate_lifting_capacity(module, platform))

            errors.extend(validate_references(module, part_ids, "parts", "part"))
            errors.extend(validate_references(module, interface_ids, "allowed_interfaces", "interface"))
            errors.extend(validate_references(module, rule_ids, "validation_rules", "rule"))
            errors.extend(validate_references(module, evidence_ids, "evidence", "evidence item"))

        for interface in interfaces:
            errors.extend(validate_interface_connection_methods(interface, part_ids))
            errors.extend(validate_interface_wiring(interface, modules))

    except Exception as exc:
        print("Validation failed:\n")
        print(f"- {exc}")
        sys.exit(1)

    if errors:
        print("Validation failed:\n")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()