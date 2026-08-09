#!/usr/bin/env python3
"""List and validate DEKC standard OKF concept schemas."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import list_concepts, resolve_knowledge_root  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = ROOT / "schemas" / "okf-concepts"
REGISTRY = SCHEMA_DIR / "registry.json"


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def load_schema(type_name: str) -> dict | None:
    path = SCHEMA_DIR / f"{type_name}.schema.json"
    if not path.is_file():
        # Dataset aliases Table schema
        if type_name == "Dataset":
            path = SCHEMA_DIR / "Table.schema.json"
        else:
            return None
    return json.loads(path.read_text(encoding="utf-8"))


def _type_ok(value, schema_type) -> bool:
    if isinstance(schema_type, list):
        return any(_type_ok(value, t) for t in schema_type)
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "array":
        return isinstance(value, list)
    if schema_type == "object":
        return isinstance(value, dict)
    return True


def validate_frontmatter(fm: dict, schema: dict) -> list[str]:
    """Minimal JSON-Schema subset validator (no external deps)."""
    errors: list[str] = []
    required = schema.get("required") or []
    props = schema.get("properties") or {}
    for key in required:
        if key not in fm or fm[key] in (None, ""):
            errors.append(f"missing required `{key}`")
    for key, value in fm.items():
        if key not in props:
            continue  # additionalProperties allowed
        p = props[key]
        if "const" in p and value != p["const"]:
            errors.append(f"`{key}` must be {p['const']!r}, got {value!r}")
        if "enum" in p and value not in p["enum"]:
            # allow empty string for optional enums used loosely
            if value != "":
                errors.append(f"`{key}` value {value!r} not in enum {p['enum']}")
        if "type" in p and not _type_ok(value, p["type"]):
            errors.append(f"`{key}` wrong type for {p['type']}")
        if p.get("type") == "array" and isinstance(value, list):
            item = p.get("items") or {}
            if item.get("type") == "object":
                for i, el in enumerate(value):
                    if not isinstance(el, dict):
                        errors.append(f"`{key}[{i}]` must be object")
                        continue
                    for rk in item.get("required") or []:
                        if rk not in el:
                            errors.append(f"`{key}[{i}]` missing `{rk}`")
    return errors


def validate_bundle(bundle: Path, *, strict_unknown: bool = False) -> dict:
    reg = load_registry()
    known = set(reg.get("concepts") or [])
    issues: list[dict] = []
    ok_count = 0
    for path, fm, _ in list_concepts(bundle):
        rel = path.relative_to(bundle).as_posix()
        t = fm.get("type")
        if not t:
            issues.append({"path": rel, "errors": ["missing type"]})
            continue
        if t not in known and t != "DesignPattern":
            if strict_unknown:
                issues.append({"path": rel, "errors": [f"unknown type {t}"]})
            continue
        schema = load_schema(t if t != "DesignPattern" else "DesignPattern")
        if not schema:
            continue
        errs = validate_frontmatter(fm, schema)
        if errs:
            issues.append({"path": rel, "type": t, "errors": errs})
        else:
            ok_count += 1
    return {
        "bundle": str(bundle),
        "schema_registry": str(REGISTRY),
        "validated_ok": ok_count,
        "issue_count": len(issues),
        "issues": issues[:50],
        "ok": len(issues) == 0,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC OKF concept schemas")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list", help="List registered concept schemas")
    p_list.add_argument("--json", action="store_true")

    p_show = sub.add_parser("show", help="Show one schema")
    p_show.add_argument("type")
    p_show.add_argument("--json", action="store_true")

    p_val = sub.add_parser("validate", help="Validate bundle concepts against schemas")
    p_val.add_argument("--repo", default=".")
    p_val.add_argument("--bundle", default=None)
    p_val.add_argument("--json", action="store_true")
    p_val.add_argument("--strict-unknown", action="store_true")

    p_int = sub.add_parser("intents", help="Show design intents → preferred types")
    p_int.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    reg = load_registry()

    if args.cmd == "list":
        if args.json:
            print(json.dumps(reg, indent=2))
        else:
            print(f"DEKC schema registry v{reg.get('version')} (okf {reg.get('okf_version')})")
            print(f"  {reg.get('description')}")
            print("  concepts:")
            for c in reg.get("concepts") or []:
                path = SCHEMA_DIR / f"{c}.schema.json"
                mark = "✓" if path.is_file() else "·"
                print(f"    {mark} {c}")
        return 0

    if args.cmd == "show":
        schema = load_schema(args.type)
        if not schema:
            print(f"unknown type: {args.type}", file=sys.stderr)
            return 1
        print(json.dumps(schema, indent=2))
        return 0

    if args.cmd == "intents":
        intents = reg.get("intents") or {}
        if args.json:
            print(json.dumps(intents, indent=2))
        else:
            for name, types in intents.items():
                print(f"{name}:")
                for t in types:
                    print(f"  - {t}")
        return 0

    if args.cmd == "validate":
        bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
        report = validate_bundle(bundle, strict_unknown=args.strict_unknown)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(f"DEKC schema validate · {report['bundle']}")
            print(f"  ok concepts: {report['validated_ok']}")
            print(f"  issues:      {report['issue_count']}")
            for iss in report["issues"][:20]:
                print(f"  - {iss['path']}: {', '.join(iss['errors'])}")
        return 0 if report["ok"] else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
