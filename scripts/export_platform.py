from pathlib import Path
from datetime import date, datetime
import json
import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_json_safe(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()

    if isinstance(value, dict):
        return {key: make_json_safe(item) for key, item in value.items()}

    if isinstance(value, list):
        return [make_json_safe(item) for item in value]

    return value


def add_meta(item: dict, collection: str, family: str, path: Path):
    item["_meta"] = {
        "collection": collection,
        "family": family,
        "source_file": path.name,
        "source_path": str(path.relative_to(ROOT)).replace("\\", "/")
    }
    return item


def load_modules(folder: Path):
    modules = []

    for path in folder.rglob("*.yaml"):
        data = load_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"Module file is not a YAML object: {path}")

        if "id" not in data:
            raise ValueError(f"Module file is missing top-level id: {path}")

        family = path.parent.name
        modules.append(add_meta(data, "modules", family, path))

    return modules


def load_wrapped_list(folder: Path, wrapper_key: str, collection_name: str):
    items = []

    for path in folder.rglob("*.yaml"):
        data = load_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a YAML object.")

        if wrapper_key not in data:
            raise ValueError(f"{path} is missing top-level key: {wrapper_key}")

        wrapped_items = data[wrapper_key]

        if not isinstance(wrapped_items, list):
            raise ValueError(f"{path}:{wrapper_key} must be a list.")

        family = path.stem

        for item in wrapped_items:
            if not isinstance(item, dict):
                raise ValueError(f"{path}:{wrapper_key} contains a non-object item: {item}")

            if "id" not in item:
                raise ValueError(f"{path}:{wrapper_key} item is missing id: {item}")

            items.append(add_meta(item, collection_name, family, path))

    return items


def load_evidence(folder: Path):
    evidence = []

    for path in folder.rglob("*.yaml"):
        data = load_yaml(path)

        if not isinstance(data, dict):
            raise ValueError(f"Evidence file is not a YAML object: {path}")

        if "id" not in data:
            raise ValueError(f"Evidence file is missing top-level id: {path}")

        family = path.parent.name
        evidence.append(add_meta(data, "evidence", family, path))

    return evidence


def main():
    EXPORTS.mkdir(exist_ok=True)

    package = {
        "platform": load_yaml(ROOT / "system" / "platform.yaml"),
        "modules": load_modules(ROOT / "modules"),
        "parts": load_wrapped_list(ROOT / "parts", "parts", "parts"),
        "interfaces": load_wrapped_list(ROOT / "interfaces", "interfaces", "interfaces"),
        "rules": load_wrapped_list(ROOT / "rules", "rules", "rules"),
        "evidence": load_evidence(ROOT / "evidence"),
    }

    package = make_json_safe(package)

    export_path = EXPORTS / "system_600_platform.json"

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2)

    print(f"Exported platform package to {export_path}")
    print(f"Modules: {len(package['modules'])}")
    print(f"Parts: {len(package['parts'])}")
    print(f"Interfaces: {len(package['interfaces'])}")
    print(f"Rules: {len(package['rules'])}")
    print(f"Evidence: {len(package['evidence'])}")


if __name__ == "__main__":
    main()