from __future__ import annotations

import json
from pathlib import Path

import yaml

from check_design import check_design
from check_connection import load_platform_package


ROOT = Path(__file__).resolve().parents[1]

FIXTURES = [
    ROOT / "designs" / "SAMPLE_DESIGN_PASS_001.yaml",
    ROOT / "designs" / "SAMPLE_DESIGN_FAIL_001.yaml",
]


def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def main():
    platform = load_platform_package()

    print("Running System 600 wall-floor connection checker examples")
    print("=" * 64)

    all_results = []

    for fixture in FIXTURES:
        design = load_yaml(fixture)
        result = check_design(design, platform)
        all_results.append(result)

        status = "PASS" if result["compliant"] else "FAIL"

        print()
        print(f"{fixture.name}: {status}")
        print(f"Design ID: {result['design']}")

        for connection in result["connections"]:
            connection_status = "PASS" if connection["compliant"] else "FAIL"
            connection_id = connection["connection"].get("connection_id", "UNKNOWN_CONNECTION")

            print(f"  {connection_id}: {connection_status}")

            failed_checks = [
                check for check in connection["checks"]
                if not check["passed"]
            ]

            for check in failed_checks:
                print(f"    - {check['rule']}: {check['detail']}")

    print()
    print("=" * 64)
    print("Full JSON result:")
    print(json.dumps(all_results, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
