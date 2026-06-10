/**
 * Renders the correct input widget for a given field type.
 */
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import type { FieldSchema } from "@/types";

interface FieldInputProps {
  field: FieldSchema;
  value: unknown;
  onChange: (value: unknown) => void;
  disabled?: boolean;
}

/**
 * Normalise an API value to what an HTML input expects.
 * The API returns ISO strings; inputs need specific truncated formats.
 */
function toInputValue(field: FieldSchema, value: unknown): string {
  if (value == null) return "";
  const str = String(value);

  if (field.field_type === "datetime") {
    // API returns "2024-01-15T10:30:00.123456+03:30" or "...Z"
    // datetime-local expects  "2024-01-15T10:30" or "2024-01-15T10:30:00"
    return str
      .replace(/\.\d+/, "")          // strip microseconds
      .replace(/[Zz]$/, "")          // strip Z
      .replace(/[+-]\d{2}:?\d{2}$/, "") // strip timezone offset
      .slice(0, 16);                  // "YYYY-MM-DDTHH:mm"
  }

  if (field.field_type === "date") {
    // "2024-01-15T..." → "2024-01-15"
    return str.slice(0, 10);
  }

  if (field.field_type === "time") {
    // "10:30:00.123" → "10:30"
    return str.replace(/\.\d+/, "").slice(0, 5);
  }

  if (field.field_type === "boolean") {
    // API returns true/false (bool) — stringify for <Select>
    return str;
  }

  return str;
}

export function FieldInput({ field, value, onChange, disabled }: FieldInputProps) {
  const str = toInputValue(field, value);

  // Radix Select forbids value="" — use sentinel for null
  const NULL_SENTINEL = "__null__";

  if (field.field_type === "boolean") {
    const selectVal = str === "" ? NULL_SENTINEL : str;
    return (
      <Select
        value={selectVal}
        onValueChange={(v) => onChange(v === NULL_SENTINEL ? null : v === "true")}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {field.nullable && <SelectItem value={NULL_SENTINEL}>— null —</SelectItem>}
          <SelectItem value="true">True</SelectItem>
          <SelectItem value="false">False</SelectItem>
        </SelectContent>
      </Select>
    );
  }

  if (field.field_type === "enum" && field.choices.length > 0) {
    const selectVal = str === "" ? NULL_SENTINEL : str;
    return (
      <Select
        value={selectVal}
        onValueChange={(v) => onChange(v === NULL_SENTINEL ? null : v)}
        disabled={disabled}
      >
        <SelectTrigger>
          <SelectValue placeholder="Select…" />
        </SelectTrigger>
        <SelectContent>
          {field.nullable && <SelectItem value={NULL_SENTINEL}>— null —</SelectItem>}
          {field.choices.map((c) => (
            <SelectItem key={c} value={c}>{c}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (field.field_type === "text") {
    return (
      <textarea
        className="flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        value={str}
        onChange={(e) => onChange(e.target.value || null)}
        disabled={disabled}
      />
    );
  }

  if (field.field_type === "json") {
    return (
      <textarea
        className="flex min-h-[100px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
        value={str}
        onChange={(e) => {
          try { onChange(JSON.parse(e.target.value)); }
          catch { onChange(e.target.value); }
        }}
        disabled={disabled}
        placeholder="{}"
      />
    );
  }

  const inputType: Record<string, string> = {
    integer: "number",
    float:   "number",
    date:    "date",
    datetime: "datetime-local",
    time:    "time",
  };

  return (
    <Input
      type={inputType[field.field_type] ?? "text"}
      value={str}
      onChange={(e) => {
        const raw = e.target.value;
        if (field.field_type === "integer")
          onChange(raw === "" ? null : parseInt(raw, 10));
        else if (field.field_type === "float")
          onChange(raw === "" ? null : parseFloat(raw));
        else
          onChange(raw === "" ? null : raw);
      }}
      disabled={disabled}
      placeholder={field.nullable ? "null" : ""}
      maxLength={field.max_length ?? undefined}
    />
  );
}
