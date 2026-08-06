"""
Database schema setup and seed data for the Support Ticketing System.
Called once at app startup — fully idempotent (safe to re-run).
"""

import random
import lakebase

# ── Allowed values (used by app.py for validation) ────────────────────────────

VALID_STATUSES   = {"open", "in_progress", "resolved", "closed"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}
VALID_CATEGORIES = {"general", "billing", "technical", "feature_request", "bug"}


# ── Schema ────────────────────────────────────────────────────────────────────

def create_schema() -> None:
    """Create tickets and ticket_messages tables if they don't already exist."""

    lakebase.run_write("""
        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id   SERIAL PRIMARY KEY,
            title       TEXT NOT NULL,
            description TEXT,
            status      TEXT NOT NULL DEFAULT 'open'
                        CHECK (status IN ('open','in_progress','resolved','closed')),
            priority    TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('low','medium','high','critical')),
            category    TEXT NOT NULL DEFAULT 'general'
                        CHECK (category IN ('general','billing','technical','feature_request','bug')),
            created_by  TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    lakebase.run_write("""
        CREATE TABLE IF NOT EXISTS ticket_messages (
            message_id   SERIAL PRIMARY KEY,
            ticket_id    INTEGER NOT NULL
                         REFERENCES tickets(ticket_id) ON DELETE CASCADE,
            message_text TEXT NOT NULL,
            author       TEXT NOT NULL,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # Enable full-row replication for Lakebase Change Data Feed (CDF)
    for table in ("tickets", "ticket_messages"):
        try:
            lakebase.run_write(f"ALTER TABLE {table} REPLICA IDENTITY FULL")
        except Exception:
            pass  # Already set — safe to ignore


# ── Seed data (100 tickets, ~250 messages) ────────────────────────────────────

_TITLES = [
    # Technical
    "Cannot connect to VPN from home office",
    "Application crashes on startup after update",
    "Password reset email never arrives",
    "Two-factor authentication not working",
    "Database connection timeout on dashboard",
    "Export to CSV produces empty file",
    "Search results not returning correct data",
    "File upload fails for files over 10 MB",
    "Browser extension conflicts with portal",
    "Mobile app freezes on Android 14",
    "SSO login loop — redirected back to login page",
    "API rate limit hit despite low request volume",
    "Notifications not sending to Slack channel",
    "Scheduled report not running at midnight",
    "WebSocket connection drops after 60 seconds",
    "LDAP sync fails with timeout error",
    "Print function produces blank page",
    "Dark mode toggle resets on page refresh",
    "Drag-and-drop upload broken in Firefox",
    "Session expires after 5 minutes of inactivity",
    # Billing
    "Invoice shows wrong tax rate for EU customers",
    "Annual subscription charged monthly by mistake",
    "Coupon code not applied at checkout",
    "Payment declined despite valid credit card",
    "Duplicate charge on 15 March invoice",
    "Refund not received after 14 business days",
    "Pro plan features locked after renewal",
    "Trial period ended 3 days early",
    "Currency shown in USD instead of EUR",
    "VAT number not reflected on invoice",
    "Billing address cannot be updated",
    "Auto-renewal turned itself back on",
    "Seat count billed for 20, only 15 users active",
    "Receipt email not arriving after payment",
    "Upgrade from Starter to Pro not applied",
    # Feature requests
    "Add dark mode to the web portal",
    "Allow bulk ticket assignment to an agent",
    "Export audit log to PDF",
    "Support for keyboard navigation throughout app",
    "Add time-tracking field on tickets",
    "Weekly summary email digest option",
    "Customisable ticket status labels",
    "Public-facing status page for incidents",
    "SLA timer visible on ticket list view",
    "Two-way email sync for ticket replies",
    "Zapier integration for ticket creation",
    "Saved filter presets for ticket list",
    "Allow merging of duplicate tickets",
    "Markdown support in ticket descriptions",
    "Rich-text editor for message composer",
    # Bugs
    "Ticket count on dashboard shows -1",
    "Sorting by date reverses on second click",
    "Pagination jumps to page 1 on status change",
    "Avatar image not loading after profile update",
    "Edit ticket form clears description on save",
    "Delete button visible to read-only users",
    "Duplicate email notification sent on every update",
    "Filter state lost on browser back navigation",
    "Priority badge missing on mobile view",
    "Column widths reset after table sort",
    "Search box loses focus after each keystroke",
    "Time zone displayed as UTC for all users",
    "Checkbox state not persisted on page refresh",
    "Copy-to-clipboard broken in Safari 17",
    "Graph tooltip shows wrong data point",
    # General
    "Request for onboarding documentation",
    "Team account access for new hire",
    "Data retention policy clarification",
    "Request to increase API rate limits",
    "How to transfer account ownership",
    "Custom domain setup assistance needed",
    "Request for GDPR data export",
    "IP allowlist configuration help",
    "Permissions not applying to sub-team",
    "Webhook URL not receiving events",
    "How to set up SAML SSO",
    "Question about SLA guarantees in contract",
    "New team members need admin access",
    "Help migrating data from legacy system",
    "SCIM provisioning failing with 400 error",
    # Mixed additional
    "Integration with HubSpot CRM broken",
    "Performance degradation on large datasets",
    "Audit log missing entries from last week",
    "Custom report template not saving",
    "Role-based access not enforced on API",
    "Email domain whitelist not working",
    "Cannot deactivate archived user account",
    "Widget embed code produces CORS error",
    "CSV import skips rows with special characters",
    "Timezone mismatch between app and reports",
    "Comment mentions (@user) not triggering alert",
    "Asset upload limit should be 50 MB not 10 MB",
    "OAuth app approval request for internal tool",
    "Monthly usage report shows incorrect team",
    "On-call schedule not syncing with PagerDuty",
]

_DESCRIPTIONS = [
    "Started experiencing this after the latest platform update. Reproducible 100% of the time on my machine.",
    "This is blocking multiple team members. We need a fix or workaround as soon as possible.",
    "Intermittent issue — happens roughly 30% of the time, especially under heavy load.",
    "Affecting our entire department. Please prioritise.",
    "Noticed this after migrating to the new workspace. May be a configuration issue.",
    "Steps to reproduce: log in → navigate to settings → trigger the action — error appears.",
    "Our client deadline is next week. This is urgent.",
    "Low severity but consistently annoying. Would appreciate a permanent fix.",
    "Worked fine until last Tuesday. No changes were made on our end.",
    "Attaching screenshots and logs in follow-up messages.",
    None,  # some tickets have no description
    None,
    None,
]

_USERS = [
    "alice.wang@example.com",
    "bob.jones@example.com",
    "carlos.ruiz@example.com",
    "diana.chen@example.com",
    "evan.miller@example.com",
    "fatima.hassan@example.com",
    "george.patel@example.com",
    "hannah.kim@example.com",
    "ivan.novak@example.com",
    "julia.santos@example.com",
    "kevin.osei@example.com",
    "lena.schmidt@example.com",
    "marco.ferrari@example.com",
    "nadia.popov@example.com",
    "omar.ali@example.com",
    "priya.sharma@example.com",
    "quinn.foster@example.com",
    "rachel.green@example.com",
    "stefan.kowalski@example.com",
    "tina.yamamoto@example.com",
]

_SUPPORT_AGENTS = [
    "support.team@example.com",
    "help@example.com",
    "tier2.support@example.com",
]

_OPENER_MESSAGES = [
    "I've been experiencing this issue since yesterday morning. Please advise.",
    "This is affecting my entire workflow. Urgently need a fix.",
    "Tried the usual troubleshooting steps — clearing cache, restarting — no luck.",
    "Can you please look into this? It's been happening for a few days now.",
    "This was working fine last week. Something seems to have changed on your end.",
    "Reproducible every time. Happy to share a screen recording if that helps.",
    "My whole team is blocked by this. Please prioritise.",
    "Just noticed this today after logging in. Never happened before.",
    "I've raised this before (different ticket) but the issue has returned.",
    "Happy to provide more details or logs if needed — just let me know what format.",
    "This is preventing us from completing a client deliverable due this Friday.",
    "Low priority but would appreciate a fix when you have capacity.",
    "Flagging this as I couldn't find an answer in the docs.",
    "Noticed this after the last update was deployed. Possibly a regression?",
    "Can someone please take a look? We've been waiting 3 days.",
]

_FOLLOW_UP_MESSAGES = [
    "Still waiting for an update on this. Any progress?",
    "I tried the suggestion from your last response — same result unfortunately.",
    "This has now escalated — two more team members are affected.",
    "Attaching the error log for your reference: [ERROR] NullPointerException at line 342.",
    "The issue went away briefly but returned this morning.",
    "Just to confirm: this is happening on Chrome 124, macOS Sonoma.",
    "Any ETA on a fix? We have a product demo next week.",
    "I've opened a second ticket for a related issue (#related).",
    "Thanks for looking into this — please keep me posted.",
    "Happy to jump on a call if that speeds things up.",
]

_AGENT_REPLIES = [
    "Thank you for reaching out. I've escalated this to our engineering team.",
    "We've reproduced the issue internally. A fix is being prepared.",
    "This appears to be related to a recent deployment. We're reverting and will update you.",
    "Could you please provide your account ID and the exact error message?",
    "I've checked your account and everything looks correct on our side. Can you try incognito mode?",
    "Our team is aware of this and it's scheduled for the next release.",
    "This is a known issue. The workaround is to clear site data and log back in.",
    "I've applied a manual fix to your account. Please try again and let me know.",
    "Marking this as resolved. Please reopen if the issue persists.",
    "This has been escalated to Tier 2 support. You'll hear from them within 24 hours.",
]


def seed_data() -> None:
    """Insert 100 sample tickets (~250 messages) if the tables are empty."""

    count = lakebase.run_query("SELECT COUNT(*) AS cnt FROM tickets")[0]["cnt"]
    if count > 0:
        return  # Already seeded — skip

    rng = random.Random(42)  # fixed seed for reproducibility

    statuses   = list(VALID_STATUSES)
    priorities = list(VALID_PRIORITIES)
    categories = list(VALID_CATEGORIES)

    # Weight distributions to make the dataset realistic
    status_weights   = [0.40, 0.25, 0.25, 0.10]  # open, in_progress, resolved, closed
    priority_weights = [0.15, 0.40, 0.30, 0.15]  # low, medium, high, critical
    category_map = {
        "technical":       _TITLES[0:20],
        "billing":         _TITLES[20:35],
        "feature_request": _TITLES[35:50],
        "bug":             _TITLES[50:65],
        "general":         _TITLES[65:],
    }

    # Build category list weighted by how many titles exist per category
    cat_pool = []
    for cat, titles in category_map.items():
        cat_pool.extend([cat] * len(titles))

    used_titles: set = set()

    with lakebase.get_connection() as conn:
        with conn.cursor() as cur:

            for i in range(100):
                # Pick category then a unique title from that category
                category = rng.choice(cat_pool)
                available = [t for t in category_map[category] if t not in used_titles]
                if not available:
                    available = category_map[category]  # allow reuse if exhausted
                title = rng.choice(available)
                used_titles.add(title)

                status   = rng.choices(statuses,   weights=status_weights)[0]
                priority = rng.choices(priorities, weights=priority_weights)[0]
                description = rng.choice(_DESCRIPTIONS)
                created_by  = rng.choice(_USERS)

                cur.execute("""
                    INSERT INTO tickets
                        (title, description, status, priority, category, created_by,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s,
                            now() - (interval '1 day' * %s),
                            now() - (interval '1 hour' * %s))
                    RETURNING ticket_id
                """, (
                    title, description, status, priority, category, created_by,
                    rng.randint(1, 60),   # created 1-60 days ago
                    rng.randint(0, 48),   # updated 0-48 hours ago
                ))
                ticket_id = cur.fetchone()["ticket_id"]

                # Insert 2–4 messages per ticket
                num_messages = rng.randint(2, 4)
                opener = rng.choice(_OPENER_MESSAGES)
                cur.execute("""
                    INSERT INTO ticket_messages (ticket_id, message_text, author, created_at)
                    VALUES (%s, %s, %s, now() - (interval '1 day' * %s))
                """, (ticket_id, opener, created_by, rng.randint(1, 60)))

                # Support agent reply
                agent_reply = rng.choice(_AGENT_REPLIES)
                agent = rng.choice(_SUPPORT_AGENTS)
                cur.execute("""
                    INSERT INTO ticket_messages (ticket_id, message_text, author, created_at)
                    VALUES (%s, %s, %s, now() - (interval '1 day' * %s))
                """, (ticket_id, agent_reply, agent, rng.randint(0, 30)))

                # Optional follow-ups (0–2 more)
                for _ in range(num_messages - 2):
                    followup = rng.choice(_FOLLOW_UP_MESSAGES + _AGENT_REPLIES)
                    author = rng.choice([created_by, agent])
                    cur.execute("""
                        INSERT INTO ticket_messages (ticket_id, message_text, author, created_at)
                        VALUES (%s, %s, %s, now() - (interval '1 hour' * %s))
                    """, (ticket_id, followup, author, rng.randint(0, 72)))

            conn.commit()
