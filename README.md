# FastAPI Admin Panel

Auto-generated admin panel for FastAPI + SQLAlchemy + Alembic projects.

> **Self-funded hobby project** — built by one developer in spare time, not backed by any company.
> Contributions, bug reports, and ideas are very welcome — see [Contributing](#contributing).

- Reads your `alembic/env.py` → discovers all SQLAlchemy models automatically
- Full CRUD (list, search, sort, paginate, create, edit, delete)
- Bulk-select and bulk-delete rows
- DB-backed admin user authentication (JWT)
- Admin user management UI (create, edit, deactivate, change password, delete)
- Sync and async SQLAlchemy engine support
- React + TypeScript frontend with dark OLED theme
- 3 lines to integrate into any existing FastAPI project

---

## Requirements

- Python 3.10+
- PostgreSQL or any SQLAlchemy-supported database

---

## Installation

```bash
pip install auto-fastapi-admin-panel
```

The wheel ships with the pre-built frontend — no Node.js required.

---

## Integration

There are three ways to add the panel, depending on how your project is structured.

---

### Way 1 — Auto-discovery via Alembic (recommended)

If your project already uses Alembic, this is all you need. The panel reads
`alembic.ini` automatically to find your `Base` and all registered models.

```python
# main.py
import os
from fastapi import FastAPI
from sqlalchemy import create_engine
from fastapi_admin_panel import AdminPanel, AdminConfig

# Import your model modules first so SQLAlchemy registers them
from myapp import models  # noqa: F401

app = FastAPI()
engine = create_engine(os.environ["DATABASE_URL"])

config = AdminConfig(secret_key=os.environ["ADMIN_SECRET_KEY"])
panel = AdminPanel(app, engine, config=config)
```

The panel looks for `alembic.ini` next to `main.py`. All common layouts work:

```ini
script_location = alembic
script_location = database/migrations
script_location = %(here)s/database/migrations
```

If `alembic.ini` is in a non-standard location, tell the panel where to look:

```python
from pathlib import Path

config = AdminConfig(
    secret_key="...",
    project_root=Path("/path/to/dir/containing/alembic.ini"),
)
```

---

### Way 2 — Pass `base=` directly (no Alembic required)

If you don't use Alembic, or want to be explicit, pass your `DeclarativeBase`
class directly. The panel skips all file discovery.

```python
# main.py
import os
from fastapi import FastAPI
from sqlalchemy import create_engine
from fastapi_admin_panel import AdminPanel, AdminConfig

from myapp.database import Base   # your DeclarativeBase
from myapp import models           # noqa: F401 — register all models

app = FastAPI()
engine = create_engine(os.environ["DATABASE_URL"])

config = AdminConfig(secret_key=os.environ["ADMIN_SECRET_KEY"])
panel = AdminPanel(app, engine, config=config, base=Base)
```

> **Important:** Import your model modules before creating `AdminPanel`.
> `Base` alone isn't enough — SQLAlchemy only knows about models that have
> been imported at least once.

---

### Way 3 — Add panel table to your Alembic migrations

By default the panel creates its `admin_panel_users` table automatically at
startup (`CREATE TABLE IF NOT EXISTS`). If you prefer the table to be managed
by your own Alembic migrations (so it appears in `alembic revision --autogenerate`),
include the panel's metadata in your `env.py`:

```python
# alembic/env.py
from myapp.database import Base
from fastapi_admin_panel import admin_metadata   # ← add this

# Combine your metadata with the panel's metadata
target_metadata = [Base.metadata, admin_metadata]
```

Then generate and run migrations as usual:

```bash
alembic revision --autogenerate -m "add admin panel users table"
alembic upgrade head
```

When using this approach, the panel detects the table already exists and skips
its auto-create step.

---

### Async engine support

If you use an async engine (`asyncpg`, `aiosqlite`, etc.) the panel cannot
run its bootstrap at import time. Call `await panel.bootstrap()` inside your
lifespan:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine
from fastapi_admin_panel import AdminPanel, AdminConfig

from myapp.database import Base
from myapp import models  # noqa: F401

engine = create_async_engine(os.environ["DATABASE_URL"])
config = AdminConfig(secret_key=os.environ["ADMIN_SECRET_KEY"])

@asynccontextmanager
async def lifespan(app: FastAPI):
    await panel.bootstrap()   # ← must be first
    yield

app = FastAPI(lifespan=lifespan)
panel = AdminPanel(app, engine, config=config, base=Base)
```

---

## Configuration reference

```python
from fastapi_admin_panel import AdminConfig
from pathlib import Path

config = AdminConfig(
    # ── Required ────────────────────────────────────────────────────────────
    secret_key="...",              # use: import secrets; secrets.token_hex(32)

    # ── UI ──────────────────────────────────────────────────────────────────
    title="Admin Panel",           # shown in sidebar and browser tab
    prefix="/admin",               # URL prefix  →  http://host/admin

    # ── Behaviour ───────────────────────────────────────────────────────────
    page_size=50,                  # default rows per page
    allow_delete=True,             # set False to disable Delete globally
    models_exclude=["AuditLog"],   # model class names to hide from the panel

    # ── Auth ────────────────────────────────────────────────────────────────
    token_expire_hours=8,
    initial_admin_username="admin",
    initial_admin_password="admin",   # change before production

    # ── Discovery ───────────────────────────────────────────────────────────
    project_root=Path(__file__).parent,   # dir containing alembic.ini
)
```

All fields have defaults. The only one you should always set explicitly is
`secret_key`.

---

## First login

On first startup an admin user is seeded automatically:

| Field | Default |
|---|---|
| Username | `admin` |
| Password | `admin` |

The seed runs **once** — only when `admin_panel_users` is empty. After that,
manage accounts through the panel UI at **System → Admin Users**, or reset
via SQL:

```bash
# Generate a bcrypt hash
python -c "from fastapi_admin_panel.auth.utils import hash_password; print(hash_password('newpass'))"
```

```sql
UPDATE admin_panel_users SET hashed_password = '<hash>' WHERE username = 'admin';
```

---

## Admin Users page

The built-in **System → Admin Users** page lets you:

- Create new admin accounts (username + password)
- Edit username or toggle active/inactive
- Change any account's password
- Delete accounts

No DB access needed to manage panel users after initial setup.

---

## Full example

```python
import os
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import create_engine

from myapp.models import Base
from myapp import models  # noqa: F401

from fastapi_admin_panel import AdminPanel, AdminConfig

app = FastAPI(title="My API")
engine = create_engine(os.environ["DATABASE_URL"])

config = AdminConfig(
    secret_key=os.environ.get("ADMIN_SECRET_KEY", secrets.token_hex(32)),
    title="My Project Admin",
    prefix="/admin",
    page_size=25,
    allow_delete=True,
    models_exclude=["AlembicVersion"],
    initial_admin_username="admin",
    initial_admin_password=os.environ.get("ADMIN_PASSWORD", "changeme"),
    token_expire_hours=8,
    project_root=Path(__file__).parent,
)

panel = AdminPanel(app, engine, config=config)

@app.get("/")
def root():
    return {"status": "ok"}
```

---

## Performance impact in production

**TL;DR: zero impact on your existing routes.**

- **Startup:** model introspection is in-memory (iterating registered mappers), < 1 ms. Route registration for 50 models adds < 1 ms.
- **Per request:** admin routes live under `config.prefix` only. No global middleware is added. Your existing routes see zero overhead.
- **Database:** no second connection pool. One short-lived connection per admin request, same pool as your app.
- **Memory:** the built frontend is ~200 KB (gzipped), loaded once at startup.

If you want to remove the admin surface from the internet entirely, block
`/admin` at the reverse-proxy level (nginx `allow`/`deny` by IP).

---

## Development (from source)

```bash
git clone https://github.com/yourname/fastapi-admin-panel
cd fastapi-admin-panel
pip install -e ".[dev]"
python scripts/build.py          # installs npm deps + builds frontend

# Hot-reload during development
# Terminal 1
uvicorn myapp.main:app --reload
# Terminal 2
cd frontend && npm run dev       # Vite proxies /admin/api → :8000
```

Open [http://localhost:5173/admin/](http://localhost:5173/admin/).

---

## Security checklist before production

- [ ] Set `secret_key` from an environment variable, never hardcode it
- [ ] Change `initial_admin_password` before first deploy
- [ ] Serve behind HTTPS (nginx / Caddy / cloud load balancer)
- [ ] Set `allow_delete=False` if deletes aren't needed in production
- [ ] Use `models_exclude` to hide sensitive internal tables
- [ ] Restrict `/admin` access by IP at the reverse-proxy level
- [ ] Rotate the admin password after first login

---

## Contributing

No company behind this — just spare-time development. All contributions welcome:

- **Bug reports** — open an issue with steps to reproduce
- **Feature requests** — open an issue describing the use case
- **Pull requests** — small focused changes are easiest to review
- **Docs** — typos, unclear wording, missing examples

```bash
git clone https://github.com/artaabbasi/fastapi-admin-panel
pip install -e ".[dev]"
python scripts/build.py
pytest
```
