#!/usr/bin/env python3
"""Convert a Gramps *JSON export* (NDJSON) into family-chart (f3) JSON.

Gramps' "Gramps JSON Export" writes one record per line, each a handle-keyed
object with a `_class` of Person / Family / Event / Place / Note. References
between records use opaque `handle` strings. This script resolves those
handles and emits the flat f3 person format the chart consumes:

    { "id", "data": {"first name","last name","gender","birthday","death"},
      "rels": {"parents":[...], "spouses":[...], "children":[...]} }

Person ids are the normalized Gramps id (e.g. "I0001" -> "i0001") so they stay
stable and human-readable across exports.

Usage: python3 scripts/gramps_json_to_f3.py family-tree.json public/gramps.json
"""
import json
import sys

# Gramps gender enum -> f3 single-letter code.
GENDER = {0: "F", 1: "M"}


def load_records(path):
    """Read an NDJSON Gramps export into a list of records."""
    recs = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def norm_id(gramps_id):
    """Normalize a Gramps id like 'I0001' -> 'i0001'."""
    return gramps_id.strip().lower()


def event_date(event):
    """Best-effort human date string from a Gramps Event.

    Prefers the numeric dateval (year, or year-month-day when known) so output
    stays terse and sortable; falls back to the free-text date field.
    """
    date = event.get("date") or {}
    dv = date.get("dateval")
    if isinstance(dv, list) and len(dv) >= 3:
        day, month, year = dv[0], dv[1], dv[2]
        if year:
            if day and month:
                return f"{year:04d}-{month:02d}-{day:02d}"
            if month:
                return f"{year:04d}-{month:02d}"
            return str(year)
    return (date.get("text") or "").strip()


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "family-tree.json"
    dst = sys.argv[2] if len(sys.argv) > 2 else "public/gramps.json"
    recs = load_records(src)

    by_class = {}
    for r in recs:
        by_class.setdefault(r.get("_class"), []).append(r)

    events = {e["handle"]: e for e in by_class.get("Event", [])}
    persons = by_class.get("Person", [])
    families = by_class.get("Family", [])

    # handle -> normalized person id, for resolving family references.
    handle_to_id = {p["handle"]: norm_id(p["gramps_id"]) for p in persons}

    def ref_date(person, index):
        """Resolve a birth/death event_ref_index into a date string."""
        if index is None or index < 0:
            return ""
        refs = person.get("event_ref_list", [])
        if index >= len(refs):
            return ""
        event = events.get(refs[index].get("ref"))
        return event_date(event) if event else ""

    people = {}
    for p in persons:
        pid = norm_id(p["gramps_id"])
        name = p.get("primary_name", {}) or {}
        surnames = name.get("surname_list", []) or []
        last = ""
        for s in surnames:
            if s.get("primary"):
                last = s.get("surname", "")
                break
        if not last and surnames:
            last = surnames[0].get("surname", "")
        people[pid] = {
            "id": pid,
            "data": {
                "first name": (name.get("first_name") or "").strip(),
                "last name": last.strip(),
                "gender": GENDER.get(p.get("gender"), ""),
                "birthday": ref_date(p, p.get("birth_ref_index", -1)),
                "death": ref_date(p, p.get("death_ref_index", -1)),
            },
            "rels": {},
        }

    def rel(pid, key):
        return people[pid]["rels"].setdefault(key, [])

    for fam in families:
        father = handle_to_id.get(fam.get("father_handle"))
        mother = handle_to_id.get(fam.get("mother_handle"))
        parents = [x for x in (father, mother) if x]

        # Spouses reference each other.
        if father and mother:
            if mother not in rel(father, "spouses"):
                rel(father, "spouses").append(mother)
            if father not in rel(mother, "spouses"):
                rel(mother, "spouses").append(father)

        # Children link to each known parent, and vice versa.
        for cref in fam.get("child_ref_list", []):
            child = handle_to_id.get(cref.get("ref"))
            if not child:
                continue
            for parent in parents:
                if parent not in rel(child, "parents"):
                    rel(child, "parents").append(parent)
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
