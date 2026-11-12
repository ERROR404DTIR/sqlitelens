#!/usr/bin/env python3
"""sqlitelens - explore any SQLite database from your terminal.

One file, zero dependencies. The database is always opened read-only.

  python sqlitelens.py shop.db tables
  python sqlitelens.py shop.db schema [table]
  python sqlitelens.py shop.db show users -n 10
  python sqlitelens.py shop.db query "SELECT * FROM orders WHERE total > 100"
  python sqlitelens.py shop.db stats orders
  python sqlitelens.py shop.db export users --format csv > users.csv
"""
import argparse
import csv
import json
import sqlite3
import sys
from pathlib import Path

__version__ = "1.0.0"


def q(name):
    """Quote an SQL identifier."""
    return '"' + name.replace('"', '""') + '"'


def cell(value, width=40):
    if value is None:
        s = "NULL"
    elif isinstance(value, (bytes, bytearray)):
        s = f"<{len(value)} bytes>"
    else:
        s = str(value)
    s = s.replace("\n", " ").replace("\r", " ")
    return s if len(s) <= width else s[: width - 3] + "..."


def render(headers, rows, width=40):
    body = [[cell(c, width) for c in r] for r in rows]
    cols = [max([len(h)] + [len(r[i]) for r in body]) for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, cols)))
    print("  ".join("-" * w for w in cols))
    for r in body:
        print("  ".join(c.ljust(w) for c, w in zip(r, cols)))
    print(f"\n({len(body)} row{'s' if len(body) != 1 else ''})")


def open_db(path):
    p = Path(path)
    if not p.is_file():
        sys.exit(f"error: no such file: {path}")
    try:
        con = sqlite3.connect(p.resolve().as_uri() + "?mode=ro", uri=True)
        con.execute("SELECT count(*) FROM sqlite_master")
    except sqlite3.Error as e:
        sys.exit(f"error: {path} is not a readable SQLite database ({e})")
    return con


def objects(con):
    return con.execute(
        "SELECT name, type FROM sqlite_master WHERE type IN ('table','view') "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


def need(con, table):
    if table not in [n for n, _ in objects(con)]:
        sys.exit(f"error: no table or view named '{table}'. Try the 'tables' command.")


def run(con, sql):
    try:
        cur = con.execute(sql)
        return [d[0] for d in cur.description or []], cur.fetchall()
    except sqlite3.Error as e:
        sys.exit(f"sql error: {e}")


def cmd_tables(con, a):
    rows = []
    for name, kind in objects(con):
        count = con.execute(f"SELECT COUNT(*) FROM {q(name)}").fetchone()[0]
        cols = len(con.execute(f"PRAGMA table_info({q(name)})").fetchall())
        rows.append((name, kind, count, cols))
    render(["name", "type", "rows", "columns"], rows)


def cmd_schema(con, a):
    sql = "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%'"
    args = ()
    if a.table:
        need(con, a.table)
        sql += " AND (name = ? OR tbl_name = ?)"
        args = (a.table, a.table)
    for (stmt,) in con.execute(sql + " ORDER BY type DESC, name", args):
        print(stmt + ";\n")


def cmd_show(con, a):
    need(con, a.table)
    headers, rows = run(con, f"SELECT * FROM {q(a.table)} LIMIT {int(a.n)}")
    render(headers, rows, a.width)


def cmd_query(con, a):
    headers, rows = run(con, a.sql)
    if not headers:
        print("(no result set - the database is opened read-only)")
        return
    render(headers, rows, a.width)


def cmd_stats(con, a):
    need(con, a.table)
    total = con.execute(f"SELECT COUNT(*) FROM {q(a.table)}").fetchone()[0]
    out = []
    for col in [r[1] for r in con.execute(f"PRAGMA table_info({q(a.table)})")]:
        c = q(col)
        row = con.execute(
            f"SELECT COUNT({c}), COUNT(DISTINCT {c}), MIN({c}), MAX({c}) FROM {q(a.table)}"
        ).fetchone()
        out.append((col,) + tuple(row))
    print(f"{a.table}: {total} rows\n")
    render(["column", "non_null", "distinct", "min", "max"], out, a.width)


def cmd_export(con, a):
    need(con, a.table)
    headers, rows = run(con, f"SELECT * FROM {q(a.table)}")
    if a.format == "json":
        data = [dict(zip(headers, r)) for r in rows]
        json.dump(data, sys.stdout, indent=2, ensure_ascii=False,
                  default=lambda o: o.hex() if isinstance(o, (bytes, bytearray)) else str(o))
        print()
    else:
        w = csv.writer(sys.stdout, lineterminator="\n")
        w.writerow(headers)
        w.writerows(rows)


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-w", "--width", type=int, default=40, help="max cell width (default 40)")

    p = argparse.ArgumentParser(prog="sqlitelens", description="Explore SQLite databases from your terminal (read-only).")
    p.add_argument("db", help="path to a SQLite database file")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tables", help="list tables and views with row counts").set_defaults(fn=cmd_tables)

    s = sub.add_parser("schema", help="print CREATE statements")
    s.add_argument("table", nargs="?")
    s.set_defaults(fn=cmd_schema)

    s = sub.add_parser("show", parents=[common], help="show the first rows of a table")
    s.add_argument("table")
    s.add_argument("-n", type=int, default=20, help="number of rows (default 20)")
    s.set_defaults(fn=cmd_show)

    s = sub.add_parser("query", parents=[common], help="run a read-only SQL query")
    s.add_argument("sql")
    s.set_defaults(fn=cmd_query)

    s = sub.add_parser("stats", parents=[common], help="per-column counts, distinct values, min and max")
    s.add_argument("table")
    s.set_defaults(fn=cmd_stats)

    s = sub.add_parser("export", help="dump a table to stdout as CSV or JSON")
    s.add_argument("table")
    s.add_argument("--format", choices=["csv", "json"], default="csv")
    s.set_defaults(fn=cmd_export)

    a = p.parse_args()
    a.fn(open_db(a.db), a)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        pass
    except KeyboardInterrupt:
        sys.exit(130)
