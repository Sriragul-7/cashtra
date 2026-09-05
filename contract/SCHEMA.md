# Cashtra Data Model

> v1 scope: single-user, single-currency (INR). Multi-user / multi-book and
> multi-currency support are deferred to v2.

---

## Account

Represents a money container -- a bank account, cash wallet, credit card, etc.

### Fields

| # | Field Name | Field Type | Required | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `account_name` | Data | Yes | Display name for the account (e.g. "HDFC Savings"). |
| 2 | `account_type` | Select | Yes | One of: `Cash`, `Bank`, `Card`, `Wallet`. |
| 3 | `currency` | Link -> Currency | Yes | Three-letter ISO code. Defaults to `INR` in v1. |
| 4 | `opening_balance` | Currency | No | Balance at the time the account was added. Defaults to `0`. |
| 5 | `current_balance` | Currency | Yes, read-only | Running balance. **Not stored redundantly** -- recalculated on every Transaction save/delete. See Business Rules. |
| 6 | `is_archived` | Check | No | Soft archive flag. Archived accounts are hidden from UI but not deleted. Default `0`. |
| 7 | `icon` | Data | No | Icon identifier for the frontend (e.g. "icon-wallet"). |
| 8 | `color` | Data | No | Hex or named colour for the frontend. |

### Notes

- **`owner`** (standard Frappe field): Used for single-user scoping in v1. Every
  query implicitly filters on `owner = current_user`. In v2 this will be replaced
  by a book/team concept -- note this but do not build it yet.

### Indexes

- `account_type` -- filtered in list views.
- `is_archived` -- filtered in list views.

### Business Rules

1. `account_name` must be unique per owner (add a unique constraint on
   `owner + account_name`).
2. `current_balance` is a **virtual/calculated field**. On every Transaction
   save or delete:
   ```
   current_balance = opening_balance
     + SUM(amount) WHERE transaction_type = 'Income'   AND account = self AND is_deleted = 0
     - SUM(amount) WHERE transaction_type = 'Expense'  AND account = self AND is_deleted = 0
     - SUM(amount) WHERE transaction_type = 'Transfer' AND account = self AND is_deleted = 0
     + SUM(amount) WHERE transaction_type = 'Transfer' AND transfer_to_account = self AND is_deleted = 0
   ```
   This is recalculated and written to the field on every relevant mutation.
   It is **not** cached or stored separately -- the recalculation is the source
   of truth.

   **Important:** Every SUM clause must include `is_deleted = 0`. Soft-deleted
   transactions must NOT count toward the balance. This is critical -- a
   transaction that is soft-deleted should behave as if it never happened for
   balance purposes, and restoring it (is_deleted=0) should bring it back.

3. Archiving an account does not affect its transactions; it only hides the
   account from dropdowns and list views.

---

## Category

A classification label for Income/Expense transactions. Supports a single
level of nesting via `parent_category`.

### Fields

| # | Field Name | Field Type | Required | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `category_name` | Data | Yes | Display name (e.g. "Groceries", "Salary"). |
| 2 | `category_type` | Select | Yes | One of: `Income`, `Expense`. |
| 3 | `parent_category` | Link -> Category | No | Parent category for sub-category nesting. Optional -- null means top-level. |
| 4 | `icon` | Data | No | Emoji character representing this category, shown inside a colored circle in the UI (e.g. "\ud83c\udf54"). Not an image upload. |
| 5 | `color` | Data | No | Hex or named colour for the frontend. |
| 6 | `is_archived` | Check | No | Soft archive flag. Default `0`. |
| 7 | `sort_order` | Int | No | Manual sort position for drag-to-reorder in category lists. Lower values appear first. Default `0`. |

### Indexes

- `category_type` -- filtered in list views and dropdowns.
- `parent_category` -- used for tree queries.
- `is_archived` -- filtered in list views.
- `sort_order` -- used for ordering queries in list views.

### Business Rules

1. `category_name` must be unique per `category_type` per `parent_category` per
   owner (unique constraint on `owner + category_type + parent_category +
   category_name`). This allows e.g. "Other" to exist as a subcategory under
   both "Food" and "Travel" without colliding.
2. `parent_category` must be of the same `category_type` (an Income category
   cannot be a child of an Expense category).
3. `parent_category` must not reference itself (directly or via a cycle).
   Validate on save.
4. Archiving a category does not affect existing transactions tagged with it.

---

## Transaction

A single financial event -- an income receipt, an expense, or a transfer
between accounts.

### Fields

| # | Field Name | Field Type | Required | Indexed | Description |
|---|-----------|-----------|----------|---------|-------------|
| 1 | `date` | Date | Yes | Yes | Date of the transaction. |
| 2 | `amount` | Currency | Yes | -- | Always stored as a **positive** number. The sign is implied by `transaction_type`, never by the value itself. |
| 3 | `transaction_type` | Select | Yes | Yes | One of: `Income`, `Expense`, `Transfer`. |
| 4 | `account` | Link -> Account | Yes | Yes | The source account (where money comes from for Income, goes out from for Expense/Transfer). |
| 5 | `category` | Link -> Category | Conditional | -- | Required when `transaction_type` is `Income` or `Expense`. Must be **empty** (null) when `transaction_type` is `Transfer`. See validation rule. |
| 6 | `transfer_to_account` | Link -> Account | Conditional | -- | Required **only** when `transaction_type` is `Transfer`. The destination account. Must be empty for Income/Expense. |
| 7 | `note` | Small Text | No | -- | Free-text memo / description. |
| 8 | `receipt` | Attach Image | No | -- | Photo or scan of a receipt. |
| 9 | `tags` | Table -> TransactionTag | No | -- | Child table linking to Tag DocType (see TransactionTag below). Enables autocomplete and reuse of tags across transactions. |
| 10 | `is_deleted` | Check | No | Yes | Soft-delete flag. Default `0`. See Business Rules for why this exists. |
| 11 | `modified` | -- | -- | Yes | Standard Frappe field. Used by the offline sync protocol as the "changed since" timestamp. |

### TransactionTag (child table row)

| Field | Field Type | Required | Description |
|-------|-----------|----------|-------------|
| `tag` | Link -> Tag | Yes | Reference to an existing Tag record. Enables autocomplete/reuse of tags across transactions instead of freeform per-transaction text. |

### Notes

- **`is_deleted`**: Transactions are never hard-deleted. When a user "deletes"
  a transaction the app sends `PUT .../Transaction/{name}` with `is_deleted=1`.
  This is essential for offline sync -- a hard delete would require a tombstone
  record or conflict resolution; a soft-delete is a normal mutation that syncs
  like any other field change.
- **`modified`**: The standard Frappe `modified` timestamp (auto-set on every
  save). The sync protocol uses this to answer "what changed since timestamp X?"
  queries. It is indexed to keep those queries fast.

### Indexes

- `date` -- primary sort for list views and reports.
- `transaction_type` -- filtered in most views.
- `account` -- filtered when showing account-specific transaction lists.
- `is_deleted` -- filtered on every list query (default `is_deleted = 0`).
- `modified` -- used by sync protocol range queries.

### Business Rules

1. **Amount is always positive.** If a negative amount is submitted, reject or
   take its absolute value. The sign is carried by `transaction_type`.
2. **Transfer validation:**
   - `transfer_to_account` is required and must differ from `account`.
   - `category` must be empty (null).
3. **Income / Expense validation:**
   - `category` is required.
   - `transfer_to_account` must be empty (null).
4. **Soft-delete:** `DELETE /api/resource/Transaction/{name}` is **not used**.
   Deletion is performed as `PUT` with `is_deleted=1`. The `modified` field
   updates normally, so sync picks it up.
5. **Balance recalculation:** After every save or soft-delete of a Transaction,
   the `current_balance` of all affected Accounts (the `account` and, for
   Transfers, the `transfer_to_account`) must be recalculated per the Account
   business rules. Only non-deleted transactions (is_deleted=0) count.

---

## Tag

A reusable label that can be applied to transactions. Tags are owned per-user
and support emoji + color for visual identification in the UI.

### Fields

| # | Field Name | Field Type | Required | Description |
|---|-----------|-----------|----------|-------------|
| 1 | `tag_name` | Data | Yes | Display name for the tag (e.g. "reimbursable", "tax-deductible"). |
| 2 | `emoji` | Data | No | The emoji character shown on the tag badge (e.g. "\ud83d\udcb0"). |
| 3 | `color` | Data | No | Hex color for the tag's badge background. |
| 4 | `is_archived` | Check | No | Soft archive flag. Default `0`. |
| 5 | `sort_order` | Int | No | Manual sort position for drag-to-reorder in tag lists. Lower values appear first. Default `0`. |

### Indexes

- `is_archived` -- filtered in list views and dropdowns.
- `sort_order` -- used for ordering queries in list views.

### Business Rules

1. `tag_name` must be unique per owner (unique constraint on `owner +
   tag_name`). The same tag name cannot exist twice for the same user, but
   different users can have tags with the same name.
2. Archiving a tag does not affect existing transactions that reference it.
   The tag simply stops appearing in autocomplete and dropdowns until
   unarchived.
