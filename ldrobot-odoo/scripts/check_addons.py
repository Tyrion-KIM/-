#!/usr/bin/env python3
"""Fast checks that do not require an installed Odoo runtime."""

from __future__ import annotations

import ast
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
ADDONS = ROOT / "addons"
REQUIRED = {"__init__.py", "__manifest__.py"}
# Manifest versions track the Odoo series; trailing x.y.z segments
# are bumped freely as each addon evolves.
ODOO_SERIES = "19.0"


def main() -> int:
    failures: list[str] = []
    modules = sorted(path for path in ADDONS.iterdir() if path.is_dir())
    if not modules:
        failures.append("No modules found under addons/")

    for module in modules:
        missing = REQUIRED - {path.name for path in module.iterdir()}
        if missing:
            failures.append(f"{module.name}: missing {sorted(missing)}")
            continue

        manifest = ast.literal_eval((module / "__manifest__.py").read_text())
        version = str(manifest.get("version", ""))
        if not version.startswith(f"{ODOO_SERIES}."):
            failures.append(
                f"{module.name}: unexpected manifest version {version!r}; "
                f"expected {ODOO_SERIES}.x.y.z"
            )
        if manifest.get("license") != "LGPL-3":
            failures.append(f"{module.name}: license must be LGPL-3")

        for relative_file in manifest.get("data", []):
            if not (module / relative_file).is_file():
                failures.append(
                    f"{module.name}: manifest data file not found: {relative_file}"
                )

        for python_file in module.rglob("*.py"):
            try:
                ast.parse(python_file.read_text(encoding="utf-8"), python_file)
            except SyntaxError as exc:
                failures.append(f"{python_file.relative_to(ROOT)}: {exc}")

        for xml_file in module.rglob("*.xml"):
            try:
                tree = ET.parse(xml_file)
            except ET.ParseError as exc:
                failures.append(f"{xml_file.relative_to(ROOT)}: {exc}")
                continue

            # Odoo 19 removed res.groups.category_id. Groups now link to a
            # res.groups.privilege, whose category owns the application area.
            for group in tree.findall(".//record[@model='res.groups']"):
                if group.find("./field[@name='category_id']") is not None:
                    failures.append(
                        f"{xml_file.relative_to(ROOT)}: res.groups.category_id "
                        "is not supported by Odoo 19; use privilege_id"
                    )

    if failures:
        print("\n".join(f"ERROR: {failure}" for failure in failures))
        return 1
    print(f"Checked {len(modules)} addon modules: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
