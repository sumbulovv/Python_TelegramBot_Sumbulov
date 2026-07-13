from db import conn as db

class CalendarTgBot:
    def __init__(self):
        pass
    
    def register_user(self, user_id, name):
        with db.conn.cursor() as cursor:
            cursor.execute("INSERT INTO users (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (user_id, name))
            db.conn.commit()
            return cursor.rowcount > 0

    def is_user_registered(self, user_id):
        with db.conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM users WHERE id = %s;", (user_id,))
            return cursor.fetchone() is not None

    def create_event(self, name, date, time, details, user_id):
        with db.conn.cursor() as cursor:
            cursor.execute("INSERT INTO events (name, date, time, details, user_id) VALUES (%s, %s, %s, %s, %s) RETURNING id;", (name, date, time, details, user_id))
            event_id = cursor.fetchone()[0]
            db.conn.commit()
            return event_id
    
    def get_event(self, event_id, user_id):
        with db.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM events WHERE id = %s AND user_id = %s;", (event_id, user_id))
            row = cursor.fetchone()
            return self._row_to_event(row) if row else None

    def delete_event(self, event_id, user_id):
        with db.conn.cursor() as cursor:
            cursor.execute("DELETE FROM events WHERE id = %s AND user_id = %s;", (event_id, user_id))
            deleted = cursor.rowcount
            db.conn.commit()

            return deleted > 0
    
    def list_events(self, user_id):
        with db.conn.cursor() as cursor:
            cursor.execute("SELECT * FROM events WHERE user_id = %s ORDER BY id;", (user_id,))
            return [self._row_to_event(row) for row in cursor.fetchall()]
    
    def update_event(self, event_id, user_id, name=None, date=None, time=None, details=None):
        fields = []
        values = []

        if name is not None:
            fields.append("name = %s")
            values.append(name)

        if date is not None:
            fields.append("date = %s")
            values.append(date)

        if time is not None:
            fields.append("time = %s")
            values.append(time)

        if details is not None:
            fields.append("details = %s")
            values.append(details)

        if not fields:
            return False

        values.append(event_id)
        values.append(user_id)

        with db.conn.cursor() as cursor:
            cursor.execute(
                f"UPDATE events SET {', '.join(fields)} WHERE id = %s AND user_id = %s;",
                values
            )
            updated = cursor.rowcount
            db.conn.commit()

            return updated > 0
    
    @staticmethod
    def _row_to_event(row):
        event_id, name, date, time, details, user_id = row
        return {
            "id": event_id,
            "name": name,
            "date": date,
            "time": time,
            "details": details,
            "user_id": user_id
        }