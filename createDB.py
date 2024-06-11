import sqlite3

# 连接到数据库，如果不存在则会创建一个名为 data.db 的数据库文件
conn = sqlite3.connect('data.db')
cursor = conn.cursor()

# 创建 users 表
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

# 创建 sessions 表
cursor.execute('''
CREATE TABLE IF NOT EXISTS sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    account TEXT,
    data TEXT,
    FOREIGN KEY (account) REFERENCES users (account) ON DELETE CASCADE ON UPDATE CASCADE
)
''')

# 创建 products 表
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

# 提交事务并关闭连接
conn.commit()
conn.close()

print("数据库和表已成功创建")
