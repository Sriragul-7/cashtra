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

## Custom Endpoints (dashboard aggregates, sync) — TBD next session

This section will cover:

- Dashboard summary endpoints (totals, monthly breakdowns, category charts).
- Offline sync protocol endpoint (batch pull/push of changes since a timestamp).
- Any other custom RPC endpoints needed.

Placeholder — to be filled in the next session.
