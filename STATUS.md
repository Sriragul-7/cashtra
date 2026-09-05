## Backend

- [x] Data contract complete for Account, Category, Transaction, Tag (see contract/SCHEMA.md and contract/API.md).
- [x] Account DocType implemented and verified — owner-scoped permissions, balance defaulting, duplicate name check working.
- [x] Category DocType implemented and verified — type-matching, cycle prevention, parent-scoped uniqueness working.
- [x] Tag DocType implemented and verified — owner-scoped uniqueness working.
- [x] Transaction DocType implemented and verified — conditional validation for Income/Expense/Transfer types working. Balance recalculation still pending as a separate step.

**All four core DocTypes now exist:** Account, Category, Tag, Transaction (plus TransactionTag child table).

## Mobile

- [ ] Not started yet
