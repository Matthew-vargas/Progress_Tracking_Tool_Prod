import os

from flask import Flask, render_template, request

from report import COMPLETE_STATUSES, INCOMPLETE_STATUSES, ReportError, build_report, fmt

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB upload cap
app.jinja_env.filters["pts"] = fmt


def _split(text, default):
    items = [s.strip() for s in (text or "").split(",") if s.strip()]
    return items or default


@app.route("/", methods=["GET", "POST"])
def index():
    ctx = {
        "complete_text": ", ".join(COMPLETE_STATUSES),
        "incomplete_text": ", ".join(INCOMPLETE_STATUSES),
        "report": None,
        "error": None,
    }
    if request.method == "POST":
        ctx["complete_text"] = request.form.get("complete", ctx["complete_text"])
        ctx["incomplete_text"] = request.form.get("incomplete", ctx["incomplete_text"])
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
                )
            except ReportError as e:
                ctx["error"] = str(e)
            except Exception as e:  # malformed file, etc.
                ctx["error"] = f"Couldn't read that file: {e}"
    return render_template("index.html", **ctx)


@app.errorhandler(413)
def too_large(_):
    return render_template("index.html", complete_text=", ".join(COMPLETE_STATUSES),
                           incomplete_text=", ".join(INCOMPLETE_STATUSES),
                           report=None, error="File is larger than 10 MB."), 413


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
