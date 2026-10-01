"""Parse a Jira export (CSV or XLSX) and compute progress metrics.

No persistence: the file is read in memory, summarized, and discarded.
"""
import csv
import io

from openpyxl import load_workbook

COMPLETE_STATUSES = ["QA Passed", "Deployed To Production"]
INCOMPLETE_STATUSES = ["To Do", "In Progress", "Dev to Test", "REVISION"]

# Header names Jira uses; fall back to column letters J/K if headers differ.
POINTS_HEADERS = ["custom field (story point estimate)", "story point estimate", "story points"]
STATUS_HEADERS = ["status"]
KEY_HEADERS = ["issue key", "key"]
SUMMARY_HEADERS = ["summary"]
POINTS_FALLBACK_COL = 9   # Column J
STATUS_FALLBACK_COL = 10  # Column K


class ReportError(Exception):
    pass


def _norm(value):
    return str(value or "").replace("\ufeff", "").strip().lower()


def _read_rows(filename, data):
    name = filename.lower()
    if name.endswith(".csv"):
        text = data.decode("utf-8-sig", errors="replace")
        return [row for row in csv.reader(io.StringIO(text))]
    if name.endswith((".xlsx", ".xlsm")):
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        rows = [["" if c is None else c for c in row] for row in ws.iter_rows(values_only=True)]
        wb.close()
        return rows
    raise ReportError("Unsupported file type. Upload a .csv or .xlsx Jira export.")


def _find_header_row(rows):
    """Jira exports put headers on row 1, but tolerate a few title rows above."""
    for i, row in enumerate(rows[:10]):
        if any(_norm(c) == "status" for c in row):
            return i
    return 0


def _col(header, candidates, fallback=None):
    normed = [_norm(h) for h in header]
    for cand in candidates:
        if cand in normed:
            return normed.index(cand)
    return fallback


def _to_points(value):
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_report(filename, data, complete=None, incomplete=None):
    complete = complete or COMPLETE_STATUSES
    incomplete = incomplete or INCOMPLETE_STATUSES
    complete_set = {s.strip().lower() for s in complete}
    incomplete_set = {s.strip().lower() for s in incomplete}

    rows = _read_rows(filename, data)
    if not rows:
        raise ReportError("The file is empty.")

    h = _find_header_row(rows)
    header = rows[h]
    pts_i = _col(header, POINTS_HEADERS, POINTS_FALLBACK_COL)
    st_i = _col(header, STATUS_HEADERS, STATUS_FALLBACK_COL)
    key_i = _col(header, KEY_HEADERS)
    sum_i = _col(header, SUMMARY_HEADERS)

    totals = {
        "points_complete": 0.0, "points_incomplete": 0.0,
        "tasks_complete": 0, "tasks_incomplete": 0,
    }
    by_status = {}
    unestimated = []   # counted as tasks, 0 points
    unmapped = []      # status not in either list; excluded from totals

    for row in rows[h + 1:]:
        if not any(str(c).strip() for c in row):
            continue
        get = lambda i: row[i] if i is not None and i < len(row) else ""
        status = str(get(st_i)).strip()
        points = _to_points(get(pts_i))
        item = {"key": str(get(key_i)), "summary": str(get(sum_i)), "status": status}

        s = status.lower()
        if s in complete_set:
            bucket = "complete"
        elif s in incomplete_set:
            bucket = "incomplete"
        else:
            unmapped.append(item)
            continue

        totals[f"tasks_{bucket}"] += 1
        totals[f"points_{bucket}"] += points or 0
        if points is None:
            unestimated.append(item)

        entry = by_status.setdefault(status, {"bucket": bucket, "tasks": 0, "points": 0.0})
        entry["tasks"] += 1
        entry["points"] += points or 0

    total_pts = totals["points_complete"] + totals["points_incomplete"]
    total_tasks = totals["tasks_complete"] + totals["tasks_incomplete"]
    totals["points_total"] = total_pts
    totals["tasks_total"] = total_tasks
    totals["points_pct"] = round(100 * totals["points_complete"] / total_pts, 1) if total_pts else 0
    totals["tasks_pct"] = round(100 * totals["tasks_complete"] / total_tasks, 1) if total_tasks else 0

    return {
        "filename": filename,
        "totals": totals,
        "by_status": sorted(by_status.items(), key=lambda kv: (kv[1]["bucket"] != "complete", kv[0])),
        "unestimated": unestimated,
        "unmapped": unmapped,
        "columns": {
            "points": str(header[pts_i]) if pts_i is not None and pts_i < len(header) else "Column J",
            "status": str(header[st_i]) if st_i is not None and st_i < len(header) else "Column K",
        },
        "complete": complete,
        "incomplete": incomplete,
    }


def fmt(n):
    """2.0 -> '2', 2.5 -> '2.5'."""
    return f"{n:g}"
