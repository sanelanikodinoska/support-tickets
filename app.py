"""
Support Ticketing System — Databricks App backed by Lakebase (Postgres)
Day 1 Homework: Build a Lakebase-Powered AI Support App

Endpoints
---------
GET  /                              Serve the SPA frontend
GET  /healthz                       Health check
GET  /api/stats                     Ticket counts by status / priority
GET  /api/tickets                   List tickets (filter: status, category, priority)
POST /api/tickets                   Create a ticket
GET  /api/tickets/<id>              Get ticket + messages
PATCH /api/tickets/<id>             Update status / priority / category / title
DELETE /api/tickets/<id>            Delete ticket (cascades messages)
POST /api/tickets/<id>/messages     Add a message
DELETE /api/messages/<id>           Delete a single message
"""

import logging
import os

from flask import Flask, jsonify, render_template, request

import db
import lakebase

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ticketing-app")

app = Flask(__name__)

# ── Startup: ensure schema exists and seed sample data ───────────────────────

try:
    db.create_schema()
    db.seed_data()
    logger.info("Database initialised successfully.")
except Exception as exc:
    logger.error("Database initialisation failed: %s", exc)


# ── Global error handler ─────────────────────────────────────────────────────

@app.errorhandler(Exception)
def handle_exception(err):
    logger.exception("Unhandled exception")
    code = getattr(err, "code", 500)
    code = code if isinstance(code, int) else 500
    return jsonify({"error": str(err)}), code


# ── Health ────────────────────────────────────────────────────────────────────

@app.route("/healthz")
def healthz():
    return jsonify({"status": "ok"})


# ── Frontend ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    databricks_app_url = os.getenv("DATABRICKS_APP_URL", "").strip()
    return render_template("index.html", databricks_app_url=databricks_app_url)


# ── Stats ─────────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def get_stats():
    rows = lakebase.run_query("""
        SELECT
            COUNT(*)                                              AS total,
            COUNT(*) FILTER (WHERE status = 'open')              AS open,
            COUNT(*) FILTER (WHERE status = 'in_progress')       AS in_progress,
            COUNT(*) FILTER (WHERE status = 'resolved')          AS resolved,
            COUNT(*) FILTER (WHERE status = 'closed')            AS closed,
            COUNT(*) FILTER (WHERE priority = 'critical')        AS critical,
            COUNT(*) FILTER (WHERE priority = 'high')            AS high_priority
        FROM tickets
    """)
    return jsonify(rows[0] if rows else {})


# ── Tickets ───────────────────────────────────────────────────────────────────

@app.route("/api/tickets")
def list_tickets():
    status   = request.args.get("status",   "").strip()
    category = request.args.get("category", "").strip()
    priority = request.args.get("priority", "").strip()

    conditions, params = [], []

    if status and status in db.VALID_STATUSES:
        conditions.append("t.status = %s");   params.append(status)
    if category and category in db.VALID_CATEGORIES:
        conditions.append("t.category = %s"); params.append(category)
    if priority and priority in db.VALID_PRIORITIES:
        conditions.append("t.priority = %s"); params.append(priority)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    rows = lakebase.run_query(f"""
        SELECT
            t.ticket_id,
            t.title,
            t.description,
            t.status,
            t.priority,
            t.category,
            t.created_by,
            t.created_at,
            t.updated_at,
            COUNT(m.message_id) AS message_count
        FROM tickets t
        LEFT JOIN ticket_messages m USING (ticket_id)
        {where}
        GROUP BY t.ticket_id
        ORDER BY
            CASE t.priority
                WHEN 'critical' THEN 1
                WHEN 'high'     THEN 2
                WHEN 'medium'   THEN 3
                ELSE                 4
            END,
            t.updated_at DESC
    """, params or None)

    return jsonify(rows)


@app.route("/api/tickets/<int:ticket_id>")
def get_ticket(ticket_id):
    rows = lakebase.run_query("""
        SELECT t.*, COUNT(m.message_id) AS message_count
        FROM tickets t
        LEFT JOIN ticket_messages m USING (ticket_id)
        WHERE t.ticket_id = %s
        GROUP BY t.ticket_id
    """, (ticket_id,))

    if not rows:
        return jsonify({"error": "Ticket not found"}), 404

    ticket = rows[0]
    ticket["messages"] = lakebase.run_query("""
        SELECT message_id, ticket_id, message_text, author, created_at
        FROM ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at ASC
    """, (ticket_id,))

    return jsonify(ticket)


@app.route("/api/tickets", methods=["POST"])
def create_ticket():
    data = request.get_json(force=True) or {}

    title       = (data.get("title")       or "").strip()
    description = (data.get("description") or "").strip()
    created_by  = (data.get("created_by")  or "").strip()
    status      = (data.get("status")      or "open").strip()
    priority    = (data.get("priority")    or "medium").strip()
    category    = (data.get("category")    or "general").strip()

    errors = {}
    if not title:
        errors["title"] = "Title is required."
    elif len(title) > 200:
        errors["title"] = "Title must be 200 characters or fewer."
    if not created_by:
        errors["created_by"] = "Your name or email is required."
    if status not in db.VALID_STATUSES:
        errors["status"] = f"Choose from: {', '.join(sorted(db.VALID_STATUSES))}"
    if priority not in db.VALID_PRIORITIES:
        errors["priority"] = f"Choose from: {', '.join(sorted(db.VALID_PRIORITIES))}"
    if category not in db.VALID_CATEGORIES:
        errors["category"] = f"Choose from: {', '.join(sorted(db.VALID_CATEGORIES))}"

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    ticket = lakebase.run_write_returning("""
        INSERT INTO tickets (title, description, status, priority, category, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """, (title, description or None, status, priority, category, created_by))

    return jsonify(ticket), 201


@app.route("/api/tickets/<int:ticket_id>", methods=["PATCH"])
def update_ticket(ticket_id):
    data = request.get_json(force=True) or {}

    allowed, errors = {}, {}

    if "status" in data:
        s = (data["status"] or "").strip()
        if s not in db.VALID_STATUSES:
            errors["status"] = f"Invalid status. Choose from: {', '.join(sorted(db.VALID_STATUSES))}"
        else:
            allowed["status"] = s

    if "priority" in data:
        p = (data["priority"] or "").strip()
        if p not in db.VALID_PRIORITIES:
            errors["priority"] = f"Invalid priority. Choose from: {', '.join(sorted(db.VALID_PRIORITIES))}"
        else:
            allowed["priority"] = p

    if "category" in data:
        c = (data["category"] or "").strip()
        if c not in db.VALID_CATEGORIES:
            errors["category"] = f"Invalid category."
        else:
            allowed["category"] = c

    if "title" in data:
        t = (data["title"] or "").strip()
        if not t:
            errors["title"] = "Title cannot be empty."
        elif len(t) > 200:
            errors["title"] = "Title must be 200 characters or fewer."
        else:
            allowed["title"] = t

    if "description" in data:
        allowed["description"] = (data["description"] or "").strip() or None

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    if not allowed:
        return jsonify({"error": "No valid fields to update."}), 400

    set_clause = ", ".join(f"{k} = %s" for k in allowed)
    values     = list(allowed.values()) + [ticket_id]

    ticket = lakebase.run_write_returning(f"""
        UPDATE tickets
        SET {set_clause}, updated_at = now()
        WHERE ticket_id = %s
        RETURNING *
    """, values)

    if not ticket:
        return jsonify({"error": "Ticket not found"}), 404

    return jsonify(ticket)


@app.route("/api/tickets/<int:ticket_id>", methods=["DELETE"])
def delete_ticket(ticket_id):
    exists = lakebase.run_query(
        "SELECT ticket_id FROM tickets WHERE ticket_id = %s", (ticket_id,)
    )
    if not exists:
        return jsonify({"error": "Ticket not found"}), 404

    lakebase.run_write("DELETE FROM tickets WHERE ticket_id = %s", (ticket_id,))
    return jsonify({"deleted": ticket_id})


# ── Messages ──────────────────────────────────────────────────────────────────

@app.route("/api/tickets/<int:ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    exists = lakebase.run_query(
        "SELECT ticket_id FROM tickets WHERE ticket_id = %s", (ticket_id,)
    )
    if not exists:
        return jsonify({"error": "Ticket not found"}), 404

    data         = request.get_json(force=True) or {}
    message_text = (data.get("message_text") or "").strip()
    author       = (data.get("author")       or "").strip()

    errors = {}
    if not message_text:
        errors["message_text"] = "Message text is required."
    elif len(message_text) > 5000:
        errors["message_text"] = "Message must be 5 000 characters or fewer."
    if not author:
        errors["author"] = "Author name or email is required."

    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400

    message = lakebase.run_write_returning("""
        INSERT INTO ticket_messages (ticket_id, message_text, author)
        VALUES (%s, %s, %s)
        RETURNING *
    """, (ticket_id, message_text, author))

    # Bump ticket's updated_at so it sorts to the top
    lakebase.run_write(
        "UPDATE tickets SET updated_at = now() WHERE ticket_id = %s", (ticket_id,)
    )

    return jsonify(message), 201


@app.route("/api/messages/<int:message_id>", methods=["DELETE"])
def delete_message(message_id):
    exists = lakebase.run_query(
        "SELECT message_id FROM ticket_messages WHERE message_id = %s", (message_id,)
    )
    if not exists:
        return jsonify({"error": "Message not found"}), 404

    lakebase.run_write(
        "DELETE FROM ticket_messages WHERE message_id = %s", (message_id,)
    )
    return jsonify({"deleted": message_id})


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8000))
    app.run(debug=True, host=host, port=port)
