#!/usr/bin/env python3
"""Stdlib SQLite + FTS5 incremental index for a DEKC bundle.

Git + Markdown stays the source of truth. `knowledge/.dekc/index.sqlite` is a
disposable accelerator: delete it and the next reader rebuilds. Every reader
self-heals via mtime+size rather than trusting a hook.

Do not copy the old JSON `.index/` (inventory + inverted tokens). That was a
full rebuild plus a JSON parse, and it got committed by accident.

Ladder (one behavior, three tiers):

    index present  →  use it
    else rg on PATH  →  prefilter
    else             →  pure Python scan

FTS5 MATCH is the `--engine fts` opt-in. Default candidate selection is
SQL LIKE on a stored haystack so ranking stays identical to a full scan
(Python still scores).

Usage:
  python3 scripts/dekc_index.py status --bundle sample-knowledge
  python3 scripts/dekc_index.py refresh --bundle sample-knowledge
  python3 scripts/dekc_index.py drop --bundle sample-knowledge
  python3 scripts/dekc_index.py build --bundle sample-knowledge   # alias: refresh --force
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from dekc_common import (  # noqa: E402
    iter_concept_paths,
    iter_typed_edges,
    parse_frontmatter,
    resolve_knowledge_root,
    toolchain_report,
)
from dekc_lineage import (  # noqa: E402
    FORWARD_FLOW,
    REVERSE_FLOW,
    extract_edges_from_sql,
    _resolve_name,
)

SCHEMA_VERSION = 1
INDEX_NAME = "index.sqlite"
LINEAGE_RELS = frozenset(FORWARD_FLOW + REVERSE_FLOW) | {"sql_from"}


@dataclass
class NodeRow:
    path: str
    type: str
    title: str
    description: str
    status: str
    tags: str
    layer: str
    mtime: int
    size: int
    fm_json: str
    body: str
    hay: str

    def frontmatter(self) -> dict[str, Any]:
        try:
            data = json.loads(self.fm_json)
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}


@dataclass
class RefreshStats:
    ok: bool
    path: str
    nodes: int = 0
    edges: int = 0
    parsed: int = 0
    unchanged: int = 0
    deleted: int = 0
    rebuilt: bool = False
    ms: float = 0.0
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "path": self.path,
            "nodes": self.nodes,
            "edges": self.edges,
            "parsed": self.parsed,
            "unchanged": self.unchanged,
            "deleted": self.deleted,
            "rebuilt": self.rebuilt,
            "ms": round(self.ms, 2),
            "error": self.error,
        }


def fts5_available() -> bool:
    report = toolchain_report()
    sqlite = report.get("sqlite") or {}
    return bool(sqlite.get("fts5"))


def index_enabled() -> bool:
    """DEKC_NO_INDEX=1 disables the index for the process (tests, --no-index)."""
    flag = os.environ.get("DEKC_NO_INDEX", "").strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return False
    return fts5_available()


def index_path(bundle: Path) -> Path:
    override = os.environ.get("DEKC_INDEX_PATH", "").strip()
    if override:
        return Path(override)
    return bundle / ".dekc" / INDEX_NAME


def _connect(path: Path, *, create: bool) -> sqlite3.Connection | None:
    if not fts5_available():
        return None
    if not create and not path.is_file():
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path), timeout=5.0)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA busy_timeout=5000")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _schema_version(con: sqlite3.Connection) -> int | None:
    try:
        row = con.execute(
            "SELECT value FROM meta WHERE key = 'schema_version'"
        ).fetchone()
    except sqlite3.DatabaseError:
        return None
    if not row:
        return None
    try:
        return int(row[0])
    except (TypeError, ValueError):
        return None


def _init_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS nodes (
            path TEXT PRIMARY KEY,
            type TEXT,
            title TEXT,
            description TEXT,
            status TEXT,
            tags TEXT,
            layer TEXT,
            mtime INTEGER NOT NULL,
            size INTEGER NOT NULL,
            fm_json TEXT NOT NULL,
            body TEXT NOT NULL,
            hay TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS edges (
            src TEXT NOT NULL,
            dst TEXT NOT NULL,
            rel TEXT NOT NULL,
            label TEXT,
            origin TEXT NOT NULL DEFAULT '',
            PRIMARY KEY (src, dst, rel, origin)
        );
        CREATE INDEX IF NOT EXISTS edges_dst ON edges(dst);
        CREATE INDEX IF NOT EXISTS edges_src ON edges(src);
        CREATE VIRTUAL TABLE IF NOT EXISTS fts USING fts5(
            path,
            title,
            description,
            tags,
            body,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        """
    )
    con.execute(
        "INSERT OR REPLACE INTO meta(key, value) VALUES ('schema_version', ?)",
        (str(SCHEMA_VERSION),),
    )
    con.commit()


def _drop_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        DROP TABLE IF EXISTS fts;
        DROP TABLE IF EXISTS edges;
        DROP TABLE IF EXISTS nodes;
        DROP TABLE IF EXISTS meta;
        """
    )
    con.commit()


def _ensure_schema(con: sqlite3.Connection) -> bool:
    """Return True if the schema was rebuilt from scratch."""
    version = _schema_version(con)
    if version == SCHEMA_VERSION:
        return False
    _drop_schema(con)
    _init_schema(con)
    return True


def _sig(path: Path) -> tuple[int, int]:
    st = path.stat()
    mtime = getattr(st, "st_mtime_ns", int(st.st_mtime * 1_000_000_000))
    return int(mtime), int(st.st_size)


def _hay(title: str, description: str, tags: str, body: str) -> str:
    return f"{title}\n{description}\n{tags}\n{body}".lower()


def _norm_target(tgt: str) -> str:
    tgt = str(tgt or "").strip()
    if not tgt:
        return ""
    if not tgt.startswith("/"):
        tgt = "/" + tgt.lstrip("./")
    return tgt


def extract_dekc_edges(
    bundle: Path, rel: str, fm: dict[str, Any], body: str
) -> list[tuple[str, str, str, str]]:
    """Return (src, dst, rel, label) including SQL lineage edges."""
    out: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for tgt, r in iter_typed_edges(fm):
        tgt = _norm_target(tgt)
        if not tgt:
            continue
        key = (rel, tgt, str(r))
        if key in seen:
            continue
        seen.add(key)
        out.append((rel, tgt, str(r), Path(tgt).stem))
    if "```sql" in body.lower():
        m = re.search(r"```sql\n(.*?)```", body, re.DOTALL | re.IGNORECASE)
        if m:
            for up, down in extract_edges_from_sql(m.group(1)):
                up_ref = _resolve_name(bundle, up)
                down_ref = _resolve_name(bundle, down)
                if not up_ref or not down_ref:
                    continue
                key = (up_ref, down_ref, "sql_from")
                if key in seen:
                    continue
                seen.add(key)
                out.append((up_ref, down_ref, "sql_from", down))
    return out


def _upsert_node(con: sqlite3.Connection, bundle: Path, rel: str, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    fm, body = parse_frontmatter(text)
    title = str(fm.get("title") or path.stem)
    description = str(fm.get("description") or "")
    status = str(fm.get("status") or "")
    layer = str(fm.get("layer") or "")
    tags_val = fm.get("tags") or []
    if isinstance(tags_val, list):
        tags = " ".join(str(t) for t in tags_val)
    else:
        tags = str(tags_val)
    ctype = str(fm.get("type") or "Unknown")
    mtime, size = _sig(path)
    fm_json = json.dumps(fm, default=str, ensure_ascii=False)
    hay = _hay(title, description, tags, body)
    con.execute(
        """
        INSERT OR REPLACE INTO nodes(
            path, type, title, description, status, tags, layer,
            mtime, size, fm_json, body, hay
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (rel, ctype, title, description, status, tags, layer, mtime, size, fm_json, body, hay),
    )
    con.execute("DELETE FROM edges WHERE origin = ? OR (origin = '' AND src = ?)", (rel, rel))
    con.execute("DELETE FROM fts WHERE path = ?", (rel,))
    edges = extract_dekc_edges(bundle, rel, fm, body)
    if edges:
        con.executemany(
            "INSERT OR IGNORE INTO edges(src, dst, rel, label, origin) VALUES (?, ?, ?, ?, ?)",
            [(src, dst, r, label, rel) for src, dst, r, label in edges],
        )
    con.execute(
        "INSERT INTO fts(path, title, description, tags, body) VALUES (?, ?, ?, ?, ?)",
        (rel, title, description, tags, body),
    )


def refresh(bundle: Path, *, force: bool = False) -> RefreshStats | None:
    """Self-healing incremental refresh. None = index unavailable (no FTS5)."""
    if not index_enabled() and not force:
        return None
    if not fts5_available():
        return None
    started = time.perf_counter()
    path = index_path(bundle)
    stats = RefreshStats(ok=True, path=str(path))
    con = _connect(path, create=True)
    if con is None:
        stats.ok = False
        stats.error = "sqlite/fts5 unavailable"
        return stats
    try:
        rebuilt = _ensure_schema(con)
        if force:
            _drop_schema(con)
            _init_schema(con)
            rebuilt = True
        stats.rebuilt = rebuilt

        disk: dict[str, Path] = {}
        disk_sig: dict[str, tuple[int, int]] = {}
        for p in iter_concept_paths(bundle):
            rel = "/" + p.relative_to(bundle).as_posix()
            disk[rel] = p
            try:
                disk_sig[rel] = _sig(p)
            except OSError:
                continue

        stored = {
            row["path"]: (int(row["mtime"]), int(row["size"]))
            for row in con.execute("SELECT path, mtime, size FROM nodes")
        }

        vanished = set(stored) - set(disk_sig)
        for rel in vanished:
            con.execute("DELETE FROM nodes WHERE path = ?", (rel,))
            con.execute("DELETE FROM edges WHERE origin = ? OR src = ?", (rel, rel))
            con.execute("DELETE FROM fts WHERE path = ?", (rel,))
            stats.deleted += 1

        for rel, p in disk.items():
            sig = disk_sig.get(rel)
            if sig is None:
                continue
            if not rebuilt and stored.get(rel) == sig:
                stats.unchanged += 1
                continue
            try:
                _upsert_node(con, bundle, rel, p)
            except (OSError, UnicodeDecodeError):
                continue
            stats.parsed += 1

        con.commit()
        stats.nodes = int(con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
        stats.edges = int(con.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
        stats.ms = (time.perf_counter() - started) * 1000
        con.execute(
            "INSERT OR REPLACE INTO meta(key, value) VALUES ('refreshed_ms', ?)",
            (str(int(time.time() * 1000)),),
        )
        con.commit()
        return stats
    except sqlite3.DatabaseError as exc:
        stats.ok = False
        stats.error = str(exc)
        stats.ms = (time.perf_counter() - started) * 1000
        return stats
    finally:
        con.close()


class GraphIndex:
    """Open connection after a refresh. One per search/pack call."""

    def __init__(self, bundle: Path, con: sqlite3.Connection, stats: RefreshStats):
        self.bundle = bundle
        self.con = con
        self.stats = stats

    def close(self) -> None:
        try:
            self.con.close()
        except sqlite3.Error:
            pass

    def __enter__(self) -> "GraphIndex":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def inbound(self, target: str) -> list[tuple[str, str, str]]:
        rows = self.con.execute(
            "SELECT rel, src, label FROM edges WHERE dst = ?", (target,)
        ).fetchall()
        return [(row["rel"], row["src"], row["label"] or "") for row in rows]

    def neighbors(self, node: str, *, lineage_only: bool = True) -> list[str]:
        """Undirected neighbors. lineage_only matches dekc_pack's build_graph walk."""
        rows = self.con.execute(
            "SELECT src, dst, rel FROM edges WHERE src = ? OR dst = ?",
            (node, node),
        ).fetchall()
        out: list[str] = []
        seen: set[str] = set()
        for row in rows:
            rel = row["rel"] or ""
            if lineage_only and rel not in LINEAGE_RELS:
                continue
            other = row["dst"] if row["src"] == node else row["src"]
            if other == node or other in seen:
                continue
            seen.add(other)
            out.append(other)
        return out

    def node(self, rel: str) -> NodeRow | None:
        row = self.con.execute(
            """
            SELECT path, type, title, description, status, tags, layer,
                   mtime, size, fm_json, body, hay
            FROM nodes WHERE path = ?
            """,
            (rel,),
        ).fetchone()
        if not row:
            return None
        return _row_to_node(row)

    def candidates(self, terms: list[str], *, engine: str = "index") -> list[Path]:
        terms = [t for t in terms if t]
        if not terms:
            return []
        if engine == "fts":
            query = " AND ".join('"' + t.replace('"', '""') + '"*' for t in terms)
            rows = self.con.execute(
                "SELECT path FROM fts WHERE fts MATCH ?", (query,)
            ).fetchall()
        else:
            clause = " AND ".join("hay LIKE ? ESCAPE '\\'" for _ in terms)
            params = [_like_term(t.lower()) for t in terms]
            rows = self.con.execute(
                f"SELECT path FROM nodes WHERE {clause}", params
            ).fetchall()
        return [self.bundle / row["path"].lstrip("/") for row in rows]

    def iter_nodes(self) -> list[NodeRow]:
        rows = self.con.execute(
            """
            SELECT path, type, title, description, status, tags, layer,
                   mtime, size, fm_json, body, hay
            FROM nodes ORDER BY path
            """
        ).fetchall()
        return [_row_to_node(row) for row in rows]


def _row_to_node(row: sqlite3.Row) -> NodeRow:
    return NodeRow(
        path=row["path"],
        type=row["type"] or "Unknown",
        title=row["title"] or "",
        description=row["description"] or "",
        status=row["status"] or "",
        tags=row["tags"] or "",
        layer=row["layer"] or "",
        mtime=int(row["mtime"]),
        size=int(row["size"]),
        fm_json=row["fm_json"] or "{}",
        body=row["body"] or "",
        hay=row["hay"] or "",
    )


def open_graph(bundle: Path, *, force: bool = False) -> GraphIndex | None:
    stats = refresh(bundle, force=force)
    if stats is None or not stats.ok:
        return None
    con = _connect(index_path(bundle), create=False)
    if con is None:
        return None
    return GraphIndex(bundle, con, stats)


def drop_index(bundle: Path) -> bool:
    path = index_path(bundle)
    gone = False
    for suffix in ("", "-journal", "-wal", "-shm"):
        p = Path(str(path) + suffix) if suffix else path
        if p.is_file():
            p.unlink()
            gone = True
    return gone


def _like_term(term: str) -> str:
    return "%" + term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def candidates(bundle: Path, terms: list[str], *, engine: str = "index") -> list[Path] | None:
    graph = open_graph(bundle)
    if graph is None:
        return None
    try:
        return graph.candidates(terms, engine=engine)
    finally:
        graph.close()


def inbound(bundle: Path, target: str) -> list[tuple[str, str, str]] | None:
    graph = open_graph(bundle)
    if graph is None:
        return None
    try:
        return graph.inbound(target)
    finally:
        graph.close()


def status(bundle: Path) -> dict[str, Any]:
    path = index_path(bundle)
    payload = {
        "path": str(path),
        "present": path.is_file(),
        "fts5": fts5_available(),
        "enabled": index_enabled(),
        "schema_version": SCHEMA_VERSION,
        "nodes": 0,
        "edges": 0,
        "on_disk_schema": None,
        "engine": "dekc-sqlite-fts5-v1",
    }
    if not path.is_file():
        return payload
    con = _connect(path, create=False)
    if con is None:
        return payload
    try:
        payload["on_disk_schema"] = _schema_version(con)
        payload["nodes"] = int(con.execute("SELECT COUNT(*) FROM nodes").fetchone()[0])
        payload["edges"] = int(con.execute("SELECT COUNT(*) FROM edges").fetchone()[0])
    except sqlite3.DatabaseError as exc:
        payload["error"] = str(exc)
    finally:
        con.close()
    return payload


# ── compatibility wrappers (dekc_brain / existing tests) ────────────────


def build_index(bundle: Path) -> dict[str, Any]:
    """Force-rebuild. Replaces the old JSON `.index/` writer."""
    stats = refresh(bundle, force=True)
    if stats is None:
        return {"ok": False, "error": "sqlite/fts5 unavailable", "engine": "dekc-sqlite-fts5-v1"}
    payload = stats.as_dict()
    payload["engine"] = "dekc-sqlite-fts5-v1"
    payload["files"] = [".dekc/index.sqlite"]
    payload["concept_count"] = stats.nodes
    payload["edge_count"] = stats.edges
    return payload


def search_index(bundle: Path, query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Ranked hits. Delegates to dekc_search so scores match a full scan."""
    from dekc_search import search as _search

    hits, _engine = _search(bundle, query, limit=limit)
    return hits


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="DEKC SQLite/FTS5 incremental index")
    parser.add_argument(
        "action",
        choices=("status", "refresh", "drop", "build", "search"),
        help="build is an alias for refresh --force (kept for CI / skills)",
    )
    parser.add_argument("--repo", default=".")
    parser.add_argument("--bundle", default=None)
    parser.add_argument("--force", action="store_true", help="Drop and rebuild (refresh only)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("query", nargs="?", default="", help="Search query (search action)")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args(argv)

    bundle = resolve_knowledge_root(Path(args.repo).resolve(), args.bundle)
    if not bundle.is_dir():
        print(f"error: bundle not found: {bundle}", file=sys.stderr)
        return 1

    if args.action == "drop":
        dropped = drop_index(bundle)
        payload = {"dropped": dropped, "path": str(index_path(bundle))}
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(f"dropped {payload['path']}" if dropped else f"no index at {payload['path']}")
        return 0

    if args.action == "search":
        if not args.query:
            print("error: search requires a query", file=sys.stderr)
            return 2
        hits = search_index(bundle, args.query, args.limit)
        print(json.dumps(hits, indent=2))
        return 0

    if args.action in {"refresh", "build"}:
        stats = refresh(bundle, force=args.force or args.action == "build")
        if stats is None:
            print("error: SQLite FTS5 unavailable; index disabled", file=sys.stderr)
            return 1
        payload = stats.as_dict()
        payload["engine"] = "dekc-sqlite-fts5-v1"
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"index {stats.path}: nodes={stats.nodes} edges={stats.edges} "
                f"parsed={stats.parsed} unchanged={stats.unchanged} "
                f"deleted={stats.deleted} rebuilt={stats.rebuilt} {stats.ms:.1f}ms"
            )
        return 0 if stats.ok else 1

    payload = status(bundle)
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        state = "present" if payload["present"] else "absent"
        print(f"index {payload['path']}: {state}")
        print(f"  FTS5: {'yes' if payload['fts5'] else 'no'}")
        print(f"  enabled: {payload['enabled']}")
        if payload["present"]:
            print(f"  nodes: {payload['nodes']}")
            print(f"  edges: {payload['edges']}")
            print(f"  schema: {payload['on_disk_schema']} (code {SCHEMA_VERSION})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
