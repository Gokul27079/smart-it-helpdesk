import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class Database:
    def __init__(self, path):
        self.path = str(path)

    @contextmanager
    def connection(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self):
        with self.connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                user_name TEXT NOT NULL,
                user_email TEXT NOT NULL,
                department TEXT NOT NULL,
                attachment_name TEXT,
                category TEXT NOT NULL,
                confidence REAL NOT NULL,
                classification_explanation TEXT,
                detected_keywords TEXT,
                priority TEXT NOT NULL,
                priority_reason TEXT,
                recommended_team TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS ticket_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                timestamp TEXT NOT NULL,
                FOREIGN KEY(ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_tickets_category ON tickets(category);
            CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);
            """)

    def _ticket(self, row):
        return dict(row) if row else None

    def next_ticket_id(self, conn):
        row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS n FROM tickets").fetchone()
        return f"TKT-{row['n']:05d}"

    def create_ticket(self, data):
        now = utc_now()
        with self.connection() as conn:
            ticket_id = self.next_ticket_id(conn)
            cur = conn.execute("""INSERT INTO tickets
                (ticket_id,title,description,user_name,user_email,department,attachment_name,
                 category,confidence,classification_explanation,detected_keywords,priority,
                 priority_reason,recommended_team,status,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                ticket_id, data['title'], data['description'], data['user_name'], data['user_email'],
                data['department'], data.get('attachment_name'), data['category'], data['confidence'],
                data.get('classification_explanation', ''), data.get('detected_keywords', ''),
                data['priority'], data.get('priority_reason', ''), data['recommended_team'],
                'Open', now, now))
            conn.execute("INSERT INTO ticket_logs (ticket_id, action, new_status, timestamp) VALUES (?,?,?,?)",
                         (cur.lastrowid, 'Ticket created', 'Open', now))
            return self.get_ticket(cur.lastrowid, conn=conn)

    def get_ticket(self, identifier, conn=None):
        own = conn is None
        ctx = self.connection() if own else None
        if own:
            conn = ctx.__enter__()
        try:
            row = conn.execute("SELECT * FROM tickets WHERE id = ? OR ticket_id = ?", (identifier, str(identifier))).fetchone()
            return self._ticket(row)
        finally:
            if own:
                ctx.__exit__(None, None, None)

    def list_tickets(self, filters=None):
        filters = filters or {}
        clauses, params = [], []
        if filters.get('q'):
            q = f"%{filters['q']}%"
            clauses.append("(ticket_id LIKE ? OR title LIKE ? OR description LIKE ? OR user_name LIKE ?)")
            params.extend([q, q, q, q])
        for field in ('category', 'priority', 'status', 'department'):
            if filters.get(field):
                clauses.append(f"{field} = ?")
                params.append(filters[field])
        order = "ASC" if filters.get('sort') == 'oldest' else "DESC"
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        with self.connection() as conn:
            rows = conn.execute(f"SELECT * FROM tickets{where} ORDER BY created_at {order}", params).fetchall()
            return [self._ticket(r) for r in rows]

    def update_status(self, identifier, status):
        now = utc_now()
        with self.connection() as conn:
            row = conn.execute("SELECT * FROM tickets WHERE id = ? OR ticket_id = ?", (identifier, str(identifier))).fetchone()
            if not row:
                return None
            old = row['status']
            conn.execute("UPDATE tickets SET status = ?, updated_at = ? WHERE id = ?", (status, now, row['id']))
            if old != status:
                conn.execute("INSERT INTO ticket_logs (ticket_id, action, old_status, new_status, timestamp) VALUES (?,?,?,?,?)",
                             (row['id'], 'Status updated', old, status, now))
            return self.get_ticket(row['id'], conn=conn)

    def delete_ticket(self, identifier):
        with self.connection() as conn:
            cur = conn.execute("DELETE FROM tickets WHERE id = ? OR ticket_id = ?", (identifier, str(identifier)))
            return cur.rowcount > 0

    def logs(self, identifier):
        ticket = self.get_ticket(identifier)
        if not ticket:
            return []
        with self.connection() as conn:
            rows = conn.execute("SELECT * FROM ticket_logs WHERE ticket_id = ? ORDER BY timestamp DESC", (ticket['id'],)).fetchall()
            return [self._ticket(r) for r in rows]

    def stats(self):
        with self.connection() as conn:
            total = conn.execute("SELECT COUNT(*) n FROM tickets").fetchone()['n']
            def counts(field):
                return {r[field]: r['n'] for r in conn.execute(f"SELECT {field}, COUNT(*) n FROM tickets GROUP BY {field}").fetchall()}
            return {'total': total, 'status': counts('status'), 'priority': counts('priority'), 'category': counts('category'),
                    'ai_classified': conn.execute("SELECT COUNT(*) n FROM tickets WHERE confidence >= 0.6").fetchone()['n']}
