# Jira Progress Report

Small Flask tool: upload a Jira filter export (.csv or .xlsx) and get four numbers:
Story Points Completed / Incomplete and Tasks Completed / Incomplete. Nothing is saved;
the file is read in memory and thrown away after the page renders.

## Run locally (Windows / PowerShell)
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python app.py        # http://localhost:5000

## Deploy on Render (free tier)
`render.yaml` defines the service, so Render fills in the settings for you.

1. Push this folder to a GitHub repo (render.yaml at the repo root).
2. In Render: New > Blueprint, pick the repo, and click Apply.
   (Or New > Web Service and enter the settings below by hand.)
3. Open the `.onrender.com` URL once the build finishes.

Settings if you create the service by hand:
- Runtime: Python 3 (version pinned to 3.12 by `.python-version`)
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 60`
- Instance type: Free
- No environment variables and no database needed.

Free tier note: the service sleeps after about 15 minutes idle, so the first
page load after a break takes about 30–60 seconds. Nothing is lost when it sleeps,
because nothing is stored.

## How it counts
- Columns: finds "Custom field (Story point estimate)" and "Status" by header name,
  falling back to columns J and K.
- Complete: QA Passed, Deployed To Production
- Incomplete: To Do, In Progress, Dev to Test, QA To Test, REVISION
  (both lists can be edited on the page under "Status mapping"; matching ignores case)
- Tickets with no story points still count as tasks, with 0 points, and are listed.
- Tickets whose status is in neither list are left out of the totals and listed,
  so a new Jira status never gets counted without you seeing it.
