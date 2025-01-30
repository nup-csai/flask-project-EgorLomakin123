import sqlite3

def create_db():
    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        contact TEXT NOT NULL,
        avatar_id INTEGER,
        FOREIGN KEY (avatar_id) REFERENCES images (id)
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS lots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        author_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        category INTEGER NOT NULL,
        weight INTEGER NOT NULL,
        active INTEGER NOT NULL,
        FOREIGN KEY (category) REFERENCES categories (id),
        FOREIGN KEY (author_id) REFERENCES users (id)
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT NOT NULL
    )
    """)


    cursor.execute("""
    CREATE TABLE IF NOT EXISTS img_to_lot (
        lot_id INTEGER NOT NULL,
        img_id INTEGER NOT NULL,
        PRIMARY KEY (lot_id, img_id),
        FOREIGN KEY (lot_id) REFERENCES lots (id) ON DELETE CASCADE,
        FOREIGN KEY (img_id) REFERENCES images (id) ON DELETE CASCADE
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)
    connection.commit()

    cursor.execute("""
        INSERT INTO images (path) Values (?)
        """, ("default_avatar.png", ))
    # 0-package or 1-envelope
    cursor.execute(""" INSERT INTO categories (name) Values (?)""", ("package",))
    connection.commit()
    cursor.execute(""" INSERT INTO categories (name) Values (?)""", ("envelope",))
    connection.commit()
    connection.close()

if __name__ == "__main__":
    create_db()