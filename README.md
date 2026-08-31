# Flight Availability Monitor

Single-user tool that monitors **one** flight search (route + date + passenger count) via the
[Duffel API](https://duffel.com/docs/api) and emails you when a matching offer appears or gets
cheaper. It never books anything — offer requests (searches) are free on Duffel.

- Flask + SQLite + APScheduler, one plain HTML page
- No auth, no accounts, one saved search at a time
- Duffel is the only data source (no scraping)

## Setup

```bash
git clone https://github.com/liorbelhassen/Flights-finder.git
cd Flights-finder
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then edit .env
python app.py             # http://127.0.0.1:5000
```

### Environment variables

Put these in `.env` in the repo root (gitignored; `.env.example` is the template). Real values are
never committed and are read at startup by `config.py`.

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `DUFFEL_API_KEY` | yes | — | Duffel access token, test tokens start with `duffel_test` |
| `CHECK_INTERVAL_MINUTES` | no | `15` | Background check interval |
| `SMTP_HOST` | yes for alerts | — | e.g. `smtp.gmail.com` or `smtp.sendgrid.net` |
| `SMTP_PORT` | no | `587` | `465` switches to implicit SSL |
| `SMTP_USERNAME` | yes for alerts | — | Gmail address, or `apikey` for SendGrid |
| `SMTP_PASSWORD` | yes for alerts | — | Gmail app password or SendGrid API key |
| `SMTP_FROM` | no | `SMTP_USERNAME` | From address |
| `SMTP_USE_TLS` | no | `true` | STARTTLS; ignored on port 465 |
| `DATABASE_PATH` | no | `flights.db` | SQLite file |
| `HOST` / `PORT` | no | `127.0.0.1` / `5000` | Web server bind |

## Usage

Open <http://127.0.0.1:5000> and fill in the form: origin/destination IATA codes, travel date,
passenger count, notify email, and an optional max price. Saving **replaces** the monitored search
and clears its alert history, so changing the monitored search just means submitting the form again.

The same page shows the current search and a log of recent checks (time, status, offers found,
alerts sent). "Check now" runs a check immediately; "Delete search" stops monitoring.

### Alerting and duplicate suppression

Each cycle posts to `/air/offer_requests`, keeps offers at or below `max_price` (if set), and emails
only offers whose Duffel offer ID has not been reported yet, plus previously reported offers whose
price has dropped. Reported offer IDs and prices live in the `seen_offers` table, so the same result
is never emailed twice. If the email fails, the offers are *not* recorded, so the alert is retried on
the next cycle. Duffel errors (including rate limits) are logged to the `checks` table and retried on
the next cycle — the app never crashes on them.

### Manual Duffel check

```bash
python scripts/test_duffel.py LHR JFK 2026-10-01 1
```

## Deploying to a free-tier host

On [Render](https://render.com): create a Web Service from this repo, build command
`pip install -r requirements.txt`, start command `gunicorn -w 1 'app:app' --preload` (add
`gunicorn` to `requirements.txt`) — a single worker matters, otherwise each worker runs its own
scheduler and duplicates emails. Set the same env vars in the Render dashboard plus
`DATABASE_PATH=/var/data/flights.db` with an attached disk, otherwise SQLite state is lost on
redeploy. Note that free instances sleep when idle, which pauses the scheduler; a paid instance or a
local run is more reliable for continuous monitoring.
