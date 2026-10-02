import os

from flask import Flask, render_template, request

from report import (COMPLETE_STATUSES, INCOMPLETE_STATUSES, POINTS_COLUMN, STATUS_COLUMN,
                    ReportError, build_report, fmt)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload cap
app.jinja_env.filters["pts"] = fmt


def _split(text, default):
    items = [s.strip() for s in (text or "").split(",") if s.strip()]
    return items or default


def _defaults():
    return {
        "complete_text": ", ".join(COMPLETE_STATUSES),
        "incomplete_text": ", ".join(INCOMPLETE_STATUSES),
        "points_col": POINTS_COLUMN,
        "status_col": STATUS_COLUMN,
        "default_points_col": POINTS_COLUMN,
        "default_status_col": STATUS_COLUMN,
        "report": None,
        "error": None,
    }


@app.route("/", methods=["GET", "POST"])
def index():
    ctx = _defaults()
    if request.method == "POST":
        for field in ("complete_text", "incomplete_text", "points_col", "status_col"):
            ctx[field] = (request.form.get(field) or "").strip() or ctx[field]
        upload = request.files.get("file")
        if not upload or not upload.filename:
            ctx["error"] = "Choose a Jira export to upload."
        else:
            try:
                ctx["report"] = build_report(
                    upload.filename,
                    upload.read(),
                    complete=_split(ctx["complete_text"], COMPLETE_STATUSES),
                    incomplete=_split(ctx["incomplete_text"], INCOMPLETE_STATUSES),
                    points_col=ctx["points_col"],
                    status_col=ctx["status_col"],
                )
            except ReportError as e:
                ctx["error"] = str(e)
            except Exception as e:  # malformed file, etc.
                ctx["error"] = f"Couldn't read that file: {e}"
    return render_template("index.html", **ctx)


@app.errorhandler(413)
def too_large(_):
    ctx = _defaults()
    ctx["error"] = "File is larger than 10 MB."
    return render_template("index.html", **ctx), 413


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
