from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"

VISUALISER_SOURCE = ROOT / "apps" / "visualiser" / "index.html"
EXPORT_SOURCE = ROOT / "exports" / "system_600_platform.json"

VISUALISER_TARGET = PUBLIC / "index.html"
EXPORT_TARGET_DIR = PUBLIC / "exports"
EXPORT_TARGET = EXPORT_TARGET_DIR / "system_600_platform.json"


def main():
    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)

    PUBLIC.mkdir()
    EXPORT_TARGET_DIR.mkdir()

    shutil.copyfile(VISUALISER_SOURCE, VISUALISER_TARGET)
    shutil.copyfile(EXPORT_SOURCE, EXPORT_TARGET)

    print(f"Built static site in {PUBLIC}")


if __name__ == "__main__":
    main()