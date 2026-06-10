import { useState } from "react";
import { api } from "@/api/client";
import { FieldInput } from "@/components/FieldInput";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import type { ModelSchema } from "@/types";

interface ModelFormProps {
  schema: ModelSchema;
  record: Record<string, unknown> | null;
  onClose: () => void;
  onSaved: () => void;
}

export function ModelForm({ schema, record, onClose, onSaved }: ModelFormProps) {
  const isEdit = record != null;

  // initialise form values (skip auto-PK on create)
  const initial: Record<string, unknown> = {};
  for (const f of schema.fields) {
    if (!isEdit && f.primary_key) continue;
    initial[f.name] = isEdit ? record[f.name] : (f.default ?? null);
  }

  const [values, setValues] = useState<Record<string, unknown>>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(name: string, value: unknown) {
    setValues((prev) => ({ ...prev, [name]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (isEdit) {
        const pk = record[schema.pk_field] as string;
        await api.update(schema.name, pk, values);
      } else {
        await api.create(schema.name, values);
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  const editableFields = schema.fields.filter(
    (f) => !(f.primary_key && !isEdit)
  );

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {isEdit ? `Edit ${schema.name}` : `Create ${schema.name}`}
          </DialogTitle>
          <DialogDescription>
            {isEdit
              ? `Update fields and click "Save changes".`
              : `Fill in the fields below and click "Create".`}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4 py-2">
          {editableFields.map((f) => (
            <div key={f.name} className="space-y-1.5">
              <label className="text-sm font-medium flex items-center gap-1.5 flex-wrap">
                {f.name}
                {f.primary_key && (
                  <span className="text-[10px] font-mono text-primary/80 bg-primary/10 border border-primary/20 rounded px-1.5 py-0.5">
                    PK
                  </span>
                )}
                {f.foreign_key && (
                  <span className="text-[10px] font-mono text-violet-400/80 bg-violet-400/10 border border-violet-400/20 rounded px-1.5 py-0.5">
                    FK → {f.foreign_key}
                  </span>
                )}
                {!f.nullable && !f.primary_key && (
                  <span className="text-destructive text-xs" title="Required">*</span>
                )}
              </label>
              <FieldInput
                field={f}
                value={values[f.name]}
                onChange={(v) => set(f.name, v)}
                disabled={f.primary_key && isEdit}
              />
              <p className="text-[11px] text-muted-foreground/60 font-mono">{f.field_type}</p>
            </div>
          ))}

          {error && (
            <div
              role="alert"
              className="px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive flex items-start gap-2"
            >
              <span className="mt-px shrink-0">⚠</span>
              <span>{error}</span>
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving…" : isEdit ? "Save changes" : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
