import sqlite3
import datetime
from typing import Optional, List, Tuple, Dict, Any

DB_PATH = "shop.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0.0,
        created_at TEXT
    )
    """)

    # Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        display_order INTEGER DEFAULT 0
    )
    """)

    # Products table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id TEXT,
        name TEXT,
        description TEXT,
        price REAL,
        active INTEGER DEFAULT 1,
        FOREIGN KEY (category_id) REFERENCES categories(id)
    )
    """)

    # Stock table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER,
        account_data TEXT,
        status TEXT DEFAULT 'available',
        sold_to INTEGER,
        sold_at TEXT,
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    """)

    # Orders table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        product_name TEXT,
        account_data TEXT,
        price REAL,
        created_at TEXT
    )
    """)

    # Deposit Requests table for KHQR
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deposit_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        currency TEXT DEFAULT 'USD',
        qr_string TEXT,
        md5 TEXT,
        status TEXT DEFAULT 'pending',
        receipt_file_id TEXT,
        created_at TEXT
    )
    """)

    # Default categories seed
    categories_data = [
        ("gmail", "📧 Gmail Accounts", 1),
        ("facebook", "📘 Facebook Accounts", 2),
        ("other", "🌐 Other Accounts", 3),
    ]
    cursor.executemany("""
    INSERT OR IGNORE INTO categories (id, name, display_order)
    VALUES (?, ?, ?)
    """, categories_data)

    # Default sample products seed if empty
    cursor.execute("SELECT COUNT(*) as count FROM products")
    if cursor.fetchone()["count"] == 0:
        sample_products = [
            ("gmail", "Gmail Aged (Old 2021-2023)", "Old aged Gmail accounts with recovery email set. Good for ads & gaming.", 1.20),
            ("gmail", "Gmail Fresh (New accounts)", "Freshly created Gmail accounts with phone verified.", 0.50),
            ("gmail", "Gmail + 2FA Enabled", "Gmail accounts with 2FA security codes included.", 1.50),
            ("facebook", "Facebook Aged Profile (2FA)", "Aged Facebook account with 2FA code and profile filled.", 2.00),
            ("facebook", "Facebook Fresh (Cookie + Token)", "Fresh Facebook account with cookies and EAAB token.", 0.80),
            ("other", "TikTok / Instagram Accounts", "Social media accounts ready for marketing or personal use.", 1.00),
        ]
        cursor.executemany("""
        INSERT INTO products (category_id, name, description, price, active)
        VALUES (?, ?, ?, ?, 1)
        """, sample_products)

    conn.commit()
    conn.close()

# User operations
def get_or_create_user(user_id: int, username: str = "", first_name: str = "") -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row is None:
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        INSERT INTO users (user_id, username, first_name, balance, created_at)
        VALUES (?, ?, ?, 0.0, ?)
        """, (user_id, username or "", first_name or "", now))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
    else:
        # Update username/first_name if changed
        if row["username"] != username or row["first_name"] != first_name:
            cursor.execute("UPDATE users SET username = ?, first_name = ? WHERE user_id = ?", (username, first_name, user_id))
            conn.commit()
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
    res = dict(row)
    conn.close()
    return res

def get_user(user_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_balance(user_id: int, amount: float) -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row["balance"] if row else 0.0

def get_all_users() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

# Categories & Products
def get_categories() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY display_order ASC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_products_by_category(category_id: str) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, 
           (SELECT COUNT(*) FROM stock s WHERE s.product_id = p.id AND s.status = 'available') as stock_count
    FROM products p
    WHERE p.category_id = ? AND p.active = 1
    ORDER BY p.id ASC
    """, (category_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_product(product_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, 
           (SELECT COUNT(*) FROM stock s WHERE s.product_id = p.id AND s.status = 'available') as stock_count
    FROM products p
    WHERE p.id = ?
    """, (product_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_products() -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT p.*, c.name as category_name,
           (SELECT COUNT(*) FROM stock s WHERE s.product_id = p.id AND s.status = 'available') as stock_count
    FROM products p
    LEFT JOIN categories c ON p.category_id = c.id
    WHERE p.active = 1
    ORDER BY p.category_id, p.id
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_product(category_id: str, name: str, description: str, price: float) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO products (category_id, name, description, price, active)
    VALUES (?, ?, ?, ?, 1)
    """, (category_id, name, description, price))
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid

def update_product_price(product_id: int, new_price: float):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET price = ? WHERE id = ?", (new_price, product_id))
    conn.commit()
    conn.close()

def delete_product(product_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET active = 0 WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

# Stock Management
def add_stock(product_id: int, account_lines: List[str]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    valid_lines = [line.strip() for line in account_lines if line.strip()]
    if not valid_lines:
        conn.close()
        return 0

    data = [(product_id, line, 'available') for line in valid_lines]
    cursor.executemany("""
    INSERT INTO stock (product_id, account_data, status)
    VALUES (?, ?, ?)
    """, data)
    added_count = cursor.rowcount
    conn.commit()
    conn.close()
    return added_count

def get_stock_count(product_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM stock WHERE product_id = ? AND status = 'available'", (product_id,))
    row = cursor.fetchone()
    conn.close()
    return row["count"] if row else 0

# Purchase logic (Atomic)
def purchase_product(user_id: int, product_id: int) -> Tuple[bool, str, Optional[int]]:
    """
    Returns (success: bool, message_or_account_data: str, order_id: Optional[int])
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        
        # 1. Fetch user
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            conn.rollback()
            conn.close()
            return False, "User not found.", None
        
        # 2. Fetch product
        cursor.execute("SELECT * FROM products WHERE id = ? AND active = 1", (product_id,))
        product = cursor.fetchone()
        if not product:
            conn.rollback()
            conn.close()
            return False, "Product not found or inactive.", None
        
        price = product["price"]
        if user["balance"] < price:
            conn.rollback()
            conn.close()
            return False, "INSUFFICIENT_BALANCE", None
        
        # 3. Fetch 1 available stock
        cursor.execute("""
        SELECT * FROM stock 
        WHERE product_id = ? AND status = 'available' 
        ORDER BY id ASC LIMIT 1
        """, (product_id,))
        stock_item = cursor.fetchone()
        if not stock_item:
            conn.rollback()
            conn.close()
            return False, "OUT_OF_STOCK", None
        
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 4. Deduct balance
        cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (price, user_id))
        
        # 5. Mark stock as sold
        cursor.execute("""
        UPDATE stock 
        SET status = 'sold', sold_to = ?, sold_at = ? 
        WHERE id = ?
        """, (user_id, now, stock_item["id"]))
        
        # 6. Create order record
        cursor.execute("""
        INSERT INTO orders (user_id, product_id, product_name, account_data, price, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, product_id, product["name"], stock_item["account_data"], price, now))
        
        order_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return True, stock_item["account_data"], order_id

    except Exception as e:
        conn.rollback()
        conn.close()
        return False, str(e), None

# Orders
def get_user_orders(user_id: int, limit: int = 10) -> List[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT * FROM orders 
    WHERE user_id = ? 
    ORDER BY id DESC LIMIT ?
    """, (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_order(order_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

# Stats
def get_stats() -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as user_count FROM users")
    user_count = cursor.fetchone()["user_count"]

    cursor.execute("SELECT COUNT(*) as sold_count, COALESCE(SUM(price), 0.0) as total_revenue FROM orders")
    order_data = cursor.fetchone()
    sold_count = order_data["sold_count"]
    total_revenue = order_data["total_revenue"]

    cursor.execute("SELECT COUNT(*) as stock_available FROM stock WHERE status = 'available'")
    stock_available = cursor.fetchone()["stock_available"]

    conn.close()
    return {
        "user_count": user_count,
        "sold_count": sold_count,
        "total_revenue": total_revenue,
        "stock_available": stock_available
    }

# Deposit Requests (KHQR)
def create_deposit_request(user_id: int, amount: float, currency: str, qr_string: str, md5: str) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
    INSERT INTO deposit_requests (user_id, amount, currency, qr_string, md5, status, created_at)
    VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (user_id, amount, currency, qr_string, md5, now))
    conn.commit()
    dep_id = cursor.lastrowid
    conn.close()
    return dep_id

def get_deposit_request(deposit_id: int) -> Optional[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposit_requests WHERE id = ?", (deposit_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_deposit_receipt(deposit_id: int, file_id: str) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE deposit_requests SET receipt_file_id = ?, status = 'submitted' WHERE id = ?", (file_id, deposit_id))
    conn.commit()
    conn.close()
    return True

def approve_deposit(deposit_id: int) -> Tuple[bool, float, int, float]:
    """
    Approves a deposit request, credits user's balance, and marks status as 'approved'.
    Returns (success, new_balance, user_id, amount)
    """
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT * FROM deposit_requests WHERE id = ?", (deposit_id,))
        dep = cursor.fetchone()
        if not dep:
            conn.rollback()
            conn.close()
            return False, 0.0, 0, 0.0
        
        if dep["status"] == "approved":
            # Already approved
            cursor.execute("SELECT balance FROM users WHERE user_id = ?", (dep["user_id"],))
            u = cursor.fetchone()
            conn.rollback()
            conn.close()
            return False, u["balance"] if u else 0.0, dep["user_id"], dep["amount"]

        amount = dep["amount"]
        user_id = dep["user_id"]

        # Credit balance
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        cursor.execute("UPDATE deposit_requests SET status = 'approved' WHERE id = ?", (deposit_id,))
        
        cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        new_bal = cursor.fetchone()["balance"]
        
        conn.commit()
        conn.close()
        return True, new_bal, user_id, amount
    except Exception:
        conn.rollback()
        conn.close()
        return False, 0.0, 0, 0.0

def reject_deposit(deposit_id: int) -> Tuple[bool, int, float]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM deposit_requests WHERE id = ?", (deposit_id,))
    dep = cursor.fetchone()
    if not dep or dep["status"] == "approved":
        conn.close()
        return False, 0, 0.0
    cursor.execute("UPDATE deposit_requests SET status = 'rejected' WHERE id = ?", (deposit_id,))
    conn.commit()
    conn.close()
    return True, dep["user_id"], dep["amount"]

