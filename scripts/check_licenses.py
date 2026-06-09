#!/usr/bin/env python3
"""
Fail if any installed dependency uses a strong-copyleft license (GPL/AGPL).

LGPL and permissive licenses (MIT/BSD/Apache/ISC/…) are allowed — LGPL is fine
as a dynamically-linked dependency for an MIT project, and permissive licenses
are unconditionally fine. Strong copyleft (GPL/AGPL) would impose relicensing
obligations on this project, so it is blocked.

Run:  python scripts/check_licenses.py [--write]
  --write   also emit THIRD_PARTY_LICENSES.md (an inventory of dep licenses)

Exits non-zero if a blocked license is found. Used as a CI supply-chain gate.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# GPL or AGPL at a word boundary; the boundary means "LGPL" is NOT matched
# (no boundary between the L and G), which is exactly what we want.
_STRONG_COPYLEFT = re.compile(r"\b(?:A)?GPL", re.IGNORECASE)


def _dependency_licenses() -> list[dict[str, str]]:
    # Invoke via the current interpreter (`-m piplicenses`) so it works whether
    # or not the console script is on PATH — same on Windows and CI.
    out = subprocess.run(
        [sys.executable, "-m", "piplicenses", "--format=json", "--with-urls"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(out)


def main() -> int:
    packages = _dependency_licenses()
    blocked: list[tuple[str, str]] = []
    for pkg in packages:
        name, lic = pkg.get("Name", "?"), pkg.get("License", "")
        if _STRONG_COPYLEFT.search(lic) and "LGPL" not in lic.upper():
            blocked.append((name, lic))

    print(f"Audited {len(packages)} dependencies for license compliance.")
    if blocked:
        print("\nBLOCKED — strong-copyleft (GPL/AGPL) licenses found:")
        for name, lic in blocked:
            print(f"  [BLOCKED] {name}: {lic}")
        print("\nReplace these or vendor an exception before shipping.")
        return 1

    if "--write" in sys.argv:
        lines = ["# Third-party licenses\n", "| Package | Version | License |", "|---|---|---|"]
        lines += [
            f"| {p.get('Name', '')} | {p.get('Version', '')} | {p.get('License', '')} |"
            for p in sorted(packages, key=lambda p: p.get("Name", "").lower())
        ]
        Path("THIRD_PARTY_LICENSES.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Wrote THIRD_PARTY_LICENSES.md")

    print("OK: no strong-copyleft licenses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
