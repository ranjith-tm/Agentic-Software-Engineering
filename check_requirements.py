"""Check every dependency in a requirements.txt against PyPI before installing.

Usage: python check_requirements.py [path/to/requirements.txt]
"""
import json
import re
import sys
import urllib.error
import urllib.request

PYPI = "https://pypi.org/pypi"


LINE_RE = re.compile(
    r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)\s*(?:\[[^\]]*\])?\s*(?:==\s*([^\s;,#]+))?"
)


def fetch_json(url):
    """Return parsed JSON, or None if PyPI answers 404."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def main(path):
    with open(path, encoding="utf-8") as f:
        lines = [l.strip() for l in f]
    deps = [l for l in lines if l and not l.startswith(("#", "-"))]

    missing_packages = []
    missing_versions = []
    oldest = None  # (upload_time, "name==version")

    for line in deps:
        m = LINE_RE.match(line)
        if not m:
            print(f"  ! could not parse line: {line!r}")
            continue
        name, version = m.group(1), m.group(2)

        if fetch_json(f"{PYPI}/{name}/json") is None:
            missing_packages.append(name)
            continue
        if version is None:
            continue  # unpinned: package exists, nothing more to check

        release = fetch_json(f"{PYPI}/{name}/{version}/json")
        if release is None:
            missing_versions.append(f"{name}=={version}")
            continue

        urls = release.get("urls") or []
        if not urls:
            continue  # release exists but has no uploaded files
        uploaded = urls[0]["upload_time"]  # ISO 8601, sorts lexically
        if oldest is None or uploaded < oldest[0]:
            oldest = (uploaded, f"{name}=={version}")

    print(f"Dependencies checked: {len(deps)}")
    print(f"Packages not on PyPI: {len(missing_packages)}")
    for n in missing_packages:
        print(f"  - {n}")
    print(f"Versions not on PyPI: {len(missing_versions)}")
    for n in missing_versions:
        print(f"  - {n}")
    if oldest:
        print(f"Oldest pinned release: {oldest[1]} ({oldest[0][:4]})")
    else:
        print("Oldest pinned release: n/a")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt")
