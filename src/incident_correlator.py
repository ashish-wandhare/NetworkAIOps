import sqlite3
from contextlib import closing
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_FILE = PROJECT_ROOT / "data" / "incidents.db"


def get_connection():
    """Open a SQLite connection and ensure required tables exist."""
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                device_id TEXT NOT NULL,
                issue TEXT NOT NULL,
                alert_count INTEGER NOT NULL DEFAULT 1,
                first_seen TEXT,
                last_seen TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN'
            )
        """)

        # Track each event processed for each incident.
        # Existing incident records and counts remain unchanged.
        connection.execute("""
            CREATE TABLE IF NOT EXISTS incident_alert_events (
                event_id TEXT NOT NULL,
                incident_id TEXT NOT NULL,
                PRIMARY KEY (event_id, incident_id)
            )
        """)

        connection.commit()
        return connection

    except Exception:
        connection.close()
        raise


def add_alert(event):
    """Store rule-based alerts without counting duplicate events twice."""
    issues = []

    if event.get("latency_ms", 0) > 100:
        issues.append("HIGH_LATENCY")

    if event.get("packet_loss_pct", 0) > 2:
        issues.append("HIGH_PACKET_LOSS")

    if event.get("interface_errors", 0) > 10:
        issues.append("HIGH_INTERFACE_ERRORS")

    device_id = str(event.get("device_id", "unknown"))
    timestamp = event.get("timestamp")
    event_id = event.get("event_id")

    updated_incidents = []

    # closing() ensures the connection is closed.
    # The inner connection context commits or rolls back transactions.
    with closing(get_connection()) as connection:
        with connection:
            for issue in issues:
                incident_id = f"{device_id}-{issue}"

                if event_id is not None:
                    # Register this event for this incident only once.
                    cursor = connection.execute("""
                        INSERT OR IGNORE INTO incident_alert_events (
                            event_id,
                            incident_id
                        )
                        VALUES (?, ?)
                    """, (str(event_id), incident_id))

                    if cursor.rowcount == 1:
                        # New event: create or increment the incident.
                        connection.execute("""
                            INSERT INTO incidents (
                                incident_id,
                                device_id,
                                issue,
                                alert_count,
                                first_seen,
                                last_seen,
                                status
                            )
                            VALUES (?, ?, ?, 1, ?, ?, 'OPEN')
                            ON CONFLICT(incident_id) DO UPDATE SET
                                alert_count = incidents.alert_count + 1,
                                last_seen = excluded.last_seen
                        """, (
                            incident_id,
                            device_id,
                            issue,
                            timestamp,
                            timestamp,
                        ))

                    # Duplicate event: do not increment the count.

                else:
                    # Preserve previous behavior for events without an ID.
                    connection.execute("""
                        INSERT INTO incidents (
                            incident_id,
                            device_id,
                            issue,
                            alert_count,
                            first_seen,
                            last_seen,
                            status
                        )
                        VALUES (?, ?, ?, 1, ?, ?, 'OPEN')
                        ON CONFLICT(incident_id) DO UPDATE SET
                            alert_count = incidents.alert_count + 1,
                            last_seen = excluded.last_seen
                    """, (
                        incident_id,
                        device_id,
                        issue,
                        timestamp,
                        timestamp,
                    ))

                row = connection.execute("""
                    SELECT *
                    FROM incidents
                    WHERE incident_id = ?
                """, (incident_id,)).fetchone()

                if row is not None:
                    updated_incidents.append(dict(row))

    return updated_incidents


def get_incidents():
    """Return all stored incidents, including records from previous runs."""
    with closing(get_connection()) as connection:
        with connection:
            rows = connection.execute("""
                SELECT *
                FROM incidents
                ORDER BY last_seen DESC, incident_id
            """).fetchall()

            return [dict(row) for row in rows]