# Cashtra API Contract

> Base URL: `/` (relative to the Frappe site, e.g. `https://cashtra.local`).
> All responses are JSON. Authentication uses Frappe session cookies or API
> tokens (Bearer header).

---

## Standard CRUD — Frappe Resource API

Cashtra uses Frappe's built-in REST resource endpoints for all three core
DocTypes. No custom API wrappers are needed for basic operations.

### Account Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/resource/Account` | List accounts |
| `POST` | `/api/resource/Account` | Create an account |
| `GET` | `/api/resource/Account/{name}` | Get a single account |
| `PUT` | `/api/resource/Account/{name}` | Update an account |
| ~~`DELETE`~~ | ~~`/api/resource/Account/{name}`~~ | See archive/delete note below. |

**Archive vs Delete:** Accounts that have Transactions referencing them should
**not** be hard-deleted. The recommended flow is:

- **Archive** = `PUT /api/resource/Account/{name}` with body:
  ```json
  { "is_archived": 1 }
  ```
  The account is hidden from dropdowns and list views but remains in the
  database. Existing Transactions are unaffected. This is the **preferred
  way to "remove"** an Account in the UI.

- **Unarchive** = `PUT /api/resource/Account/{name}` with body:
  ```json
  { "is_archived": 0 }
  ```

- **Hard delete** (`DELETE` method) is only safe when **no Transactions** reference
  this account. Frappe's link-integrity check should block the delete if any
  linked Transactions exist — but the mobile app should not offer delete at all
  when transactions are present; archive is always the right choice.

### Category Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/resource/Category` | List categories |
| `POST` | `/api/resource/Category` | Create a category |
| `GET` | `/api/resource/Category/{name}` | Get a single category |
| `PUT` | `/api/resource/Category/{name}` | Update a category |
| ~~`DELETE`~~ | ~~`/api/resource/Category/{name}`~~ | See archive/delete note below. |

**Archive vs Delete:** Same principle as Account. Categories with existing
Transactions should be archived, not deleted:

- **Archive** = `PUT /api/resource/Category/{name}` with body:
  ```json
  { "is_archived": 1 }
  ```

- **Unarchive** = `PUT /api/resource/Category/{name}` with body:
  ```json
  { "is_archived": 0 }
  ```

- **Hard delete** (`DELETE` method) is only safe when **no Transactions** reference
  this category. The mobile app should prefer archive in the UI.

### Tag Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/resource/Tag` | List tags |
| `POST` | `/api/resource/Tag` | Create a tag |
| `GET` | `/api/resource/Tag/{name}` | Get a single tag |
| `PUT` | `/api/resource/Tag/{name}` | Update a tag |
| ~~`DELETE`~~ | ~~`/api/resource/Tag/{name}`~~ | See archive/delete note below. |

**Archive vs Delete:** Same principle as Account/Category. Tags referenced by
existing TransactionTag child rows should be archived, not deleted:

- **Archive** = `PUT /api/resource/Tag/{name}` with body:
  ```json
  { "is_archived": 1 }
  ```

- **Unarchive** = `PUT /api/resource/Tag/{name}` with body:
  ```json
  { "is_archived": 0 }
  ```

- **Hard delete** (`DELETE` method) is only safe when **no Transactions** reference
  this tag via the TransactionTag child table. The mobile app should prefer
  archive in the UI.

### Transaction Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/resource/Transaction` | List transactions |
| `POST` | `/api/resource/Transaction` | Create a transaction |
| `GET` | `/api/resource/Transaction/{name}` | Get a single transaction |
| `PUT` | `/api/resource/Transaction/{name}` | Update a transaction |
| ~~`DELETE`~~ | ~~`/api/resource/Transaction/{name}`~~ | **Not used.** See soft-delete note below. |

### Query Parameters (list endpoints)

These apply to all `GET /api/resource/{DocType}` calls:

| Parameter | Example | Description |
|-----------|---------|-------------|
| `filters` | `[["account_type","=","Bank"]]` | JSON-encoded array of filter tuples. Supports `=`, `!=`, `>`, `<`, `>=`, `<=`, `like`, `not like`, `in`, `not in`. |
| `fields` | `["account_name","current_balance"]` | JSON array of field names to return. Omit for all fields. |
| `limit_page_length` | `20` | Max records per page (default 20, max 1000). |
| `limit_start` | `0` | Offset for pagination. |
| `order_by` | `date desc` | Column and direction. Default varies by DocType. |
| `or_filters` | `[["category_type","=","Income"],["category_type","=","Expense"]]` | OR-combined filter groups. |

#### Default ordering

- **Account**: `account_name asc`
- **Category**: `category_type asc, category_name asc`
- **Tag**: `sort_order asc, tag_name asc`
- **Transaction**: `date desc, modified desc`

### Soft-Delete for Transactions

Transactions are **never hard-deleted** via the API. Instead:

- **Delete** = `PUT /api/resource/Transaction/{name}` with body:
  ```json
  { "is_deleted": 1 }
  ```
  This sets the soft-delete flag. The `modified` timestamp updates automatically,
  so the offline sync protocol picks up the change like any other mutation.

- **Restore** = `PUT /api/resource/Transaction/{name}` with body:
  ```json
  { "is_deleted": 0 }
  ```

- **List queries** must always filter out soft-deleted records. Add this filter
  by default on all `GET /api/resource/Transaction` calls:
  ```
  filters=[["is_deleted","=",0]]
  ```
  The backend (or a Frappe hook) should enforce this so the client never has to
  remember.

- **`DELETE` method is not used.** If called, return `405 Method Not Allowed`
  or simply ignore it. All "deletion" flows go through `PUT`.

---

## Custom Endpoints — Sync Protocol

Two whitelisted RPC endpoints handle offline sync for all four DocTypes in
a single call each. This avoids 4x round trips on what's typically a flaky
mobile connection.

---

### POST /api/method/cashtra.api.sync.pull

Fetch all records that changed since a given timestamp. Used for both full
initial sync (no `since`) and incremental sync (pass the `server_time` from
the previous pull).

**Request body:**

```json
{ "since": "<ISO timestamp>" }
```

Omit `since` or pass `null` for a full initial sync. The server returns
every record the user owns, regardless of `modified`.

**Response:**

```json
{
  "server_time": "<ISO timestamp>",
  "accounts": [...],
  "categories": [...],
  "tags": [...],
  "transactions": [...]
}
```

Each array contains every record matching the query, with **all fields**
including `client_id` and `modified`. The client should store
`server_time` and use it as the `since` value for its next incremental
pull.

**Why `server_time` is captured at the START of the query (not the end):**
If we captured it at the end, a record modified *during* the query window
would have a `modified` timestamp between our start and end snapshots.
On the next incremental pull (using the end timestamp as `since`), that
record's `modified` would be *before* the new `since` — so it would be
silently missed. Capturing `server_time` before any queries run guarantees
every record modified up to that instant is included in the current pull,
and the next pull starts from that exact cutoff.

**Filtering rules:**
- Account, Category, Tag: `modified > since` AND `owner = current_user`.
- Transaction: `modified > since` AND `owner = current_user`.
  **Soft-deleted records (`is_deleted=1`) ARE included.** The client needs
  them to know a record was deleted locally (to hide/remove it from its
  local DB). This is the one place where the sync payload deliberately
  differs from normal list views, which always exclude `is_deleted=1`.

---

### POST /api/method/cashtra.api.sync.push

Batched creates and updates across all four DocTypes. Each record includes
its `client_id` (required for records created offline that don't have a
server-assigned `name` yet) and all field values.

**Request body:**

```json
{
  "accounts": [{...}, ...],
  "categories": [...],
  "tags": [...],
  "transactions": [...]
}
```

Each array may be empty or omitted entirely. For each record in the push:

1. **If `client_id` already exists on the server AND the incoming
   `modified` is NOT newer than the server's stored `modified` for that
   record:** skip it, do not overwrite. Add it to the response's
   `rejected` list with `reason: "stale"`. This is the last-write-wins
   conflict case — the server's version wins.

2. **If `client_id` already exists AND incoming `modified` IS newer:**
   apply the update normally through the DocType's controller (which runs
   `validate()` — all business rules are enforced).

3. **If `client_id` does not exist on the server:** create a new record
   through the DocType's controller. The server assigns the `name`.

**Response:**

```json
{
  "accepted": {
    "accounts": [
      {"client_id": "...", "name": "<server-assigned name>"},
      ...
    ],
    "categories": [...],
    "tags": [...],
    "transactions": [...]
  },
  "rejected": {
    "accounts": [
      {"client_id": "...", "reason": "stale", "server_modified": "<timestamp>"}
    ],
    "categories": [...],
    "tags": [...],
    "transactions": [...]
  }
}
```

The `accepted` mapping is how the client learns the real server name for
records it created offline with only a `client_id`. The client should update
its local record's primary key from the temporary `client_id` to the
server-assigned `name`.

The `rejected` list lets the client optionally surface "an edit didn't apply"
rather than silently losing it. Each rejected entry includes the
`server_modified` timestamp so the client can pull the server's version.

**Conflict resolution policy:** Last-write-wins, determined by `modified`
timestamps. No merge. If the client and server both modified the same record
while offline, the version with the newer `modified` wins. The losing side
receives a `rejected` entry so it can decide how to handle the loss (e.g.
show a conflict badge, or silently accept the server's version).

### Cross-record references in the same push batch

When a user creates a new Account and immediately records a Transaction
against it while still offline, both records are in the same push batch.
The Transaction's `account` field can't be a server-assigned name yet — it
doesn't exist on the server. The client must reference it by `client_id`.

**Reference format — two cases:**

| Scenario | JSON shape | Example |
|----------|-----------|---------|
| Referencing an **already-synced** record (has a real server name) | Plain string (the server `name`) | `"account": "HDFC Savings"` |
| Referencing a **same-batch** record (not yet on the server) | Object with `client_id` key | `"account": {"client_id": "acc-1"}` |

This applies to the following Link fields:

- **Transaction** → `account`, `category`, `transfer_to_account`
- **Transaction** → `tags[].tag` (TransactionTag child table rows)
- **Category** → `parent_category`

The server resolves same-batch references progressively as it processes
the batch (see dependency order below). If a referenced `client_id` is
not found in the current batch OR as an existing record's `client_id` in
the database, that specific record is rejected with:

```json
{
  "client_id": "txn-1",
  "reason": "unresolved reference",
  "detail": "client_id 'acc-1' not found in batch or database"
}
```

The rest of the batch continues processing — a single bad reference does
not abort the entire push.

### Batch processing order

Records are processed in dependency order within a single push call:

1. **Accounts and Tags** (no inter-dependencies) — processed first. As each
   record is created, its `client_id → server_name` mapping is added to a
   resolution map.
2. **Categories** (may reference `parent_category` which is another Category)
   — processed second. Same-batch `parent_category` references are resolved
   from the map built in step 1.
3. **Transactions** (may reference `account`, `category`,
   `transfer_to_account`, and `tags[].tag`) — processed last. All
   same-batch references are resolved from the map built in steps 1–2.

---
