#!/usr/bin/env python3
"""Capture Mermaid / PlantUML diagrams and wireframes for DEKC concepts.

Diagrams live as OKF Markdown with fenced ```mermaid or ```plantuml listings.
Wireframes (PlantUML salt/wireframe) attach to Report/Dashboard design work.
Architecture, component, activity, state, class, and ERD diagrams support jobs,
lakes, marts, and catalogs.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    add_typed_link,
    append_log,
    concept_ref,
    ensure_bundle,
    list_concepts,
    path_for_type,
    refresh_catalog_index,
    resolve_knowledge_root,
    slugify,
    utc_now,
    write_concept,
    parse_frontmatter,
    dump_frontmatter,
)

DIAGRAM_KINDS = (
    "wireframe",
    "architecture",
    "component",
    "activity",
    "state",
    "class",
    "erd",
    "sequence",
    "deployment",
    "flowchart",
    "c4",
)

LANGUAGES = ("mermaid", "plantuml")

TEMPLATES: dict[tuple[str, str], str] = {
    ("wireframe", "plantuml"): """\
@startuml
!include <salt/all>
salt
{{+
  {T
    Executive Revenue Dashboard | [Refresh] | [Export]
  }
  {
    Period: ^Last 30 days^ | Currency: ^All^
  }
  {
    {^GMV^
    $1.2M
    }
    |
    {^Orders^
    8,420
    }
    |
    {^AOV^
    $142
    }
  }
  {
    Revenue by day
    ^chart area^
  }
  {
    Top products
    ^table^
  }
}}
@enduml
""",
    ("wireframe", "mermaid"): """\
flowchart TB
  subgraph Header
    T[Title: Executive Revenue]
    F[Filters: Period · Currency]
  end
  subgraph KPIs
    K1[GMV]
    K2[Orders]
    K3[AOV]
  end
  subgraph Charts
    C1[Revenue trend]
    C2[Top products table]
  end
  Header --> KPIs --> Charts
""",
    ("architecture", "mermaid"): """\
flowchart LR
  SRC[Sources / Streams] --> BRZ[Bronze Landing]
  BRZ --> SLV[Silver Cleansed]
  SLV --> GLD[Gold Marts]
  GLD --> SEM[Semantic Model]
  SEM --> RPT[Reports / Dashboards]
  JOB[Jobs / Pipelines] -.-> BRZ
  JOB -.-> SLV
  JOB -.-> GLD
""",
    ("architecture", "plantuml"): """\
@startuml
skinparam componentStyle rectangle
cloud "Sources" as SRC
rectangle "Data Lake" {
  [Bronze] as BRZ
  [Silver] as SLV
  [Gold / Marts] as GLD
}
database "Semantic" as SEM
[Reports] as RPT
SRC --> BRZ
BRZ --> SLV --> GLD --> SEM --> RPT
@enduml
""",
    ("component", "mermaid"): """\
flowchart TB
  subgraph Orchestrator
    WF[Workflow / Pipeline]
  end
  subgraph Compute
    T1[Extract Task]
    T2[Transform Task]
    T3[Load Task]
  end
  subgraph Storage
    S1[(Landing path)]
    S2[(Curated tables)]
  end
  WF --> T1 --> S1
  WF --> T2 --> S2
  WF --> T3 --> S2
""",
    ("component", "plantuml"): """\
@startuml
package "Job" {
  [Orchestrator] as ORC
  [Extract] as E
  [Transform] as T
  [Load] as L
}
database "Lake" as LK
ORC --> E
ORC --> T
ORC --> L
E --> LK
T --> LK
L --> LK
@enduml
""",
    ("activity", "mermaid"): """\
flowchart TD
  A([Start]) --> B[Validate source]
  B --> C{Data OK?}
  C -->|yes| D[Land bronze]
  C -->|no| E[Dead-letter / alert]
  D --> F[Transform silver]
  F --> G[Publish gold]
  G --> H[Run DQ rules]
  H --> I{DQ pass?}
  I -->|yes| J([Success])
  I -->|no| K[Quarantine + notify]
  E --> L([Fail])
  K --> L
""",
    ("activity", "plantuml"): """\
@startuml
start
:Validate source;
if (Data OK?) then (yes)
  :Land bronze;
  :Transform silver;
  :Publish gold;
  :Run DQ rules;
  if (DQ pass?) then (yes)
    stop
  else (no)
    :Quarantine + notify;
    stop
  endif
else (no)
  :Dead-letter / alert;
  stop
endif
@enduml
""",
    ("state", "mermaid"): """\
stateDiagram-v2
  [*] --> Idle
  Idle --> Running: trigger
  Running --> Succeeded: complete
  Running --> Failed: error
  Failed --> Running: retry
  Failed --> DeadLetter: max retries
  Succeeded --> [*]
  DeadLetter --> [*]
""",
    ("state", "plantuml"): """\
@startuml
[*] --> Idle
Idle --> Running : trigger
Running --> Succeeded : complete
Running --> Failed : error
Failed --> Running : retry
Failed --> DeadLetter : max retries
Succeeded --> [*]
DeadLetter --> [*]
@enduml
""",
    ("class", "mermaid"): """\
classDiagram
  class Workflow {
    +name
    +orchestrator
    +schedule
    +mode
  }
  class Task {
    +name
    +retries
  }
  class Table {
    +fqn
    +layer
  }
  class DQRule {
    +rule_type
    +severity
  }
  Workflow "1" --> "*" Task : contains
  Task --> Table : reads_writes
  DQRule --> Table : validates
""",
    ("class", "plantuml"): """\
@startuml
class Workflow {
  +name
  +orchestrator
  +schedule
  +mode
}
class Task {
  +name
  +retries
}
class Table {
  +fqn
  +layer
}
class DQRule {
  +rule_type
  +severity
}
Workflow "1" *-- "*" Task
Task --> Table : reads/writes
DQRule --> Table : validates
@enduml
""",
    ("erd", "mermaid"): """\
erDiagram
  CUSTOMER ||--o{ ORDER : places
  ORDER ||--|{ ORDER_LINE : contains
  PRODUCT ||--o{ ORDER_LINE : "sold as"
  ORDER {
    string order_id PK
    string customer_id FK
    date order_ts
    number gross_amount
  }
  CUSTOMER {
    string customer_id PK
    string segment
  }
  PRODUCT {
    string product_id PK
    string name
  }
  ORDER_LINE {
    string order_id FK
    string product_id FK
    number qty
  }
""",
    ("erd", "plantuml"): """\
@startuml
entity Customer {
  * customer_id : string <<PK>>
  --
  segment : string
}
entity Order {
  * order_id : string <<PK>>
  --
  * customer_id : string <<FK>>
  order_ts : date
  gross_amount : number
}
entity OrderLine {
  * order_id : string <<FK>>
  * product_id : string <<FK>>
  --
  qty : number
}
entity Product {
  * product_id : string <<PK>>
  --
  name : string
}
Customer ||--o{ Order
Order ||--|{ OrderLine
Product ||--o{ OrderLine
@enduml
""",
    ("sequence", "mermaid"): """\
sequenceDiagram
  participant Src as Source/Stream
  participant Job as Landing Job
  participant Brz as Bronze
  participant DQ as DQ Rules
  participant Slv as Silver
  Src->>Job: event/batch
  Job->>Brz: write landing
  Job->>DQ: validate
  DQ-->>Job: pass/fail
  Job->>Slv: promote on pass
""",
    ("sequence", "plantuml"): """\
@startuml
actor Source
participant "Landing Job" as Job
database Bronze
participant DQ
database Silver
Source -> Job : event/batch
Job -> Bronze : write landing
Job -> DQ : validate
DQ --> Job : pass/fail
Job -> Silver : promote on pass
@enduml
""",
    ("flowchart", "mermaid"): """\
flowchart TD
  A[Start] --> B[Process]
  B --> C[End]
""",
    ("deployment", "mermaid"): """\
flowchart TB
  subgraph Cloud
    subgraph Lakehouse
      ST[(Storage)]
      CAT[Catalog]
      COMP[Compute / Jobs]
    end
    BI[BI Workspace]
  end
  ST --- CAT
  COMP --> ST
  BI --> CAT
""",
    ("c4", "mermaid"): """\
flowchart TB
  person[Analyst]
  system[Data Platform]
  person --> system
""",
}


def template_for(kind: str, language: str) -> str:
    key = (kind, language)
    if key in TEMPLATES:
        return TEMPLATES[key]
    if language == "mermaid":
        return TEMPLATES.get((kind, "mermaid")) or TEMPLATES[("flowchart", "mermaid")]
    return TEMPLATES.get((kind, "plantuml")) or TEMPLATES[("architecture", "plantuml")]


def fence(language: str, code: str) -> str:
    lang = "plantuml" if language == "plantuml" else "mermaid"
    code = code.strip() + "\n"
    return f"```{lang}\n{code}```\n"


def resolve_subject(bundle: Path, name: str) -> str:
    """Resolve a subject name or path to an absolute in-bundle concept path."""
    n = name.strip()
    if n.startswith("/") and n.endswith(".md"):
        return n
    if "/" in n and n.endswith(".md"):
        return "/" + n.lstrip("/")
    # exact path under bundle
    cand = bundle / n if not n.startswith("/") else bundle / n.lstrip("/")
    if cand.is_file():
        return "/" + cand.relative_to(bundle).as_posix()

    stem = slugify(Path(n).stem if n.endswith(".md") else n)
    # search concepts by stem, wiki_key, title slug
    hits: list[tuple[int, str]] = []
    for path, fm, _ in list_concepts(bundle):
        rel = "/" + path.relative_to(bundle).as_posix()
        pstem = path.stem
        title_slug = slugify(str(fm.get("title") or ""))
        score = 0
        if pstem == stem or pstem.endswith("-" + stem) or stem in pstem:
            score += 3
        if title_slug == stem:
            score += 4
        if stem in title_slug or title_slug in stem:
            score += 1
        typ = fm.get("type") or ""
        # type-aware boosts from keywords
        low = n.lower()
        prefer = {
            "dashboard": "Dashboard",
            "report": "Report",
            "workflow": "Workflow",
            "job": "Workflow",
            "pipeline": "Workflow",
            "lake": "DataLake",
            "mart": "DataMart",
            "catalog": "DataCatalog",
            "stream": "Stream",
            "table": "Table",
        }
        for key, tname in prefer.items():
            if key in low and typ == tname:
                score += 2
        if score:
            hits.append((score, rel))
    if hits:
        hits.sort(key=lambda x: -x[0])
        return hits[0][1]

    # heuristic default catalogs
    low = n.lower()
    if "dashboard" in low:
        return concept_ref(n, "dashboards")
    if "report" in low:
        return concept_ref(n, "reports")
    if any(k in low for k in ("workflow", "job", "pipeline")):
        return concept_ref(n, "workflows")
    if "lake" in low:
        return concept_ref(n, "lakes")
    if "mart" in low:
        return concept_ref(n, "marts")
    if "catalog" in low:
        return concept_ref(n, "catalogs")
    if "stream" in low:
        return concept_ref(n, "streams")
    return concept_ref(n, "tables")


def capture_diagram(
    bundle: Path,
    *,
    name: str,
    diagram_kind: str,
    language: str = "mermaid",
    description: str = "",
    code: str = "",
    subject: str | None = None,
    subjects: list[str] | None = None,
    use_template: bool = True,
) -> list[tuple[str, str]]:
    diagram_kind = diagram_kind.lower().strip()
    language = language.lower().strip()
    if diagram_kind not in DIAGRAM_KINDS:
        raise ValueError(f"unknown diagram_kind {diagram_kind}; choose from {DIAGRAM_KINDS}")
    if language not in LANGUAGES:
        raise ValueError(f"language must be one of {LANGUAGES}")

    is_wireframe = diagram_kind == "wireframe"
    type_name = "Wireframe" if is_wireframe else "Diagram"
    slug = slugify(f"{diagram_kind}-{name}")
    rel = path_for_type(type_name, slug)

    body_code = code.strip() if code.strip() else (template_for(diagram_kind, language) if use_template else "")
    if not body_code:
        body_code = f"(empty {language} {diagram_kind} diagram)"

    links: list[dict[str, str]] = []
    subj_list = list(subjects or [])
    if subject:
        subj_list.insert(0, subject)
    resolved_subjects: list[str] = []
    for s in subj_list:
        ref = resolve_subject(bundle, s)
        resolved_subjects.append(ref)
        links.append({"target": ref, "rel": "wireframes" if is_wireframe else "documents"})

    fm: dict[str, Any] = {
        "type": type_name,
        "title": name,
        "description": description or f"{diagram_kind} diagram ({language}): {name}",
        "diagram_kind": diagram_kind,
        "language": language,
        "tags": ["diagram", diagram_kind, language, "dekc"]
        + (["wireframe"] if is_wireframe else []),
        "timestamp": utc_now(),
        "status": "active",
        "verified": True,
        "generated": True,
        "stable_timestamp": True,
        "wiki_key": f"{'wireframe' if is_wireframe else 'diagram'}-{slug}",
        "truth_state": "current",
    }
    if resolved_subjects:
        fm["subjects"] = resolved_subjects
        fm["links"] = links

    body = f"# {name}\n\n"
    body += f"**Kind:** `{diagram_kind}` · **Language:** `{language}`\n\n"
    if description:
        body += f"{description}\n\n"
    if resolved_subjects:
        body += "## Subjects\n\n"
        for ref in resolved_subjects:
            body += f"- [{Path(ref).stem}]({ref})\n"
        body += "\n"
    body += "## Diagram\n\n"
    body += fence(language, body_code)
    body += "\n## Notes\n\n"
    body += "_Edit the fenced listing above; keep language tag as `mermaid` or `plantuml`._\n"

    _, action = write_concept(bundle, rel, fm, body)
    catalog = "wireframes" if is_wireframe else "diagrams"
    refresh_catalog_index(bundle, catalog)
    for ref in resolved_subjects:
        _patch_subject(
            bundle,
            ref,
            f"/{rel}",
            "has_wireframe" if is_wireframe else "documented_by",
        )
    append_log(bundle, f"Captured {type_name}: {name} ({diagram_kind}/{language})")
    return [(rel, action)]


def _patch_subject(bundle: Path, src_ref: str, dst_ref: str, rel: str) -> None:
    path = bundle / src_ref.lstrip("/")
    if not path.is_file():
        return
    fm, body = parse_frontmatter(path.read_text(encoding="utf-8"))
    add_typed_link(fm, dst_ref, rel)
    path.write_text(dump_frontmatter(fm) + "\n" + body.rstrip() + "\n", encoding="utf-8")


def list_templates() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for kind, lang in TEMPLATES:
        out.setdefault(kind, []).append(lang)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC diagram / wireframe capture (Mermaid + PlantUML)")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--json", action="store_true")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("capture", help="Capture a diagram or wireframe concept")
    p.add_argument("--name", required=True)
    p.add_argument("--kind", required=True, choices=DIAGRAM_KINDS)
    p.add_argument("--language", default="mermaid", choices=LANGUAGES)
    p.add_argument("--description", default="")
    p.add_argument("--code", default="", help="Inline diagram source (else template)")
    p.add_argument("--code-file", default="", help="Read diagram source from file")
    p.add_argument("--subject", default=None, help="Primary subject concept path or name")
    p.add_argument("--subjects", nargs="*", default=[], help="Additional subject paths/names")
    p.add_argument("--no-template", action="store_true")

    p = sub.add_parser("wireframe", help="Shortcut: wireframe for a report/dashboard")
    p.add_argument("--name", required=True)
    p.add_argument("--subject", required=True, help="Report or dashboard path/name")
    p.add_argument("--description", default="")
    p.add_argument("--language", default="plantuml", choices=LANGUAGES)
    p.add_argument("--code", default="")
    p.add_argument("--code-file", default="")

    p = sub.add_parser("templates", help="List built-in templates")
    p.add_argument("--show", nargs=2, metavar=("KIND", "LANG"), help="Print one template")

    p = sub.add_parser("job-pack", help="Scaffold job diagrams: activity + state + class + component")
    p.add_argument("--workflow", required=True, help="Workflow name or path")
    p.add_argument("--language", default="mermaid", choices=LANGUAGES)

    p = sub.add_parser("report-pack", help="Scaffold report/dashboard wireframe")
    p.add_argument("--subject", required=True)
    p.add_argument("--name", default="")
    p.add_argument("--language", default="plantuml", choices=LANGUAGES)

    args = parser.parse_args(argv)

    if args.cmd == "templates":
        if args.show:
            kind, lang = args.show
            print(template_for(kind, lang))
            return 0
        data = list_templates()
        if args.json:
            print(json.dumps(data, indent=2))
        else:
            for k, langs in sorted(data.items()):
                print(f"{k}: {', '.join(langs)}")
        return 0

    repo = Path(args.repo).resolve()
    bundle = resolve_knowledge_root(repo, args.bundle)
    ensure_bundle(bundle)
    results: list[tuple[str, str]] = []

    def load_code(code: str, code_file: str) -> str:
        if code_file:
            return Path(code_file).read_text(encoding="utf-8")
        return code

    if args.cmd == "capture":
        results = capture_diagram(
            bundle,
            name=args.name,
            diagram_kind=args.kind,
            language=args.language,
            description=args.description,
            code=load_code(args.code, args.code_file),
            subject=args.subject,
            subjects=args.subjects,
            use_template=not args.no_template,
        )
    elif args.cmd == "wireframe":
        results = capture_diagram(
            bundle,
            name=args.name,
            diagram_kind="wireframe",
            language=args.language,
            description=args.description or f"Wireframe for {args.subject}",
            code=load_code(args.code, args.code_file),
            subject=args.subject,
            use_template=not bool(args.code or args.code_file),
        )
    elif args.cmd == "job-pack":
        wf = args.workflow
        base = Path(wf).stem if wf.endswith(".md") else slugify(wf)
        for kind in ("activity", "state", "class", "component"):
            results.extend(
                capture_diagram(
                    bundle,
                    name=f"{base}-{kind}",
                    diagram_kind=kind,
                    language=args.language,
                    description=f"{kind} diagram for workflow {wf}",
                    subject=wf,
                )
            )
    elif args.cmd == "report-pack":
        subj = args.subject
        name = args.name or f"{Path(subj).stem}-wireframe"
        results = capture_diagram(
            bundle,
            name=name,
            diagram_kind="wireframe",
            language=args.language,
            description=f"Wireframe for {subj}",
            subject=subj,
        )
    else:
        parser.error(f"unknown cmd {args.cmd}")

    if args.json:
        print(json.dumps([{"path": p, "action": a} for p, a in results], indent=2))
    else:
        for pth, act in results:
            print(f"{act:8} {pth}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
