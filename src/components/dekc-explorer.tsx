import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  BookOpen,
  Boxes,
  Database,
  GitBranch,
  Layers,
  Radar,
  Search,
  Sparkles,
  Workflow,
} from "lucide-react";
import { Link } from "@tanstack/react-router";
import { SignedIn, SignedOut, UserButton } from "@/lib/auth/gates";
import { useCurrentUserState } from "@/lib/auth/use-current-user";
import {
  type CatalogConcept,
  type CatalogPayload,
  PRIMARY_TYPES,
  TYPE_LABELS,
  layerTone,
  typeTone,
} from "@/lib/catalog";

type Tab = "catalog" | "lineage" | "glossary" | "agents";

export function DekcExplorer() {
  const [data, setData] = useState<CatalogPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [layerFilter, setLayerFilter] = useState<string>("all");
  const [selected, setSelected] = useState<CatalogConcept | null>(null);
  const [tab, setTab] = useState<Tab>("catalog");
  const { isPending } = useCurrentUserState();

  useEffect(() => {
    fetch("/data/catalog.json")
      .then((r) => {
        if (!r.ok) throw new Error(`catalog ${r.status}`);
        return r.json();
      })
      .then((payload: CatalogPayload) => {
        setData(payload);
        const focus =
          payload.concepts.find((c) => c.path.includes("gold-order-daily")) ||
          payload.concepts.find((c) => c.type === "Table") ||
          payload.concepts[0] ||
          null;
        setSelected(focus);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const counts = useMemo(() => {
    const map = new Map<string, number>();
    for (const c of data?.concepts || []) {
      map.set(c.type, (map.get(c.type) || 0) + 1);
    }
    return map;
  }, [data]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    return data.concepts
      .filter((c) => PRIMARY_TYPES.includes(c.type as (typeof PRIMARY_TYPES)[number]) || typeFilter !== "all")
      .filter((c) => (typeFilter === "all" ? true : c.type === typeFilter))
      .filter((c) =>
        layerFilter === "all" ? true : (c.layer || "").toLowerCase() === layerFilter,
      )
      .filter((c) => {
        if (!q) return true;
        return (
          c.title.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.path.toLowerCase().includes(q) ||
          c.tags.some((t) => t.toLowerCase().includes(q))
        );
      })
      .sort((a, b) => a.title.localeCompare(b.title));
  }, [data, query, typeFilter, layerFilter]);

  const glossary = useMemo(
    () =>
      (data?.concepts || []).filter(
        (c) => c.type === "GlossaryTerm" || c.type === "BusinessObject",
      ),
    [data],
  );

  const agents = useMemo(
    () => (data?.concepts || []).filter((c) => c.type === "AgentNode"),
    [data],
  );

  const lineageEdges = useMemo(() => {
    if (!data) return [] as Array<{ from: string; to: string }>;
    const edges: Array<{ from: string; to: string }> = [];
    for (const [from, tos] of Object.entries(data.graph || {})) {
      for (const to of tos) edges.push({ from, to });
    }
    return edges;
  }, [data]);

  return (
    <div className="min-h-dvh bg-bg text-fg">
      <header className="sticky top-0 z-20 border-b border-border/80 bg-bg/90 backdrop-blur-md pt-[var(--grok-banner-h,0px)]">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-md border border-primary/40 bg-primary/15 text-primary">
              <Database className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h1 className="truncate text-base font-semibold tracking-tight sm:text-lg">
                  DEKC
                </h1>
                <span className="rounded-full border border-border px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-muted">
                  v0.1.0
                </span>
              </div>
              <p className="truncate text-xs text-muted">
                Data Engineering Knowledge Capture · PKC + OKF
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isPending ? (
              <div className="h-8 w-8 animate-pulse rounded-full bg-surface-2" />
            ) : (
              <>
                <SignedOut>
                  <Link
                    to="/login"
                    className="rounded-md border border-border px-3 py-1.5 text-sm text-muted transition hover:border-primary/40 hover:text-fg"
                  >
                    Sign in
                  </Link>
                </SignedOut>
                <SignedIn>
                  <UserButton />
                </SignedIn>
              </>
            )}
          </div>
        </div>
      </header>

      <section className="border-b border-border bg-[radial-gradient(ellipse_at_top,_rgba(13,148,136,0.12),_transparent_55%)]">
        <div className="mx-auto grid max-w-7xl gap-6 px-4 py-8 sm:px-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="space-y-4">
            <p className="font-mono text-xs uppercase tracking-[0.16em] text-primary">
              Second brain for data platforms
            </p>
            <h2 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">
              Walk the lake. Capture lineage. Speak business.
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-muted sm:text-base">
              DEKC extends{" "}
              <span className="text-fg">Project Knowledge Capture (PKC)</span> and
              depends on <span className="text-fg">OKF</span>. Agents inventory
              schemas, tables, SQL/DAX, medallion layers, dashboards, and promote
              them into glossary-backed business objects — indexed for LLMs.
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                "Claude Code",
                "Grok Build",
                "Codex",
                "OpenCode",
              ].map((host) => (
                <span
                  key={host}
                  className="rounded-full border border-border bg-surface px-2.5 py-1 text-xs text-muted"
                >
                  {host}
                </span>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Stat
              icon={<Layers className="h-4 w-4 text-bronze" />}
              label="Concepts"
              value={data?.concepts.length ?? "—"}
            />
            <Stat
              icon={<GitBranch className="h-4 w-4 text-accent" />}
              label="Lineage edges"
              value={lineageEdges.length}
            />
            <Stat
              icon={<BookOpen className="h-4 w-4 text-primary" />}
              label="Business / glossary"
              value={glossary.length}
            />
            <Stat
              icon={<Radar className="h-4 w-4 text-gold" />}
              label="Agent walks"
              value={agents.length}
            />
          </div>
        </div>
      </section>

      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
        <div className="mb-4 flex flex-wrap gap-2">
          {(
            [
              ["catalog", "Catalog", Database],
              ["lineage", "Lineage", GitBranch],
              ["glossary", "Business & glossary", BookOpen],
              ["agents", "Agents", Sparkles],
            ] as const
          ).map(([id, label, Icon]) => (
            <button
              key={id}
              type="button"
              onClick={() => setTab(id)}
              className={`inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition ${
                tab === id
                  ? "border-primary/50 bg-primary/15 text-fg"
                  : "border-border bg-surface text-muted hover:border-border hover:text-fg"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </button>
          ))}
        </div>

        {error && (
          <div className="mb-4 rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
            Failed to load catalog: {error}
          </div>
        )}

        {!data && !error && (
          <div className="panel animate-pulse p-8 text-sm text-muted">
            Loading sample knowledge…
          </div>
        )}

        {data && tab === "catalog" && (
          <div className="grid gap-4 lg:grid-cols-[280px_1fr_320px]">
            <aside className="panel p-3">
              <p className="mb-2 px-1 font-mono text-[10px] uppercase tracking-[0.14em] text-muted">
                Filters
              </p>
              <div className="relative mb-3">
                <Search className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search concepts…"
                  className="w-full rounded-md border border-border bg-bg py-2 pl-9 pr-3 text-sm outline-none ring-primary/40 placeholder:text-muted focus:ring-2"
                />
              </div>
              <label className="mb-1 block px-1 text-xs text-muted">Type</label>
              <select
                value={typeFilter}
                onChange={(e) => setTypeFilter(e.target.value)}
                className="mb-3 w-full rounded-md border border-border bg-bg px-2 py-2 text-sm"
              >
                <option value="all">All primary types</option>
                {PRIMARY_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {TYPE_LABELS[t] || t} ({counts.get(t) || 0})
                  </option>
                ))}
              </select>
              <label className="mb-1 block px-1 text-xs text-muted">Layer</label>
              <select
                value={layerFilter}
                onChange={(e) => setLayerFilter(e.target.value)}
                className="mb-4 w-full rounded-md border border-border bg-bg px-2 py-2 text-sm"
              >
                <option value="all">All layers</option>
                {["bronze", "silver", "gold"].map((l) => (
                  <option key={l} value={l}>
                    {l}
                  </option>
                ))}
              </select>
              <div className="space-y-1">
                {filtered.slice(0, 80).map((c) => (
                  <button
                    key={c.path}
                    type="button"
                    onClick={() => setSelected(c)}
                    className={`w-full rounded-md px-2.5 py-2 text-left transition ${
                      selected?.path === c.path
                        ? "bg-primary/15 ring-1 ring-primary/40"
                        : "hover:bg-surface-2"
                    }`}
                  >
                    <div className={`text-sm font-medium ${typeTone(c.type)}`}>
                      {c.title}
                    </div>
                    <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                      <span>{c.type}</span>
                      {c.layer && (
                        <span
                          className={`rounded border px-1 py-px font-mono uppercase ${layerTone(c.layer)}`}
                        >
                          {c.layer}
                        </span>
                      )}
                    </div>
                  </button>
                ))}
                {filtered.length === 0 && (
                  <p className="px-2 py-4 text-sm text-muted">No matches.</p>
                )}
              </div>
            </aside>

            <main className="panel min-h-[28rem] p-5">
              {selected ? (
                <article className="space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-muted">
                        {selected.type}
                      </p>
                      <h3 className="text-2xl font-semibold tracking-tight">
                        {selected.title}
                      </h3>
                    </div>
                    {selected.layer && (
                      <span
                        className={`rounded-full border px-2.5 py-1 font-mono text-xs uppercase ${layerTone(selected.layer)}`}
                      >
                        {selected.layer}
                      </span>
                    )}
                  </div>
                  <p className="text-sm leading-relaxed text-muted">
                    {selected.description || "No description."}
                  </p>
                  <p className="font-mono text-xs text-muted">/{selected.path}</p>
                  {selected.tags?.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {selected.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[11px] text-muted"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                  {selected.links?.length > 0 && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                        Typed edges
                      </h4>
                      <ul className="space-y-1.5 text-sm">
                        {selected.links.map((l, i) => (
                          <li
                            key={`${l.target}-${l.rel}-${i}`}
                            className="flex flex-wrap items-center gap-2 rounded-md border border-border/70 bg-bg px-2.5 py-1.5"
                          >
                            <span className="font-mono text-xs text-primary">
                              {l.rel}
                            </span>
                            <span className="text-muted">→</span>
                            <span className="font-mono text-xs">{l.target}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                  {selected.excerpt && (
                    <div>
                      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted">
                        Excerpt
                      </h4>
                      <pre className="overflow-x-auto rounded-md border border-border bg-bg p-3 font-mono text-xs leading-relaxed text-muted">
                        {selected.excerpt}
                      </pre>
                    </div>
                  )}
                </article>
              ) : (
                <p className="text-sm text-muted">Select a concept.</p>
              )}
            </main>

            <aside className="space-y-3">
              <div className="panel p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Boxes className="h-4 w-4 text-primary" />
                  Stack
                </div>
                <ul className="space-y-2 text-sm text-muted">
                  <li>
                    <span className="text-fg">OKF</span> — graph format + impact
                  </li>
                  <li>
                    <span className="text-fg">PKC</span> — meetings / decisions
                  </li>
                  <li>
                    <span className="text-fg">DEKC</span> — data assets + lineage
                  </li>
                </ul>
              </div>
              <div className="panel p-4">
                <div className="mb-2 flex items-center gap-2 text-sm font-medium">
                  <Workflow className="h-4 w-4 text-accent" />
                  Medallion
                </div>
                <div className="flex flex-col gap-2">
                  {["bronze", "silver", "gold"].map((layer, i) => (
                    <div key={layer} className="flex items-center gap-2">
                      <span
                        className={`rounded border px-2 py-1 font-mono text-xs uppercase ${layerTone(layer)}`}
                      >
                        {layer}
                      </span>
                      <span className="text-xs text-muted">
                        {
                          data.concepts.filter(
                            (c) =>
                              (c.layer || "").toLowerCase() === layer &&
                              (c.type === "Table" || c.type === "View"),
                          ).length
                        }{" "}
                        tables/views
                      </span>
                      {i < 2 && (
                        <span className="ml-auto font-mono text-xs text-muted">
                          →
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
              <div className="panel p-4">
                <p className="text-xs leading-relaxed text-muted">
                  Try the plugin:{" "}
                  <code className="text-fg">/dekc-walk</code>,{" "}
                  <code className="text-fg">/dekc-business-object</code>,{" "}
                  <code className="text-fg">/dekc-lineage</code>,{" "}
                  <code className="text-fg">/dekc-index</code>
                </p>
              </div>
            </aside>
          </div>
        )}

        {data && tab === "lineage" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-5">
              <h3 className="mb-3 text-lg font-semibold">Lineage edges</h3>
              {lineageEdges.length === 0 ? (
                <p className="text-sm text-muted">
                  No graph edges yet — capture lineage paths or walk SQL models.
                </p>
              ) : (
                <ul className="space-y-2">
                  {lineageEdges.map((e) => (
                    <li
                      key={`${e.from}->${e.to}`}
                      className="flex flex-wrap items-center gap-2 rounded-md border border-border bg-bg px-3 py-2 font-mono text-xs"
                    >
                      <span className="text-fg">{basename(e.from)}</span>
                      <span className="text-primary">feeds</span>
                      <span className="text-fg">{basename(e.to)}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="panel p-5">
              <h3 className="mb-3 text-lg font-semibold">Mermaid</h3>
              <pre className="overflow-x-auto rounded-md border border-border bg-bg p-3 font-mono text-xs leading-relaxed text-muted">
                {data.mermaid || "flowchart LR\n  empty[No edges]"}
              </pre>
              <p className="mt-3 text-xs text-muted">
                Lineage paths and transformations in the sample retail lake:
                bronze orders → silver orders → gold daily revenue.
              </p>
            </div>
          </div>
        )}

        {data && tab === "glossary" && (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {glossary.map((c) => (
              <button
                key={c.path}
                type="button"
                onClick={() => {
                  setSelected(c);
                  setTab("catalog");
                }}
                className="panel p-4 text-left transition hover:border-primary/40"
              >
                <p className="font-mono text-[10px] uppercase tracking-[0.12em] text-primary">
                  {c.type}
                </p>
                <h3 className="mt-1 text-base font-semibold">{c.title}</h3>
                <p className="mt-2 line-clamp-4 text-sm text-muted">
                  {c.description}
                </p>
              </button>
            ))}
          </div>
        )}

        {data && tab === "agents" && (
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-5">
              <h3 className="mb-3 text-lg font-semibold">Orchestrator + subagents</h3>
              <ul className="space-y-3 text-sm">
                {[
                  ["data-lake-walker", "Orchestrates full lake walks and indexing"],
                  ["schema-scout", "Schemas, tables, columns, contracts"],
                  ["lineage-tracer", "SQL/DAX/pipeline lineage + promotions"],
                  ["semantic-mapper", "Business objects + glossary + metrics"],
                  ["report-cataloger", "Dashboards, reports, BI bindings"],
                  ["layer-auditor", "Medallion health + orphan detection"],
                ].map(([name, desc]) => (
                  <li
                    key={name}
                    className="rounded-md border border-border bg-bg px-3 py-2"
                  >
                    <div className="font-mono text-xs text-accent">{name}</div>
                    <div className="text-muted">{desc}</div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="panel p-5">
              <h3 className="mb-3 text-lg font-semibold">Walk receipts</h3>
              {agents.length === 0 ? (
                <p className="text-sm text-muted">No agent receipts in the sample yet.</p>
              ) : (
                <ul className="space-y-2">
                  {agents.map((a) => (
                    <li
                      key={a.path}
                      className="rounded-md border border-border bg-bg px-3 py-2"
                    >
                      <div className="font-medium">{a.title}</div>
                      <div className="text-sm text-muted">{a.description}</div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </div>

      <footer className="border-t border-border py-8 text-center text-xs text-muted">
        Spillwave Solutions · depends on{" "}
        <span className="text-fg">project-knowledge-capture</span> +{" "}
        <span className="text-fg">okf-graph-eng</span>
      </footer>
    </div>
  );
}

function Stat({
  icon,
  label,
  value,
}: {
  icon: ReactNode;
  label: string;
  value: string | number;
}) {
  return (
    <div className="panel p-4">
      <div className="mb-2 flex items-center gap-2 text-xs text-muted">
        {icon}
        {label}
      </div>
      <div className="text-2xl font-semibold tracking-tight">{value}</div>
    </div>
  );
}

function basename(path: string): string {
  return path.split("/").pop()?.replace(/\.md$/, "") || path;
}
