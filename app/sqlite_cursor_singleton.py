import sqlite3
from threading import Lock

'''
usage example:
db_singleton = SQLiteCursorSingleton('example.db')

cursor = db_singleton.get_cursor()

cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
db_singleton.commit()

db_singleton.close()
'''


class SQLiteCursorSingleton:
    _instance = None
    _lock = Lock()

    def __new__(cls, db_name, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls, *args, **kwargs)
                    cls._instance._configure_cursor(db_name)
        return cls._instance

    def _configure_cursor(self, db_name):
        self.connection = sqlite3.connect(db_name)
        self.cursor = self.connection.cursor()

    def get_cursor(self):
        return self.cursor

    def commit(self):
        self.connection.commit()

    def close(self):
        self.connection.close()
