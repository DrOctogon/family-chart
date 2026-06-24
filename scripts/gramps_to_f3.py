#!/usr/bin/env python3
"""Convert a Gramps CSV export into family-chart (f3) JSON.

The Gramps CSV has four sections separated by blank lines, each with its own
header row: Places, Persons, Marriages, Family-children. We parse Persons,
Marriages, and Family-children and emit the f3 person format:

    { "id", "data": {"first name","last name","gender","birthday","death"},
      "rels": {"parents":[...], "spouses":[...], "children":[...]} }

Usage: python3 scripts/gramps_to_f3.py gramps_tree.csv public/gramps.json
"""
import csv
import json
import sys


def gid(raw):
    """Normalize a bracketed Gramps id like '[I0001]' -> 'i0001'."""
    return raw.strip().strip("[]").lower()


def split_sections(path):
    """Split the CSV into sections keyed by their header's first column."""
    sections = {}
    current_header = None
    with open(path, newline="") as f:
        for row in csv.reader(f):
            if not any(cell.strip() for cell in row):  # blank line -> section break
                current_header = None
                continue
            if current_header is None:
                current_header = row[0]
                sections[current_header] = {"fields": row, "rows": []}
                continue
            sections[current_header]["rows"].append(row)
    return sections


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "gramps_tree.csv"
    dst = sys.argv[2] if len(sys.argv) > 2 else "public/gramps.json"
    sections = split_sections(src)

    # --- Persons ---
    people = {}
    p = sections["Person"]
    idx = {name: i for i, name in enumerate(p["fields"])}
    for row in p["rows"]:
        pid = gid(row[idx["Person"]])
        gender = row[idx["Gender"]].strip().lower()
        people[pid] = {
            "id": pid,
            "data": {
                "first name": row[idx["Given"]].strip(),
                "last name": row[idx["Surname"]].strip(),
                "gender": "M" if gender == "male" else "F",
                "birthday": row[idx["Birth date"]].strip(),
                "death": row[idx["Death date"]].strip(),
            },
            "rels": {},
        }

    def rel(pid, key):
        return people[pid]["rels"].setdefault(key, [])

    # --- Marriages: husband + wife are spouses; remember family -> couple ---
    family_parents = {}
    m = sections["Marriage"]
    midx = {name: i for i, name in enumerate(m["fields"])}
    for row in m["rows"]:
        fam = gid(row[midx["Marriage"]])
        h, w = gid(row[midx["Husband"]]), gid(row[midx["Wife"]])
        family_parents[fam] = [h, w]
        if w not in rel(h, "spouses"):
            rel(h, "spouses").append(w)
        if h not in rel(w, "spouses"):
            rel(w, "spouses").append(h)

    # --- Family children: link child<->both parents ---
    fc = sections["Family"]
    fidx = {name: i for i, name in enumerate(fc["fields"])}
    for row in fc["rows"]:
        fam = gid(row[fidx["Family"]])
        child = gid(row[fidx["Child"]])
        parents = family_parents.get(fam, [])
        rel(child, "parents").extend(p for p in parents if p not in rel(child, "parents"))
        for parent in parents:
            if child not in rel(parent, "children"):
                rel(parent, "children").append(child)

    out = list(people.values())
    with open(dst, "w") as f:
        json.dump(out, f, indent=2)

    connected = {pid for pid, x in people.items() if x["rels"]}
    orphans = sorted(pid for pid in people if pid not in connected)
    print(f"wrote {len(out)} people -> {dst}")
    print(f"connected: {len(connected)}  disconnected: {len(orphans)} -> {orphans}")


if __name__ == "__main__":
    main()
