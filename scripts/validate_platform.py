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


def collect_interfaces():
    interface_ids = set()
    for path, data in load_all_yaml(ROOT / "interfaces"):
        for interface in data.get("interfaces", []):
            interface_ids.add(interface["id"])
    return interface_ids


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


def validate_interface_references(module, interface_ids):
    errors = []
    for interface_id in module.get("allowed_interfaces", []):
        if interface_id not in interface_ids:
            errors.append(
                f"{module['id']} references undefined interface {interface_id}."
            )
    return errors


def main():
    errors = []

    platform = load_yaml(ROOT / "system" / "platform.yaml")
    interface_ids = collect_interfaces()

    module_files = list((ROOT / "modules").rglob("*.yaml"))

    for module_file in module_files:
        module = load_yaml(module_file)

        errors.extend(validate_module_width(module, platform))
        errors.extend(validate_lifting_capacity(module, platform))
        errors.extend(validate_interface_references(module, interface_ids))

    if errors:
        print("Validation failed:\n")
        for error in errors:
            print(f"- {error}")
        sys.exit(1)

    print("Validation passed.")


if __name__ == "__main__":
    main()