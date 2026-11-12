<p align="center">
  <img src="assets/banner.svg" alt="sqlitelens animated terminal demo" width="800">
</p>

<h1 align="center">sqlitelens</h1>

<p align="center">
  Explore any SQLite database from your terminal.<br>
  <b>One file. Zero dependencies. Read-only and safe.</b>
</p>

---

## Quick start

No install, no `pip`. Just download the single file and run it:

```bash
curl -O https://raw.githubusercontent.com/ERROR404DTIR/sqlitelens/main/sqlitelens.py
python sqlitelens.py mydata.db tables
```

Requires Python 3.8+ (uses only the standard library).

## Commands

| Command | What it does |
|---|---|
| `tables` | List tables and views with row and column counts |
| `schema [table]` | Print the `CREATE` statements |
| `show <table> -n 20` | Preview the first rows as an aligned table |
| `query "<sql>"` | Run any read-only SQL query |
| `stats <table>` | Per-column non-null count, distinct values, min and max |
| `export <table> --format csv\|json` | Dump a table to stdout |

## Examples

```bash
python sqlitelens.py shop.db schema orders
python sqlitelens.py shop.db show users -n 5 -w 60
python sqlitelens.py shop.db query "SELECT status, COUNT(*) FROM orders GROUP BY status"
python sqlitelens.py shop.db export users --format json > users.json
```

## Why it's safe

The database is opened with SQLite's `mode=ro`, so nothing you run here can modify your data.
BLOBs are shown as `<N bytes>` and long cells are truncated (change with `-w`).
