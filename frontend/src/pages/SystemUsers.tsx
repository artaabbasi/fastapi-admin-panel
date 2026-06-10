import { useEffect, useState } from "react";
import { KeyRound, Pencil, Plus, ShieldCheck, ShieldOff, Trash2 } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import { system, type AdminUser } from "@/api/client";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

// ── Create/Edit User Dialog ────────────────────────────────────────────────────

interface UserFormProps {
  user: AdminUser | null;
  onClose: () => void;
  onSaved: () => void;
}

function UserForm({ user, onClose, onSaved }: UserFormProps) {
  const isEdit = user !== null;
  const [username, setUsername] = useState(user?.username ?? "");
  const [password, setPassword] = useState("");
  const [isActive, setIsActive] = useState(user?.is_active ?? true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      if (isEdit) {
        await system.updateUser(user.id, { username, is_active: isActive });
      } else {
        if (!password) throw new Error("Password is required");
        await system.createUser(username, password, isActive);
      }
      onSaved();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit User" : "Create Admin User"}</DialogTitle>
          <DialogDescription>
            {isEdit ? "Update username or active status." : "Add a new admin panel user."}
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4 py-2">
          <div className="space-y-1.5">
            <label className="text-sm font-medium">Username</label>
            <Input value={username} onChange={(e) => setUsername(e.target.value)} required />
          </div>
          {!isEdit && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium">Password</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
          )}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="h-4 w-4"
            />
            <label htmlFor="is_active" className="text-sm">Active</label>
          </div>
          {error && (
            <div role="alert" className="px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive flex items-start gap-2">
              <span className="mt-px shrink-0">⚠</span>
              <span>{error}</span>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving ? "Saving…" : isEdit ? "Save" : "Create"}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// ── Change Password Dialog ─────────────────────────────────────────────────────

interface ChangePasswordProps {
  user: AdminUser;
  onClose: () => void;
}

function ChangePasswordDialog({ user, onClose }: ChangePasswordProps) {
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await system.changePassword(user.id, password);
      setDone(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Change Password</DialogTitle>
          <DialogDescription>Set a new password for <strong>{user.username}</strong>.</DialogDescription>
        </DialogHeader>
        {done ? (
          <div className="py-4 text-sm text-center text-muted-foreground">
            Password updated successfully.
            <div className="mt-4">
              <Button onClick={onClose}>Close</Button>
            </div>
          </div>
        ) : (
          <form onSubmit={submit} className="space-y-4 py-2">
            <div className="space-y-1.5">
              <label className="text-sm font-medium">New Password</label>
              <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>
            {error && (
              <div role="alert" className="px-3 py-2.5 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive flex items-start gap-2">
                <span className="mt-px shrink-0">⚠</span>
                <span>{error}</span>
              </div>
            )}
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose} disabled={saving}>Cancel</Button>
              <Button type="submit" disabled={saving || !password}>{saving ? "Saving…" : "Update"}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function SystemUsers() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formUser, setFormUser] = useState<AdminUser | null | "create">(null);
  const [pwdUser, setPwdUser] = useState<AdminUser | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setUsers(await system.listUsers());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  async function toggleActive(user: AdminUser) {
    try {
      await system.updateUser(user.id, { is_active: !user.is_active });
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Failed");
    }
  }

  async function handleDelete(user: AdminUser) {
    if (!confirm(`Delete user "${user.username}"? This cannot be undone.`)) return;
    try {
      await system.deleteUser(user.id);
      load();
    } catch (e: unknown) {
      alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <div className="p-6 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold">Admin Users</h1>
          <p className="text-xs text-muted-foreground mt-0.5">
            Manage admin panel accounts
          </p>
        </div>
        <Button size="sm" onClick={() => setFormUser("create")}>
          <Plus className="h-4 w-4" />
          Add User
        </Button>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive flex items-start gap-2">
          <span className="mt-px shrink-0">⚠</span>
          <span>{error}</span>
        </div>
      )}

      <div className="rounded-lg border border-border overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-muted/90 border-b border-border">
              <th className="px-4 py-3 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">ID</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Username</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Status</th>
              <th className="px-4 py-3 text-left text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Created</th>
              <th className="px-4 py-3 text-right text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border/60">
            {loading && (
              Array.from({ length: 3 }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-8" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-24" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-5 w-14 rounded-md" /></td>
                  <td className="px-4 py-3"><Skeleton className="h-4 w-32" /></td>
                  <td className="px-4 py-3"><div className="flex justify-end gap-1"><Skeleton className="h-7 w-7 rounded-md" /><Skeleton className="h-7 w-7 rounded-md" /><Skeleton className="h-7 w-7 rounded-md" /></div></td>
                </tr>
              ))
            )}
            {!loading && users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-14 text-center">
                  <div className="flex flex-col items-center gap-2 text-muted-foreground">
                    <div className="h-10 w-10 rounded-full bg-muted/60 flex items-center justify-center">
                      <ShieldOff className="h-4 w-4 opacity-40" />
                    </div>
                    <p className="text-sm font-medium">No admin users found</p>
                  </div>
                </td>
              </tr>
            )}
            {!loading && users.map((user) => (
              <tr key={user.id} className="hover:bg-accent/30 transition-colors">
                <td className="px-4 py-3 text-muted-foreground font-mono text-xs tabular-nums">{user.id}</td>
                <td className="px-4 py-3 font-medium">{user.username}</td>
                <td className="px-4 py-3">
                  <Badge variant={user.is_active ? "default" : "secondary"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                </td>
                <td className="px-4 py-3 text-muted-foreground text-xs font-mono tabular-nums">
                  {user.created_at ? new Date(user.created_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-3 text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 cursor-pointer"
                      title={user.is_active ? "Deactivate user" : "Activate user"}
                      onClick={() => toggleActive(user)}
                    >
                      {user.is_active
                        ? <ShieldOff className="h-3.5 w-3.5 text-muted-foreground" />
                        : <ShieldCheck className="h-3.5 w-3.5 text-green-500" />}
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 cursor-pointer"
                      title="Change password"
                      onClick={() => setPwdUser(user)}
                    >
                      <KeyRound className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 cursor-pointer"
                      title="Edit user"
                      onClick={() => setFormUser(user)}
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      size="icon"
                      variant="ghost"
                      className="h-7 w-7 text-destructive/70 hover:text-destructive hover:bg-destructive/10 cursor-pointer"
                      title="Delete user"
                      onClick={() => handleDelete(user)}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Dialogs */}
      {formUser !== null && (
        <UserForm
          user={formUser === "create" ? null : formUser}
          onClose={() => setFormUser(null)}
          onSaved={() => { setFormUser(null); load(); }}
        />
      )}
      {pwdUser !== null && (
        <ChangePasswordDialog
          user={pwdUser}
          onClose={() => setPwdUser(null)}
        />
      )}
    </div>
  );
}
