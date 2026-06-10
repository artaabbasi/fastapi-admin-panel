import { useState } from "react";
import { Database, GitMerge, Layers, Search, Table2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import type { ModelSchema } from "@/types";

interface DashboardProps {
  models: ModelSchema[];
  onSelect: (name: string) => void;
}

export function Dashboard({ models, onSelect }: DashboardProps) {
  const [search, setSearch] = useState("");

  const filtered = search.trim()
    ? models.filter((m) =>
        m.name.toLowerCase().includes(search.toLowerCase()) ||
        m.table_name.toLowerCase().includes(search.toLowerCase())
      )
    : models;

  const totalFields = models.reduce((sum, m) => sum + m.fields.length, 0);
  const totalRelations = models.reduce(
    (sum, m) => sum + m.fields.filter((f) => f.foreign_key).length,
    0
  );

  return (
    <div className="p-8 max-w-5xl">
      {/* Header */}
      <div className="mb-7">
        <h1 className="text-2xl font-bold tracking-tight mb-1">Dashboard</h1>
        <p className="text-muted-foreground text-sm">
          {models.length} model{models.length !== 1 ? "s" : ""} discovered from your SQLAlchemy project.
        </p>
      </div>

      {/* Stat cards */}
      {models.length > 0 && (
        <div className="grid grid-cols-3 gap-4 mb-8">
          <StatCard
            icon={Layers}
            label="Tables"
            value={models.length}
            color="text-primary"
            bg="bg-primary/10"
          />
          <StatCard
            icon={Database}
            label="Total Fields"
            value={totalFields}
            color="text-sky-400"
            bg="bg-sky-400/10"
          />
          <StatCard
            icon={GitMerge}
            label="Relationships"
            value={totalRelations}
            color="text-violet-400"
            bg="bg-violet-400/10"
          />
        </div>
      )}

      {/* Search */}
      {models.length > 0 && (
        <div className="relative mb-6">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            className="pl-9 max-w-sm"
            placeholder="Search models…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search models"
          />
        </div>
      )}

      {filtered.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((m) => (
            <ModelCard key={m.name} model={m} onSelect={onSelect} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-24 text-muted-foreground">
          <Database className="h-10 w-10 mb-4 opacity-25" />
          <p className="text-sm font-medium">
            {search ? `No models match "${search}"` : "No models discovered."}
          </p>
          {search && (
            <p className="text-xs mt-1 opacity-70">Try a different search term</p>
          )}
        </div>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  bg,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
  color: string;
  bg: string;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <div className={`p-2 rounded-lg ${bg}`}>
          <Icon className={`h-4 w-4 ${color}`} />
        </div>
      </div>
      <p className={`text-3xl font-bold tabular-nums ${color}`}>{value}</p>
    </div>
  );
}

function ModelCard({
  model,
  onSelect,
}: {
  model: ModelSchema;
  onSelect: (name: string) => void;
}) {
  const fkCount = model.fields.filter((f) => f.foreign_key).length;

  return (
    <button
      onClick={() => onSelect(model.name)}
      className="group text-left bg-card border border-border rounded-xl p-5 hover:border-primary/40 hover:bg-primary/[0.04] transition-all duration-200 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-background"
    >
      <div className="flex items-start justify-between mb-3.5">
        <div className="p-2 bg-primary/10 rounded-lg ring-1 ring-primary/15 group-hover:bg-primary/15 transition-colors">
          <Table2 className="h-4 w-4 text-primary" />
        </div>
        <span className="text-[11px] text-muted-foreground font-mono bg-muted/60 px-2 py-0.5 rounded-md border border-border/60">
          {model.table_name}
        </span>
      </div>
      <h2 className="font-semibold text-sm mb-1.5 group-hover:text-primary transition-colors">
        {model.name}
      </h2>
      <p className="text-xs text-muted-foreground flex items-center gap-2">
        <span>{model.fields.length} field{model.fields.length !== 1 ? "s" : ""}</span>
        {fkCount > 0 && (
          <>
            <span className="opacity-40">·</span>
            <span>{fkCount} FK{fkCount !== 1 ? "s" : ""}</span>
          </>
        )}
        <span className="opacity-40">·</span>
        <span className="font-mono">PK: {model.pk_field}</span>
      </p>
    </button>
  );
}
