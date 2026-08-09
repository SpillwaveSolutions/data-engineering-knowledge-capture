export type CatalogLink = {
  target?: string;
  rel?: string;
};

export type CatalogConcept = {
  path: string;
  type: string;
  title: string;
  description: string;
  layer?: string | null;
  tags: string[];
  links: CatalogLink[];
  status?: string;
  verified?: boolean;
  excerpt?: string;
};

export type CatalogPayload = {
  title: string;
  version: string;
  depends_on: string[];
  concepts: CatalogConcept[];
  graph: Record<string, string[]>;
  mermaid: string;
};

export const TYPE_LABELS: Record<string, string> = {
  Table: "Tables",
  View: "Views",
  Query: "Queries",
  Schema: "Schemas",
  Column: "Columns",
  Layer: "Layers",
  SourceSystem: "Sources",
  Transformation: "Transforms",
  LineagePath: "Lineage",
  Workflow: "Workflows",
  SemanticModel: "Semantic",
  Metric: "Metrics",
  Dashboard: "Dashboards",
  Report: "Reports",
  BusinessObject: "Business objects",
  GlossaryTerm: "Glossary",
  SqlArtifact: "SQL",
  DaxArtifact: "DAX",
  AgentNode: "Agents",
  ContextPack: "Packs",
};

export const PRIMARY_TYPES = [
  "Table",
  "View",
  "BusinessObject",
  "GlossaryTerm",
  "LineagePath",
  "Metric",
  "Dashboard",
  "SemanticModel",
  "Workflow",
  "Transformation",
  "Query",
  "Layer",
  "SourceSystem",
  "AgentNode",
] as const;

export function layerTone(layer?: string | null): string {
  switch ((layer || "").toLowerCase()) {
    case "bronze":
      return "text-bronze border-bronze/40 bg-bronze/10";
    case "silver":
      return "text-silver border-silver/40 bg-silver/10";
    case "gold":
      return "text-gold border-gold/40 bg-gold/10";
    default:
      return "text-muted border-border bg-surface-2";
  }
}

export function typeTone(type: string): string {
  if (type === "BusinessObject" || type === "GlossaryTerm") return "text-primary";
  if (type === "LineagePath" || type === "Transformation") return "text-accent";
  if (type === "Dashboard" || type === "Report" || type === "Metric")
    return "text-gold";
  return "text-fg";
}
