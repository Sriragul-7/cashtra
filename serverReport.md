# Cashtra — Server Reports

> Chronological log of setup, verification, and design reports from each
> session. Kept for reference so we can trace back what was done and why.

---

## 1. Session 1 — Initial Scaffold Setup

### 1.1 Environment Check (Step 0)

| Tool | Version | Status |
|------|---------|--------|
| python3 | 3.12.3 | ✅ (need 3.10+) |
| node | v24.18.1 | ✅ (need 18+) |
| redis-server | 7.0.15 | ✅ |
| mariadb | 10.11.14 | ✅ |
| wkhtmltopdf | 0.12.6 | ✅ |
| bench | 5.31.0 | ✅ |

**MariaDB root password**: (redacted — stored locally, never committed to repo)

### 1.2 Bench / Site / App Creation (Step 1)

- **Bench**: Created at `frappe-bench/` (Frappe v15 branch).
- **Site**: `cashtra.local` — created successfully with MariaDB backend.
- **App**: `cashtra` created:
  - Title: Cashtra
  - Description: Open-source, self-hostable expense tracker backend
  - Publisher: Sriragul
  - License: MIT
- **Admin password**: (placeholder — must be changed before any real deployment)
- **`bench start`**: All services booted successfully:
  - `redis_cache.1` on port 13000
  - `redis_queue.1` on port 11000
  - `web.1` on port 8000
  - `socketio.1` on port 9000
  - `worker.1`, `schedule.1`, `watch.1` — all running

**Notes:**
- `bench init` failed at the supervisor restart step (supervisor not installed)
  but the bench directory and frappe app were fully created. Proceeded manually.
- `bench new-app` also failed at supervisor restart but the app was created and
  built successfully. Proceeded with `bench --site cashtra.local install-app cashtra`
  which succeeded.

### 1.3 Repo Structure (Step 2)

Created at the project root:
- `contract/SCHEMA.md` — placeholder
- `contract/API.md` — placeholder
- `contract/SYNC_PROTOCOL.md` — placeholder
- `STATUS.md` — Backend/Mobile sections with "Not started yet"
- `.gitignore` — standard Frappe/bench + Python/Node ignores

### 1.4 Git (Step 3)

- Initialized on `main` branch at `/home/sriragul/cashtra/`.
- Remote: `origin` → `https://github.com/Sriragul-7/cashtra.git`
- Committed: `f644e0f` — "Initial scaffold: Frappe bench + cashtra app + repo structure"
- **Push failed**: No GitHub credentials configured. User pushed manually later.

---

## 2. Session 2 — Verification + Restructure

### 2.1 Verification (Step 1)

| Check | Result |
|-------|--------|
| `frappe-bench/apps/cashtra` git repo | Valid |
| Branch | `develop` |
| Existing commit | `43c8c90 feat: Initialize App` |
| Remote | None (clean) |
| Outer `.git` at `/home/sriragul/cashtra/` | Present, commit `f644e0f` |

### 2.2 Restructure (Step 2)

- **Moved** `contract/` (3 files) and `STATUS.md` from outer project root into
  `frappe-bench/apps/cashtra/`.
- **Merged `.gitignore`** — kept Frappe-app-relevant entries (`*.pyc`,
  `__pycache__/`, `node_modules/`, `.env`, IDE/OS ignores, etc.), dropped
  `frappe-bench/`, `sites/`, `env/`, `logs/` paths.
- **Remote set**: `origin` → `https://github.com/Sriragul-7/cashtra.git`
- **Committed**: `41f83fe` on branch `develop` — "Add contract docs and status tracking to app repo"
- **Push failed**: No GitHub credentials (HTTPS or SSH) configured.

### 2.3 Outer Project Root Contents (Step 3)

| Item | Type | Notes |
|------|------|-------|
| `.git/` | dir | Orphaned outer repo (commit `f644e0f`) — to be removed |
| `.gitignore` | file | Redundant — superseded by app's `.gitignore` |
| `frappe-bench/` | dir | Working bench, contains the real repo |

---

## 3. Session 3 — Cleanup

### 3.1 Removed

- `/home/sriragul/cashtra/.git/` — orphaned outer repo (commit `f644e0f`)
- `/home/sriragul/cashtra/.gitignore` — redundant

### 3.2 What Remains

Only `frappe-bench/` at the project root. The real git repo lives at
`frappe-bench/apps/cashtra/`.

---

## 4. Session 3 (cont.) — Git Push Troubleshooting

User pushed manually after configuring GitHub credentials:
```
git push -u origin develop
```
**Issue**: The user initially tried `git push -u origin main` from inside
`frappe-bench/apps/cashtra/` but the branch was called `develop`, not `main`.
Corrected to `git push -u origin develop` — succeeded.

**Note**: The user's home directory had a separate `~/frappe-bench/` from a
previous bench setup. The cashtra bench lives at `~/cashtra/frappe-bench/`.
The user needed to `cd` into the correct path:
```
cd /home/sriragul/cashtra/frappe-bench/apps/cashtra
```

---

## 5. Session 4 — Initial Data Contract

### 5.1 Files Written

- `contract/SCHEMA.md` — Full data model for 3 DocTypes (Account, Category,
  Transaction) with field specs, indexes, and business rules.
- `contract/API.md` — REST endpoint contract using Frappe's standard resource
  API, with query parameter docs and soft-delete protocol for Transactions.

### 5.2 Design Decisions

- **v1 is single-user, single-currency (INR).** Multi-user/multi-currency is
  deferred to v2.
- **`current_balance` is calculated, not cached.** Recalculated on every
  Transaction save/delete. No redundant storage.
- **Soft-delete for Transactions.** `is_deleted` flag used instead of hard
  deletes. Essential for offline sync — avoids tombstone records.
- **`modified` field** is the sync protocol's "changed since" marker.
- **Transfers** link two accounts; `category` is empty for Transfers.
- **Tags** are a child table on Transaction for user-defined labels.
