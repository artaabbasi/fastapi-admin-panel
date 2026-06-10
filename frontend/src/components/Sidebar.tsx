import { Database, LayoutDashboard, Search, Table2, Users } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import type { ModelSchema } from "@/types";

interface SidebarProps {
  models: ModelSchema[];
  activeModel: string | null;
  onSelect: (name: string | null) => void;
  title?: string;
}

const SYSTEM_ITEMS = [
  { key: "__system_users__", label: "Admin Users", icon: Users },
];

function NavItem({
  active,
  onClick,
  icon: Icon,
  label,
  title,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ElementType;
  label: string;
  title?: string;
}) {
  return (
    <button
      onClick={onClick}
      title={title}
      className={cn(
        "w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-all duration-150 cursor-pointer",
        active
          ? "bg-primary/10 text-primary font-medium"
          : "text-muted-foreground hover:bg-accent/60 hover:text-foreground"
      )}
      style={active ? { boxShadow: "inset 2px 0 0 hsl(var(--primary))" } : undefined}
    >
      <Icon className="h-4 w-4 shrink-0" />
      <span className="truncate">{label}</span>
    </button>
  );
}

export function Sidebar({ models, activeModel, onSelect, title = "Admin Panel" }: SidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = search.trim()
    ? models.filter((m) => m.name.toLowerCase().includes(search.toLowerCase()))
    : models;

  const isSystem = SYSTEM_ITEMS.some((i) => i.key === activeModel);

  return (
    <aside className="w-60 h-screen sticky top-0 bg-card border-r border-border flex flex-col shrink-0">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 h-14 border-b border-border shrink-0">
        <div className="p-1.5 rounded-md bg-primary/15 ring-1 ring-primary/20">
          <Database className="h-4 w-4 text-primary" />
        </div>
        <span className="font-semibold text-sm tracking-tight truncate">{title}</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 px-3 space-y-0.5">
        <NavItem
          active={activeModel === null && !isSystem}
          onClick={() => onSelect(null)}
          icon={LayoutDashboard}
          label="Dashboard"
        />

        {models.length > 0 && (
          <>
            <div className="pt-4 pb-1.5 px-3">
              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
                Tables
              </p>
            </div>

            <div className="relative mb-2">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <input
                className="w-full bg-muted/60 border border-border rounded-md text-sm pl-8 pr-3 py-1.5 placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring transition-colors"
                placeholder="Filter tables…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                aria-label="Filter tables"
              />
            </div>

            {filtered.length === 0 ? (
              <p className="px-3 py-2 text-xs text-muted-foreground">No match</p>
            ) : (
              filtered.map((m) => (
                <NavItem
                  key={m.name}
                  active={activeModel === m.name}
                  onClick={() => onSelect(m.name)}
                  icon={Table2}
                  label={m.name}
                  title={m.name}
                />
              ))
            )}
          </>
        )}

        <div className="pt-4 pb-1.5 px-3">
          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest">
            System
          </p>
        </div>

        {SYSTEM_ITEMS.map(({ key, label, icon }) => (
          <NavItem
            key={key}
            active={activeModel === key}
            onClick={() => onSelect(key)}
            icon={icon}
            label={label}
          />
        ))}
      </nav>

      {/* Footer */}
      <div className="px-5 py-3.5 border-t border-border shrink-0">
        <p className="text-xs text-muted-foreground tabular-nums">
          {models.length} table{models.length !== 1 ? "s" : ""}
        </p>
      </div>
    </aside>
  );
}
