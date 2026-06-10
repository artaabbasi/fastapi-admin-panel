import { useEffect, useRef, useState } from "react";
import { LogOut, User } from "lucide-react";
import { adminConfig, api, auth, tokenStorage } from "@/api/client";
import { Sidebar } from "@/components/Sidebar";
import { Button } from "@/components/ui/button";
import { Dashboard } from "@/pages/Dashboard";
import { Login } from "@/pages/Login";
import { ModelList } from "@/pages/ModelList";
import { SystemUsers } from "@/pages/SystemUsers";
import type { ModelSchema } from "@/types";

interface PanelConfig {
  title: string;
  prefix: string;
  allow_delete: boolean;
  page_size: number;
}

export default function App() {
  const [authenticated, setAuthenticated] = useState(!!tokenStorage.get());
  const [currentUser, setCurrentUser] = useState<string | null>(null);
  const [config, setConfig] = useState<PanelConfig | null>(null);
  const [models, setModels] = useState<ModelSchema[]>([]);
  const [activeModel, setActiveModel] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mainRef = useRef<HTMLElement>(null);

  // Load config + models after authentication
  useEffect(() => {
    if (!authenticated) { setLoading(false); return; }

    setLoading(true);
    Promise.all([adminConfig(), api.models(), auth.me()])
      .then(([cfg, mdls, me]) => {
        setConfig(cfg);
        setModels(mdls);
        setCurrentUser(me.username);
      })
      .catch((e: unknown) => {
        const msg = e instanceof Error ? e.message : "Failed to load";
        // 401 → token expired
        if (msg.includes("401")) { tokenStorage.clear(); setAuthenticated(false); }
        else setError(msg);
      })
      .finally(() => setLoading(false));
  }, [authenticated]);

  function handleLogin(username: string) {
    setCurrentUser(username);
    setAuthenticated(true);
  }

  async function handleLogout() {
    await auth.logout();
    setAuthenticated(false);
    setCurrentUser(null);
    setModels([]);
    setConfig(null);
    setActiveModel(null);
  }

  // ── Not authenticated ───────────────────────────────────────────────────────
  if (!authenticated) {
    return <Login title={config?.title ?? "Admin Panel"} onLogin={handleLogin} />;
  }

  const schema = models.find((m) => m.name === activeModel) ?? null;

  // Scroll main area to top whenever the active view changes
  useEffect(() => {
    mainRef.current?.scrollTo({ top: 0, behavior: "instant" });
  }, [activeModel]);

  // ── Authenticated ───────────────────────────────────────────────────────────
  return (
    <div className="flex min-h-screen">
      <Sidebar
        models={models}
        activeModel={activeModel}
        onSelect={setActiveModel}
        title={config?.title ?? "Admin Panel"}
      />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-14 border-b border-border bg-card/60 backdrop-blur-sm flex items-center justify-end px-6 gap-3 shrink-0">
          {currentUser && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/60 border border-border text-xs">
              <div className="h-5 w-5 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                <User className="h-3 w-3 text-primary" />
              </div>
              <span className="font-medium">{currentUser}</span>
            </div>
          )}
          <Button
            size="sm"
            variant="ghost"
            className="h-8 text-xs gap-1.5 text-muted-foreground hover:text-foreground cursor-pointer"
            onClick={handleLogout}
          >
            <LogOut className="h-3.5 w-3.5" />
            Sign out
          </Button>
        </header>

        {/* Main content */}
        <main ref={mainRef} className="flex-1 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center h-full gap-2.5 text-muted-foreground text-sm">
              <span className="h-4 w-4 border-2 border-muted-foreground border-t-transparent rounded-full animate-spin" />
              Loading…
            </div>
          )}

          {!loading && error && (
            <div className="p-8">
              <div className="inline-flex items-start gap-3 px-4 py-3 rounded-lg bg-destructive/10 border border-destructive/30 text-sm text-destructive max-w-md">
                <span className="mt-px shrink-0">⚠</span>
                <span>Error: {error}</span>
              </div>
            </div>
          )}

          {!loading && !error && activeModel === null && (
            <Dashboard models={models} onSelect={setActiveModel} />
          )}

          {!loading && !error && activeModel === "__system_users__" && (
            <SystemUsers />
          )}

          {!loading && !error && schema !== null && activeModel !== "__system_users__" && (
            <ModelList
              key={schema.name}
              schema={schema}
              allowDelete={config?.allow_delete ?? true}
              pageSize={config?.page_size ?? 50}
            />
          )}
        </main>
      </div>
    </div>
  );
}
