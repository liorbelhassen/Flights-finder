"""Flight availability monitor: one saved search, polled on a schedule."""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for

import config
import db
import monitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "flight-monitor-local"  # only used for flash messages, single-user local app


@app.get("/")
def index():
    return render_template(
        "index.html",
        search=db.get_search(),
        checks=db.recent_checks(),
        interval=config.CHECK_INTERVAL_MINUTES,
        duffel_configured=bool(config.DUFFEL_API_KEY),
        smtp_configured=bool(config.SMTP_HOST),
    )


@app.post("/search")
def save_search():
    form = request.form
    try:
        origin = form["origin"].strip().upper()
        destination = form["destination"].strip().upper()
        departure_date = form["departure_date"].strip()
        passengers = int(form["passengers"])
        email = form["email"].strip()
        raw_max_price = form.get("max_price", "").strip()
        max_price = float(raw_max_price) if raw_max_price else None
    except (KeyError, ValueError):
        flash("Please fill in all required fields with valid values.")
        return redirect(url_for("index"))

    if len(origin) != 3 or len(destination) != 3 or not (origin.isalpha() and destination.isalpha()):
        flash("Origin and destination must be 3-letter IATA codes.")
        return redirect(url_for("index"))
    if passengers < 1 or passengers > 9:
        flash("Passengers must be between 1 and 9.")
        return redirect(url_for("index"))

    db.save_search(origin, destination, departure_date, passengers, email, max_price)
    flash("Search saved. Monitoring started; alert history was reset.")
    return redirect(url_for("index"))


@app.post("/check-now")
def check_now():
    result = monitor.check_once()
    flash(f"Check finished: {result['status']} — {result['detail']}")
    return redirect(url_for("index"))


@app.post("/delete")
def delete_search():
    db.delete_search()
    flash("Search deleted. Monitoring stopped.")
    return redirect(url_for("index"))


def _scheduled_check():
    try:
        monitor.check_once()
    except Exception:  # a crash here would kill the job, so log and continue
        logger.exception("Scheduled check raised an unexpected error")


def start_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(
        _scheduled_check,
        "interval",
        minutes=config.CHECK_INTERVAL_MINUTES,
        id="flight-check",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()
    logger.info("Scheduler started: checking every %s minute(s)", config.CHECK_INTERVAL_MINUTES)
    return scheduler


db.init()
if config.RUN_SCHEDULER:
    start_scheduler()

if __name__ == "__main__":
    app.run(host=config.HOST, port=config.PORT, use_reloader=False)
