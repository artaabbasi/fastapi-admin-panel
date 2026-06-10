import type { ListParams, ListResponse, ModelSchema } from "@/types";

const BASE = "/admin/api";
const TOKEN_KEY = "admin_token";

// ── Token storage ─────────────────────────────────────────────────────────────

export const tokenStorage = {
  get: (): string | null => localStorage.getItem(TOKEN_KEY),
  set: (token: string) => localStorage.setItem(TOKEN_KEY, token),
  clear: () => localStorage.removeItem(TOKEN_KEY),
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────

async function req<T>(url: string, init?: RequestInit): Promise<T> {
  const token = tokenStorage.get();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string>),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(url, { ...init, headers });

  if (res.status === 401) {
    tokenStorage.clear();
    window.location.reload();
    throw new Error("Session expired");
  }

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${text}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  login: async (username: string, password: string): Promise<string> => {
    const data = await req<{ access_token: string; username: string }>(
      `${BASE}/auth/login`,
      { method: "POST", body: JSON.stringify({ username, password }) }
    );
    tokenStorage.set(data.access_token);
    return data.username;
  },

  logout: async () => {
    try { await req(`${BASE}/auth/logout`, { method: "POST" }); } catch {}
    tokenStorage.clear();
  },

  me: (): Promise<{ id: string; username: string }> => req(`${BASE}/auth/me`),
};

// ── Admin config ──────────────────────────────────────────────────────────────

export const adminConfig = (): Promise<{
  title: string;
  prefix: string;
  allow_delete: boolean;
  page_size: number;
}> => req(`${BASE}/config`);

// ── Models + CRUD ─────────────────────────────────────────────────────────────

// ── System (admin user management) ───────────────────────────────────────────

export interface AdminUser {
  id: number;
  username: string;
  is_active: boolean;
  created_at: string | null;
}

export const system = {
  listUsers: (): Promise<AdminUser[]> => req(`${BASE}/system/users`),

  createUser: (username: string, password: string, is_active = true): Promise<AdminUser> =>
    req(`${BASE}/system/users`, {
      method: "POST",
      body: JSON.stringify({ username, password, is_active }),
    }),

  updateUser: (id: number, data: Partial<{ username: string; is_active: boolean }>): Promise<AdminUser> =>
    req(`${BASE}/system/users/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  changePassword: (id: number, new_password: string): Promise<void> =>
    req(`${BASE}/system/users/${id}/password`, {
      method: "POST",
      body: JSON.stringify({ new_password }),
    }),

  deleteUser: (id: number): Promise<void> =>
    req(`${BASE}/system/users/${id}`, { method: "DELETE" }),
};

export const api = {
  models: (): Promise<ModelSchema[]> => req(`${BASE}/models`),

  list: (model: string, params: ListParams = {}): Promise<ListResponse> => {
    const q = new URLSearchParams();
    if (params.skip != null) q.set("skip", String(params.skip));
    if (params.limit != null) q.set("limit", String(params.limit));
    if (params.search) q.set("search", params.search);
    if (params.search_field) q.set("search_field", params.search_field);
    if (params.order_by) q.set("order_by", params.order_by);
    if (params.order_dir) q.set("order_dir", params.order_dir);
    return req(`${BASE}/${model.toLowerCase()}/?${q}`);
  },

  get: (model: string, pk: string | number): Promise<Record<string, unknown>> =>
    req(`${BASE}/${model.toLowerCase()}/${pk}`),

  create: (model: string, data: Record<string, unknown>): Promise<Record<string, unknown>> =>
    req(`${BASE}/${model.toLowerCase()}/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (
    model: string,
    pk: string | number,
    data: Record<string, unknown>
  ): Promise<Record<string, unknown>> =>
    req(`${BASE}/${model.toLowerCase()}/${pk}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  delete: (model: string, pk: string | number): Promise<void> =>
    req(`${BASE}/${model.toLowerCase()}/${pk}`, { method: "DELETE" }),
};
