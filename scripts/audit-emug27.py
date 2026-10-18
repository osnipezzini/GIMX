#!/usr/bin/env python3
"""Extract reproducible EMUG27 descriptor evidence from an official Git clone.

Read-only: no hardware, network, checkout changes, or runtime dependencies.
This intentionally handles only the HID short-item subset in the pinned arrays.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess


SNAPSHOTS = (
    ("legacy-v5.8", "fd02ed3e3c4a620a4c3a49deb63a793ead454195", "EMUG27PS3"),
    ("current-source-8.0", "ab2215ebad5d50fd25b6b40ac74254f1f4c0bda5", "EMUG27"),
)


def read_source(repo, commit, path):
    return subprocess.check_output(
        ["git", "-C", str(repo), "show", f"{commit}:{path}"], text=True
    )


def extract_descriptor(source):
    source = re.sub(r"/\*.*?\*/|//[^\n]*", "", source, flags=re.S)
    match = re.search(r"\bReport\[\]\s*=\s*\{(.*?)\}", source, re.S)
    if not match:
        raise ValueError("Report[] not found")
    return bytes(int(v, 16) for v in re.findall(r"0x([0-9a-fA-F]+)", match[1]))


def audit_descriptor(data):
    size = count = page = 0
    usages = []
    usage_min = usage_max = None
    totals = {"input": 0, "output": 0, "feature": 0}
    fields = []
    pos = 0
    while pos < len(data):
        prefix = data[pos]
        if prefix == 0xFE:
            raise ValueError("Long HID item is outside this audit's supported subset")
        length = (0, 1, 2, 4)[prefix & 3]
        if pos + 1 + length > len(data):
            raise ValueError("Truncated HID item")
        value = int.from_bytes(data[pos + 1:pos + 1 + length], "little")
        item_type, tag = (prefix >> 2) & 3, prefix >> 4
        if item_type == 1:
            if tag == 0:
                page = value
            elif tag == 7:
                size = value
            elif tag == 9:
                count = value
            elif tag in (8, 10, 11):
                raise ValueError("Report IDs/global stack require a full HID parser")
        elif item_type == 2:
            if tag == 0:
                usages.append(value)
            elif tag == 1:
                usage_min = value
            elif tag == 2:
                usage_max = value
        elif item_type == 0:
            kind = {8: "input", 9: "output", 11: "feature"}.get(tag)
            if kind:
                fields.append({
                    "kind": kind, "bit_offset": totals[kind],
                    "report_size_bits": size, "report_count": count,
                    "usage_page": page, "usages": usages[:],
                    "usage_min": usage_min, "usage_max": usage_max,
                    "flags": value,
                })
                totals[kind] += size * count
            usages = []
            usage_min = usage_max = None
        pos += 1 + length
    if totals != {"input": 88, "output": 56, "feature": 1152}:
        raise ValueError(f"Unexpected descriptor totals: {totals}")
    return totals, fields


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("firmware_repo", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = {"schema_version": 1, "source_repository": "https://github.com/matlo/GIMX-firmwares", "snapshots": []}
    for label, commit, directory in SNAPSHOTS:
        path = f"{directory}/Descriptors.c"
        source = read_source(args.firmware_repo, commit, path)
        data = extract_descriptor(source)
        totals, fields = audit_descriptor(data)
        result["snapshots"].append({
            "label": label, "commit": commit, "path": path,
            "source_url": f"{result['source_repository']}/blob/{commit}/{path}",
            "source_sha256_utf8_lf": hashlib.sha256(source.encode()).hexdigest(),
            "report_descriptor_length": len(data),
            "report_descriptor_sha256": hashlib.sha256(data).hexdigest(),
            "report_descriptor_hex": data.hex(),
            "report_bits": totals, "fields": fields,
        })
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
