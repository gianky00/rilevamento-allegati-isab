import os
import sys
import re

def bump_version(part='patch'):
    """
    Increments the version in version.py.
    part: 'major', 'minor', or 'patch'
    """
    version_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "version.py")

    with open(version_file, "r") as f:
        content = f.read()

    # Extract version
    match = re.search(r'__version__\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content)
    if not match:
        print("Error: Could not find version string.")
        sys.exit(1)

    major, minor, patch = map(int, match.groups())

    if part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif part == 'minor':
        minor += 1
        patch = 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(r'__version__\s*=\s*".*"', f'__version__ = "{new_version}"', content)

    with open(version_file, "w") as f:
        f.write(new_content)

    print(f"Version bumped to {new_version}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('part', choices=['major', 'minor', 'patch'], default='patch', nargs='?')
    args = parser.parse_args()
    bump_version(args.part)
