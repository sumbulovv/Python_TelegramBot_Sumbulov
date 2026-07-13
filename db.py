import psycopg2

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(
            host="localhost",
            database="calendar",
            user="calendar",
            password="calendar"
        )
        self.cursor = self.conn.cursor()
        self.create_table()

    def create_table(self):
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id serial PRIMARY KEY,
            name text NOT NULL,
            date date NOT NULL,
            time time NOT NULL,
            details text
        );
        """)
        self.conn.commit()

    def close(self):
        self.cursor.close()
        self.conn.close()
        
conn = Database()