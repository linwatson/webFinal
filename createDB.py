import sqlite3
from app import save_user_session

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
    price INTEGER,
    seller TEXT,
    quantity INTEGER,        
    FOREIGN KEY (seller) REFERENCES users (account) ON DELETE CASCADE ON UPDATE CASCADE
)
''')

account = "admin"
password = "admin"
member_name = "admin"
member_address = "admin'address"
member_email = "admin@gmail.com"
member_phone = "0912345678"

cursor.execute(
    """
    INSERT INTO users (account, password, member_name, member_address, member_email, member_phone)
    VALUES (?,?,?,?,?,?)
""",(account, password, member_name, member_address, member_email, member_phone))

products = {
    ("DHABG5-A900GIOA", "ACER Aspire 3 A315-35-P4CG 銀", "(N6000/8GB/512GB SSD/Win11/15.6吋) 效能筆電", "12900", "admin"),
    ("DHAFOD-1900HHONC", "ASUS 15.6吋效能筆電-午夜藍", "(i7-12700H/16G/512G/W11/FHD/15.6)", 22999, "admin"),
    ("DHABC1-A900GLD2T", "MSI微星 Bravo 15 C7VFK-200TW-SP1 黑", "(R5-7535HS/8G+8G/512G SSD/RTX4060 8G/W11/15.6)特仕筆電", 29900, "admin"),
    ("DHABC2-A900GJCY7", "MSI微星 Modern 15 H B13M-002TW-SP4 黑", "(i7-13700H/32G/1TB SSD/W11P/15.6)特仕筆電", 29500, "admin"),
}

cursor.executemany(
    """INSERT INTO products (product_id, name, description, price, seller)
    VALUES (?, ?, ?, ?, ?)""",products
)

conn.commit()
conn.close()

session_data = {
    'memberInfo': {
        'account': account,
        'password': password,
        'member_name': member_name,
        'member_address': member_address,
        'member_email': member_email,
        'member_phone': member_phone
    },
    'seller': {
        'Listings': [], # 上架商品
        'Pending_orders': [], # 待處理訂單
        'order_history': [] # 完成訂單
    }
}

save_user_session("admin", session_data)

print("數據庫與資料表已成功創建")
