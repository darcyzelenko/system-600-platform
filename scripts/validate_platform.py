from pathlib import Path
import yaml
import sys


ROOT = Path(__file__).resolve().parents[1]


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_all_yaml(folder: Path):
    items = []
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
    for path, data in load_all_yaml(ROOT / "interfaces"):
        for interface in data.get("interfaces", []):
            interface_ids.add(interface["id"])
    return interface_ids


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


def validate_module_width(module, platform):
    permitted = platform["module_sizes"]["permitted_widths_mm"]
    width = module["dimensions_mm"]["width"]

    if width not in permitted:
        return [
            f"{module['id']} width {width} mm is not permitted. "
            f"Permitted widths: {permitted}"
        ]

    return []


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


def validate_interface_connection_methods(interface, part_ids):
    errors = []

    for part_id in interface.get("connection_methods", []):
        if part_id not in part_ids:
            errors.append(
                f"{interface['id']} references undefined connection part: {part_id}"
            )

    return errors


def main():
    errors = []

    platform = load_yaml(ROOT / "system" / "platform.yaml")

    part_ids = collect_parts()
    interface_ids = collect_interfaces()
    rule_ids = collect_rules()
    evidence_ids = collect_evidence()

    for module_file in (ROOT / "modules").rglob("*.yaml"):
        module = load_yaml(module_file)

        errors.extend(validate_module_width(module, platform))
        errors.extend(validate_lifting_capacity(module, platform))

        errors.extend(validate_references(module, part_ids, "parts", "part"))
        errors.extend(validate_references(module, interface_ids, "allowed_interfaces", "interface"))
        errors.extend(validate_references(module, rule_ids, "validation_rules", "rule"))
        errors.extend(validate_references(module, evidence_ids, "evidence", "evidence item"))

    for interface_file, data in load_all_yaml(ROOT / "interfaces"):
        for interface in data.get("interfaces", []):
            errors.extend(validate_interface_connection_methods(interface, part_ids))

    if errors:
        print("Validation failed:\n")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()