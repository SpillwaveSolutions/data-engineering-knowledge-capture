#!/usr/bin/env python3
"""Top-level reverse-engineering orchestrator.

Init + breadth-first plan, then optional pause, then domain-scoped walk/capture.
Agent hosts invoke this as the deterministic backbone of
reverse-engineering-orchestrator / data-lake-walker.

Workflow: init-bundle → plan → (optional pause) → scoped walk → (agents enrich
and mark checklists) → existing grade / skeptics / judge.

Query-time retrieve (data-retriever / dekc-retrieve) is a different path.
No live Glue/S3/Fabric control-plane calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import append_log, ensure_bundle, resolve_author, resolve_knowledge_root  # noqa: E402
from dekc_plan import (  # noqa: E402
    checklist_summary,
    load_plan,
    mark_area_item_if_present,
    plan_paths,
    scan_domains_from_plan,
    write_plan,
)
from dekc_validate import validate_bundle  # noqa: E402
from dekc_walk import walk_scoped  # noqa: E402


def _public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": plan.get("system"),
        "system_slug": plan.get("system_slug"),
        "roots": plan.get("roots"),
        "exports": plan.get("exports"),
        "ecosystems": plan.get("ecosystems"),
        "focus_areas": [
            {
                "id": a.get("id"),
                "rank": a.get("rank"),
                "title": a.get("title"),
                "kind": a.get("kind") or "domain",
                "parent": a.get("parent"),
                "signal": a.get("signal"),
                "hit_count": a.get("hit_count"),
                "agent": a.get("agent"),
                "scan_domains": a.get("scan_domains"),
                "spawn": a.get("spawn", True),
                "checklist": a.get("checklist"),
            }
            for a in (plan.get("focus_areas") or [])
        ],
        "specialists": plan.get("specialists")
        or [
            {
                "id": a.get("id"),
                "kind": a.get("kind"),
                "parent": a.get("parent"),
                "agent": a.get("agent"),
                "title": a.get("title"),
                "signal": a.get("signal"),
            }
            for a in (plan.get("focus_areas") or [])
            if a.get("kind") in ("orchestration", "elt-tool")
        ],
        "cicd_handoff": plan.get("cicd_handoff") or [],
        "artifacts": plan.get("artifacts"),
        "written": plan.get("written"),
        "checklist": plan.get("checklist") or checklist_summary(plan),
    }


def _resolve_from_plan(bundle: Path, from_plan: str | Path | None) -> Path:
    if from_plan:
        p = Path(from_plan)
        if not p.is_absolute():
            if p.exists():
                return p.resolve()
            cand = bundle / p
            if cand.exists():
                return cand.resolve()
            return p.resolve()
        return p
    return plan_paths(bundle)["json"]


def orchestrate(
    host_repo: Path,
    scan_roots: list[Path],
    *,
    system_name: str,
    bundle_name: str | None,
    author: str,
    exports: list[Path] | None = None,
    fabric_items: Path | None = None,
    pbi_bindings: Path | None = None,
    inventory: Path | None = None,
    workspace: str = "",
    workspace_id: str = "",
    inventory_layer: str = "gold",
    plan_only: bool = False,
    from_plan: str | Path | None = None,
    area: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    bundle = resolve_knowledge_root(host_repo, bundle_name)
    if not dry_run:
        ensure_bundle(bundle, system_name)
    else:
        bundle.mkdir(parents=True, exist_ok=True)
    phases_done = ["init-bundle"]

    export_paths = list(exports or [])
    if fabric_items:
        export_paths.append(fabric_items)
    if pbi_bindings:
        export_paths.append(pbi_bindings)
    if inventory:
        export_paths.append(inventory)

    if from_plan:
        plan = load_plan(_resolve_from_plan(bundle, from_plan))
        if system_name == "Data platform" and plan.get("system"):
            system_name = plan["system"]
    else:
        plan = write_plan(bundle, scan_roots, system_name=system_name, exports=export_paths)
        phases_done.append("plan")
        append_log(
            bundle,
            "RE plan: areas="
            + ",".join(a["id"] for a in (plan.get("focus_areas") or []))
            + f" checklist={checklist_summary(plan)}",
        )

    if plan_only:
        validation = validate_bundle(bundle)
        return {
            "bundle": str(bundle),
            "system": system_name,
            "phases": phases_done,
            "plan": _public_plan(plan),
            "walk": None,
            "validation": {
                "ok": validation["ok"],
                "errors": validation["errors"],
                "warnings": validation["warnings"],
            },
        }

    domains = scan_domains_from_plan(plan, area=area)
    focus_match = next((a for a in (plan.get("focus_areas") or []) if a.get("id") == area), None)
    enrichment_only = bool(area and focus_match is not None and not (focus_match.get("scan_domains") or []))
    lake_root = scan_roots[0] if scan_roots else None
    walk_payload: dict[str, Any] | None
    if enrichment_only:
        walk_payload = {"created": [], "updated": [], "skipped": [], "errors": [], "domains": [], "counts": {}}
        phases_done.append("enrichment")
    else:
        result = walk_scoped(
            lake_root,
            bundle,
            domains=domains,
            source_name=system_name,
            fabric_items=fabric_items,
            pbi_bindings=pbi_bindings,
            inventory=inventory,
            workspace=workspace,
            workspace_id=workspace_id,
            inventory_layer=inventory_layer,
            dry_run=dry_run,
        )
        walk_payload = result.to_dict()
        walk_payload["domains"] = domains
        phases_done.append("walk")
        if area:
            mark_area_item_if_present(
                bundle, area=area, item="capture", status="done", note="orchestrate --from-plan"
            )
        else:
            for focus in plan.get("focus_areas") or []:
                if "capture" in {i["id"] for i in (focus.get("checklist") or [])}:
                    mark_area_item_if_present(
                        bundle,
                        area=focus["id"],
                        item="capture",
                        status="done",
                        note="orchestrate scoped capture",
                    )
    try:
        plan = load_plan(bundle)
    except FileNotFoundError:
        pass
    validation = validate_bundle(bundle)
    phases_done.append("validate")
    append_log(bundle, f"Orchestrate complete: phases={','.join(phases_done)}")
    return {
        "bundle": str(bundle),
        "system": system_name,
        "phases": phases_done,
        "plan": _public_plan(plan),
        "walk": walk_payload,
        "validation": {
            "ok": validation["ok"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="DEKC reverse-engineering orchestrator")
    p.add_argument("--repo", default=".", help="Knowledge host repo")
    p.add_argument("--bundle", default=None)
    p.add_argument("--system", default="Data platform")
    p.add_argument("--scan-root", action="append", default=[], help="Lake / SQL / job root(s)")
    p.add_argument("--export", action="append", default=[], help="Optional export JSON paths")
    p.add_argument("--fabric-items", default=None)
    p.add_argument("--pbi-bindings", default=None)
    p.add_argument("--inventory", default=None)
    p.add_argument("--workspace", default="")
    p.add_argument("--workspace-id", default="")
    p.add_argument("--inventory-layer", default="gold")
    p.add_argument("--plan-only", action="store_true", help="Init + breadth-first plan, then stop")
    p.add_argument("--from-plan", default=None, help="Existing .dekc/re-plan.json")
    p.add_argument("--area", default=None, help="With --from-plan: one focus area")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--author", default="")
    args = p.parse_args(argv)
    author = ""
    if not args.dry_run:
        author = resolve_author(args.author)
    host = Path(args.repo).resolve()
    roots = [Path(r).resolve() for r in (args.scan_root or ([str(host)] if not args.from_plan else []))]
    result = orchestrate(
        host,
        roots,
        system_name=args.system,
        bundle_name=args.bundle,
        author=author,
        exports=[Path(e).resolve() for e in (args.export or [])],
        fabric_items=Path(args.fabric_items).resolve() if args.fabric_items else None,
        pbi_bindings=Path(args.pbi_bindings).resolve() if args.pbi_bindings else None,
        inventory=Path(args.inventory).resolve() if args.inventory else None,
        workspace=args.workspace,
        workspace_id=args.workspace_id,
        inventory_layer=args.inventory_layer,
        plan_only=args.plan_only,
        from_plan=args.from_plan,
        area=args.area,
        dry_run=args.dry_run,
    )
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Data Engineering Knowledge Capture orchestrate")
        print(f"  bundle: {result['bundle']}")
        print(f"  system: {result['system']}")
        print(f"  phases: {', '.join(result['phases'])}")
        print(f"  valid: {result['validation']['ok']}")
        plan = result.get("plan") or {}
        areas = ", ".join(
            f"{a.get('rank')}:{a.get('id')}({a.get('agent')})" for a in (plan.get("focus_areas") or [])
        )
        if areas:
            print(f"  plan: {areas}")
        if plan.get("checklist"):
            print(f"  checks: {plan['checklist']}")
        written = plan.get("written") or {}
        if written.get("md"):
            print(f"  plan md: {written['md']}")
    return 0 if result["validation"]["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
