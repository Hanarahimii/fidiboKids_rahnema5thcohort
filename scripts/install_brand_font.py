"""Install the owner's copy of Kahroba locally without bundling it in redistributable source."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "3-Kahroba-V1.0-Eco.zip"
DESTINATION = ROOT / "runtime" / "brand_fonts"
FONTS = ("Kahroba-FD-RG.woff2", "Kahroba-FD-B.woff2", "Kahroba-FD-BL.woff2")

if not ARCHIVE.is_file():
    raise SystemExit(f"Font archive not found: {ARCHIVE}")
with zipfile.ZipFile(ARCHIVE) as archive:
    members = {}
    for name in FONTS:
        candidates = [item for item in archive.namelist() if item.endswith("/FD(FarsiDigits)/" + name)]
        if len(candidates) != 1:
            raise SystemExit(f"Expected one licensed font file: {name}")
        members[name] = archive.read(candidates[0])
DESTINATION.mkdir(parents=True, exist_ok=True)
for name, data in members.items():
    (DESTINATION / name).write_bytes(data)
print("Licensed font installed for local use. Restart the server and refresh the browser.")
