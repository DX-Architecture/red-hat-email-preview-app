# Red Hat Email Preview App

Internal **Email on Acid** replacement for Digital Activation / DX Architecture.

Marketers send a test to an OpenShift testing alias. **Mailpit** catches it, a **Linux Playwright worker** captures browser screenshots, an optional **Windows Outlook worker** captures native Outlook, and results land in a **Streamlit** dashboard with **SQLite** history on a shared PVC.

```
Marketer → Testing Alias → Mailpit
                              ├─ Linux Pod + Playwright  ─┐
                              └─ Windows VM + Outlook   ─┼─ SQLite + PVC → Streamlit Route
```

## MVP scope (colleague tenant)

Stand this up in an existing OpenShift tenant before requesting a dedicated appcode/tenant.

| Component | Runs where | Status in this repo |
|-----------|------------|---------------------|
| Mailpit | OpenShift | Manifests ready |
| Linux Playwright worker | OpenShift (sidecar) | Ready |
| Streamlit dashboard | OpenShift Route | Ready |
| SQLite + PVC | Shared volume | Ready |
| Windows Outlook worker | External Windows VM | Script ready (needs Outlook + share/sync of `/data`) |

## Project layout

```
red-hat-email-preview-app/
├── README.md
├── Dockerfile
├── requirements.txt
├── config.py
├── database/
│   └── db.py
├── workers/
│   ├── linux_playwright_worker.py
│   └── windows_outlook_worker.py
├── app/
│   └── dashboard.py
└── k8s/
    ├── namespace.yaml
    ├── pvc.yaml
    ├── mailpit-deployment.yaml
    ├── app-deployment.yaml
    └── route.yaml
```

## Local smoke test

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Terminal 1 — Mailpit
docker run --rm -p 8025:8025 -p 1025:1025 axllent/mailpit

# Terminal 2 — Linux worker
export DATA_DIR=./data DB_PATH=./data/email_preview.db MAILPIT_API_URL=http://127.0.0.1:8025
python workers/linux_playwright_worker.py

# Terminal 3 — Dashboard
streamlit run app/dashboard.py

# Send a test
python - <<'PY'
import smtplib
from email.mime.text import MIMEText
msg = MIMEText("<h1>Hello from MVP</h1><p>Red Hat Email Preview</p>", "html")
msg["Subject"] = "MVP preview test"
msg["From"] = "marketer@redhat.com"
msg["To"] = "preview@localhost"
smtplib.SMTP("127.0.0.1", 1025).send_message(msg)
print("sent")
PY
```

Open http://localhost:8501 and http://localhost:8025 (Mailpit UI).

## OpenShift deploy (MVP)

1. Adjust namespace / image registry / storage class for your colleague’s tenant.
2. Build and push the image:

```bash
oc project email-preview   # or your existing project
oc new-build --name=email-preview-app --binary --strategy=docker
oc start-build email-preview-app --from-dir=. --follow
```

3. Apply manifests:

```bash
oc apply -f k8s/namespace.yaml   # skip if using an existing project
oc apply -f k8s/pvc.yaml
oc apply -f k8s/mailpit-deployment.yaml
oc apply -f k8s/app-deployment.yaml
oc apply -f k8s/route.yaml
oc get route email-preview-dashboard -n email-preview
```

4. Point the internal testing alias SMTP at the Mailpit service (`mailpit:1025` in-cluster, or expose SMTP via a LoadBalancer/NodePort if mail lands outside the cluster).

### Windows Outlook worker

Run `workers/windows_outlook_worker.py` on a Windows VM that can read/write the same `DATA_DIR` (SMB mount of the PVC, or sync). Install Outlook + `pywin32` + `Pillow` for native captures; without Outlook the worker falls back to a Playwright screenshot labeled `outlook/desktop` so demos still complete.

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATA_DIR` | `/data` | PVC mount for DB + images |
| `DB_PATH` | `/data/email_preview.db` | SQLite file |
| `MAILPIT_API_URL` | `http://mailpit:8025` | Mailpit HTTP API |
| `MAILPIT_POLL_SECONDS` | `10` | Linux worker poll interval |
| `WINDOWS_WORKER_POLL_SECONDS` | `15` | Outlook worker poll interval |

## Status values

- `pending` → queued  
- `processing` → Linux render in progress  
- `linux_complete` → browser shots done, waiting on Outlook  
- `complete` → Playwright + Outlook available  
- `error` → see `error_message` in the dashboard  

## Next steps after MVP

- Wire real SMTP alias / subdomain with IT  
- Dedicated OpenShift project + appcode  
- Harden Outlook worker (queued API instead of shared SQLite file locks)  
- Auth on the Streamlit Route (OAuth / SSO)
