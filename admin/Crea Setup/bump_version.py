"""
Script di utilità per incrementare la versione dell'applicazione in version.py.
Supporta l'incremento di major, minor e patch version.
"""

import re
from pathlib import Path


def bump_version(part="patch"):
    """
    Incrementa la versione nel file src/version.py.

    Args:
        part (str): La parte della versione da incrementare ('major', 'minor', o 'patch').
    Returns:
        str: La nuova stringa di versione.
    """
    # admin/Crea Setup/bump_version.py -> ../../src/version.py
    version_file = Path(__file__).resolve().parents[2] / "src" / "version.py"

    if not version_file.exists():
        print(f"Error: version.py not found at {version_file}")
        return None

    content = version_file.read_text(encoding="utf-8")

    # Extract version
    match = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("Error: Could not find version string.")
        return None

    major, minor, patch = map(int, match.groups())

    if part == "major":
        major += 1
        minor = 0
        patch = 0
    elif part == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(r'__version__\s*=\s*".*"', f'__version__ = "{new_version}"', content)

    version_file.write_text(new_content, encoding="utf-8")

    print(f"Version bumped to {new_version}")
    return new_version


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("part", choices=["major", "minor", "patch"], default="patch", nargs="?")
    args = parser.parse_args()
    bump_version(args.part)
