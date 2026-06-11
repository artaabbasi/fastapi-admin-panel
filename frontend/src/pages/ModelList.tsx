import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronLeft, ChevronRight, Pencil, Plus, Trash2, X } from "lucide-react";
import { api } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import type { FieldSchema, ListParams, ModelSchema } from "@/types";
import { ModelForm } from "./ModelForm";

interface ModelListProps {
  schema: ModelSchema;
  allowDelete?: boolean;
  pageSize?: number;
}

const SEARCHABLE_TYPES = new Set([
  "string", "text", "integer", "float", "uuid", "date", "datetime", "time",
]);

function CellValue({ value, field }: { value: unknown; field: FieldSchema }) {
  if (value == null)
    return <span className="text-muted-foreground/60 italic text-xs">null</span>;
  if (field.field_type === "boolean")
    return (
      <Badge
        variant={value ? "default" : "secondary"}
        className="font-mono text-[11px] px-1.5 py-0"
      >
        {value ? "true" : "false"}
      </Badge>
    );
  const str = String(value);
  if (str.length > 60)
    return (
      <span title={str} className="cursor-help">
        {str.slice(0, 60)}…
      </span>
    );
  return <span>{str}</span>;
}

function SortIcon({ field, orderBy, orderDir }: { field: string; orderBy?: string; orderDir: "asc" | "desc" }) {
  if (orderBy !== field) return <ArrowUpDown className="h-3 w-3 opacity-25" />;
  return orderDir === "asc"
    ? <ArrowUp className="h-3 w-3 text-primary" />
    : <ArrowDown className="h-3 w-3 text-primary" />;
}

export function ModelList({ schema, allowDelete = true, pageSize = 50 }: ModelListProps) {
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [total, setTotal] = useState(0);
  const [skip, setSkip] = useState(0);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [searchField, setSearchField] = useState("__all__");
  const [orderBy, setOrderBy] = useState<string | undefined>();
  const [orderDir, setOrderDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<Set<unknown>>(new Set());
  const [deleting, setDeleting] = useState(false);
  const [formOpen, setFormOpen] = useState(false);
  const [editRecord, setEditRecord] = useState<Record<string, unknown> | null>(null);

  const tableRef = useRef<HTMLDivElement>(null);

  const visibleFields = schema.fields.slice(0, 8);
  const searchableFields = schema.fields.filter((f) => SEARCHABLE_TYPES.has(f.field_type));

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setSelected(new Set());
    const params: ListParams = { skip, limit: pageSize, order_dir: orderDir };
    if (search) {
      params.search = search;
      if (searchField !== "__all__") params.search_field = searchField;
    }
    if (orderBy) params.order_by = orderBy;
    try {
      const res = await api.list(schema.name, params);
      setRows(res.data);
      setTotal(res.total);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [schema.name, skip, search, searchField, orderBy, orderDir, pageSize]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    tableRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [skip, search]);

  function applySearch() { setSearch(searchInput); setSkip(0); }
  function clearSearch() { setSearch(""); setSearchInput(""); setSkip(0); }

  function toggleSort(col: string) {
    if (orderBy === col) setOrderDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setOrderBy(col); setOrderDir("asc"); }
    setSkip(0);
  }

  async function handleDelete(pk: unknown) {
    if (!confirm("Delete this record?")) return;
    try {
      await api.delete(schema.name, pk as string);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  function toggleRow(pk: unknown) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(pk)) next.delete(pk);
      else next.add(pk);
      return next;
    });
  }

  function toggleAll() {
    setSelected(
      selected.size === rows.length
        ? new Set()
        : new Set(rows.map((r) => r[schema.pk_field]))
    );
  }

  async function deleteSelected() {
    if (!confirm(`Delete ${selected.size} selected record${selected.size !== 1 ? "s" : ""}?`)) return;
    setDeleting(true);
    try {
      await Promise.all([...selected].map((pk) => api.delete(schema.name, pk as string)));
      setSelected(new Set());
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Bulk delete failed");
    } finally {
      setDeleting(false);
    }
  }

  function openCreate() { setEditRecord(null); setFormOpen(true); }
  function openEdit(row: Record<string, unknown>) { setEditRecord(row); setFormOpen(true); }

  const pages = Math.ceil(total / pageSize);
  const page = Math.floor(skip / pageSize) + 1;
  const allChecked = rows.length > 0 && selected.size === rows.length;
  const someChecked = selected.size > 0 && selected.size < rows.length;
  const colSpan = visibleFields.length + (allowDelete ? 2 : 1);

  return (
    <div className="p-6 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-start justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold tracking-tight">{schema.name}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            <span className="tabular-nums">{total}</span> record{total !== 1 ? "s" : ""}
            {" · "}table{" "}
            <code className="font-mono bg-muted/60 px-1.5 py-0.5 rounded text-[11px] border border-border/50">
              {schema.table_name}
            </code>
          </p>
        </div>
        <div className="flex items-center gap-2">
          {allowDelete && selected.size > 0 && (
            <Button size="sm" variant="destructive" onClick={deleteSelected} disabled={deleting}>
              <Trash2 className="h-3.5 w-3.5" />
              Delete {selected.size}
            </Button>
          )}
          <Button size="sm" onClick={openCreate}>
            <Plus className="h-3.5 w-3.5" />
            Add {schema.name}
          </Button>
        </div>
      </div>

      {/* Search toolbar */}
      <div className="flex gap-2 mb-4">
        <select
          className="h-9 rounded-md border border-input bg-card px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring shrink-0 cursor-pointer"
          value={searchField}
          onChange={(e) => {
            setSearchField(e.target.value);
            setSearch("");
            setSearchInput("");
            setSkip(0);
          }}
        >
          <option value="__all__">All text fields</option>
          {searchableFields.map((f) => (
            <option key={f.name} value={f.name}>
              {f.name} ({f.field_type})
            </option>
          ))}
        </select>

        <div className="relative flex-1">
          <Input
            className="pr-8"
            placeholder={searchField === "__all__" ? `Search ${schema.name}…` : `Search by ${searchField}…`}
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") applySearch(); }}
          />
          {searchInput && (
            <button
              type="button"
              className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
              onClick={clearSearch}
              aria-label="Clear search"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <Button variant="secondary" size="sm" className="h-9 px-4 shrink-0" onClick={applySearch}>
          Search
        </Button>
      </div>

      {/* Active search note */}
      {search && (
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs text-muted-foreground">
            {total} result{total !== 1 ? "s" : ""} for{" "}
            <strong className="text-foreground">"{search}"</strong>
            {searchField !== "__all__" && (
              <> in <code className="font-mono text-[11px]">{searchField}</code></>
            )}
          </span>
          <button
            className="text-xs text-muted-foreground hover:text-foreground underline underline-offset-2 transition-colors cursor-pointer"
            onClick={clearSearch}
          >
            Clear
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive flex items-start gap-2">
          <span className="mt-px shrink-0">⚠</span>
          <span>{error}</span>
        </div>
      )}

      {/* Table */}
      <div ref={tableRef} className="flex-1 overflow-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10">
            <tr className="bg-muted/90 backdrop-blur-sm border-b border-border">
              {allowDelete && (
                <th className="px-4 py-3 w-10">
                  <Checkbox
                    checked={allChecked}
                    indeterminate={someChecked}
                    onCheckedChange={toggleAll}
                    aria-label="Select all"
                  />
                </th>
              )}
              {visibleFields.map((f) => (
                <th
                  key={f.name}
                  className="px-4 py-3 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap cursor-pointer hover:text-foreground select-none transition-colors"
                  onClick={() => toggleSort(f.name)}
                >
                  <span className="flex items-center gap-1.5">
                    {f.name}
                    <SortIcon field={f.name} orderBy={orderBy} orderDir={orderDir} />
                  </span>
                </th>
              ))}
              <th className="px-4 py-3 text-right text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {loading &&
              Array.from({ length: Math.min(pageSize, 8) }).map((_, i) => (
                <tr key={i}>
                  {allowDelete && (
                    <td className="px-4 py-3 w-10">
                      <Skeleton className="h-4 w-4" />
                    </td>
                  )}
                  {visibleFields.map((f) => (
                    <td key={f.name} className="px-4 py-3">
                      <Skeleton className={`h-4 ${i % 3 === 0 ? "w-24" : i % 3 === 1 ? "w-32" : "w-20"}`} />
                    </td>
                  ))}
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Skeleton className="h-7 w-7 rounded-md" />
                      {allowDelete && <Skeleton className="h-7 w-7 rounded-md" />}
                    </div>
                  </td>
                </tr>
              ))}

            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={colSpan} className="px-4 py-16 text-center">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <div className="h-10 w-10 rounded-full bg-muted/60 flex items-center justify-center">
                      <Trash2 className="h-4 w-4 opacity-40" />
                    </div>
                    <p className="text-sm font-medium">No records found</p>
                    {search && <p className="text-xs opacity-70">Try a different search term</p>}
                  </div>
                </td>
              </tr>
            )}

            {!loading &&
              rows.map((row, i) => {
                const pk = row[schema.pk_field];
                const isChecked = selected.has(pk);
                return (
                  <tr
                    key={i}
                    className={`group transition-colors ${
                      isChecked
                        ? "bg-primary/5 hover:bg-primary/8"
                        : "hover:bg-accent/30"
                    }`}
                  >
                    {allowDelete && (
                      <td className="px-4 py-3 w-10">
                        <Checkbox
                          checked={isChecked}
                          onCheckedChange={() => toggleRow(pk)}
                          aria-label={`Select row ${i + 1}`}
                        />
                      </td>
                    )}
                    {visibleFields.map((f) => (
                      <td key={f.name} className="px-4 py-3 max-w-[200px] truncate font-mono text-xs">
                        <CellValue value={row[f.name]} field={f} />
                      </td>
                    ))}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="icon"
                          variant="ghost"
                          className="h-7 w-7 cursor-pointer text-muted-foreground hover:text-foreground hover:bg-accent"
                          title="Edit record"
                          onClick={() => openEdit(row)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </Button>
                        {allowDelete && (
                          <Button
                            size="icon"
                            variant="ghost"
                            className="h-7 w-7 cursor-pointer text-muted-foreground hover:text-destructive hover:bg-destructive/10"
                            title="Delete record"
                            onClick={() => handleDelete(pk)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {total > pageSize && (
        <div className="flex items-center justify-between mt-4 text-sm">
          <span className="text-xs text-muted-foreground tabular-nums">
            {skip + 1}–{Math.min(skip + pageSize, total)} of {total}
            {pages > 1 && <span className="ml-1 opacity-60">· Page {page}/{pages}</span>}
          </span>
          <div className="flex items-center gap-1">
            <Button
              size="icon"
              variant="outline"
              className="h-8 w-8 cursor-pointer"
              disabled={skip === 0}
              onClick={() => setSkip(0)}
              title="First page"
            >
              <ChevronLeft className="h-4 w-4 -mr-1" />
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              variant="outline"
              className="h-8 w-8 cursor-pointer"
              disabled={skip === 0}
              onClick={() => setSkip(Math.max(0, skip - pageSize))}
              title="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>

            {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
              const p =
                pages <= 7
                  ? i + 1
                  : page <= 4
                  ? i + 1
                  : page >= pages - 3
                  ? pages - 6 + i
                  : page - 3 + i;
              if (p < 1 || p > pages) return null;
              return (
                <Button
                  key={p}
                  size="icon"
                  variant={p === page ? "default" : "outline"}
                  className="h-8 w-8 text-xs cursor-pointer"
                  onClick={() => setSkip((p - 1) * pageSize)}
                >
                  {p}
                </Button>
              );
            })}

            <Button
              size="icon"
              variant="outline"
              className="h-8 w-8 cursor-pointer"
              disabled={skip + pageSize >= total}
              onClick={() => setSkip(skip + pageSize)}
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
            <Button
              size="icon"
              variant="outline"
              className="h-8 w-8 cursor-pointer"
              disabled={skip + pageSize >= total}
              onClick={() => setSkip((pages - 1) * pageSize)}
              title="Last page"
            >
              <ChevronRight className="h-4 w-4 -mr-1" />
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {formOpen && (
        <ModelForm
          schema={schema}
          record={editRecord}
          onClose={() => setFormOpen(false)}
          onSaved={() => { setFormOpen(false); load(); }}
        />
      )}
    </div>
  );
}
