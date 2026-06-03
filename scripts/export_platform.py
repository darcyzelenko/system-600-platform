from pathlib import Path
import json
import yaml


ROOT = Path(__file__).resolve().parents[1]
EXPORTS = ROOT / "exports"


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_yaml_folder(folder: Path):
    items = []

    for path in folder.rglob("*.yaml"):
        data = load_yaml(path)

        if isinstance(data, dict):
            if "parts" in data:
                items.extend(data["parts"])
            elif "interfaces" in data:
                items.extend(data["interfaces"])
            elif "rules" in data:
                items.extend(data["rules"])
            else:
                items.append(data)

    return items


def main():
    EXPORTS.mkdir(exist_ok=True)

    platform = load_yaml(ROOT / "system" / "platform.yaml")
    modules = load_yaml_folder(ROOT / "modules")
    parts = load_yaml_folder(ROOT / "parts")
    interfaces = load_yaml_folder(ROOT / "interfaces")
    rules = load_yaml_folder(ROOT / "rules")
    evidence = load_yaml_folder(ROOT / "evidence")

    package = {
        "platform": platform,
        "modules": modules,
        "parts": parts,
        "interfaces": interfaces,
        "rules": rules,
        "evidence": evidence,
    }

    export_path = EXPORTS / "system_600_platform.json"

    with open(export_path, "w", encoding="utf-8") as f:
        json.dump(package, f, indent=2)

    print(f"Exported platform package to {export_path}")


if __name__ == "__main__":
    main()