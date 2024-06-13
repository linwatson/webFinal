import sqlite3

conn = sqlite3.connect('data.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    member_name TEXT,
    member_address TEXT,
    member_email TEXT,
    member_phone TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT,
    data TEXT,
    FOREIGN KEY (account) REFERENCES users (account) ON DELETE CASCADE ON UPDATE CASCADE
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    price REAL,
    seller TEXT,
    FOREIGN KEY (seller) REFERENCES users (account) ON DELETE CASCADE ON UPDATE CASCADE
)
''')

conn.commit()
conn.close()

print("數據庫與資料表已成功創建")
