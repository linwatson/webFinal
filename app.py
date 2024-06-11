import sqlite3
import re
import json
from flask import Flask, redirect, render_template, request, session, url_for

app = Flask(__name__)
app.secret_key = 'lectronic_commerce_platform'
app.templates_auto_reload = True
DB_NAME = "data.db"  # 設定資料庫名稱


def log_error(error):
    '''將發生的錯誤存檔'''
    with open('error.log', 'a') as f:
        f.write(str(error) + '\n')


def get_db_connection():
    '''獲取資料庫連接'''
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # 設置 row_factory
    conn.execute('PRAGMA foreign_keys = ON;')
    return conn


def get_user_session(account):
    '''從資料庫中獲取最新的 session 數據'''
    conn = get_db_connection()
    cursor = conn.cursor()
    # 選擇符合account的最新一筆數據
    cursor.execute("SELECT data FROM sessions WHERE account = ? ORDER BY session_id DESC LIMIT 1", (account,))
    session_data = cursor.fetchone()
    conn.close()
    
    if session_data and session_data['data']:
        return json.loads(session_data['data'])

    return None


def save_user_session(account, session_data):
    '''保存 session 數據到資料庫'''
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT OR REPLACE INTO sessions (account, data) VALUES (?, ?)", 
                       (account, json.dumps(session_data)))
        conn.commit()
    except Exception as e:
        log_error(e)
    finally:
        conn.close()


def get_products(prod_id_list):
    '''
    input: list of product IDs
    output: list of product dictionaries
    '''
    if not prod_id_list:
        return []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        placeholders = ', '.join(['?'] * len(prod_id_list))
        query = f'SELECT * FROM products WHERE product_id IN ({placeholders})'
        cursor.execute(query, prod_id_list)
        rows = cursor.fetchall()

        products = [
            {
                'id': row['product_id'],
                'name': row['name'],
                'description': row['description'],
                'price': row['price'],
                'seller': row['seller']
            }
            for row in rows
        ]

        return products
    except Exception as e:
        log_error(e)
        return []
    finally:
        conn and conn.close()


def calculate_total_price(products):
    return sum(product['price'] for product in products)


@app.route('/register', methods=['GET', 'POST'])
def register():
    '''註冊會員 註冊完成導向login'''
    if request.method == 'GET':
        return render_template('register.html')
    
    elif request.method == 'POST':
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            account = request.form.get('account')
            password = request.form.get('password')
            AGpassword = request.form.get('AGpassword')
            member_name = request.form.get('member_name')
            member_address = request.form.get('member_address')
            member_email = request.form.get('member_email')
            member_phone = request.form.get('member_phone')

            assert password == AGpassword, '密碼與確認密碼不相符!'
            assert re.match(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', member_email), '請輸入正確的Email!'
            assert re.match(r'^09\d{8}$', member_phone), '請輸入有效的手機號碼'
            
            # 將 member 資料寫入 member 資料表
            cursor.execute(
                "INSERT INTO users (account, password, member_name, member_address, member_email, member_phone) VALUES (?,?,?,?,?,?);",
                (account, password, member_name, member_address, member_email, member_phone)
            )
            conn.commit()


            # 初始化用戶 session
            session_data = {
                'memberInfo': {
                    'account': account,
                    'password': password,
                    'member_name': member_name,
                    'member_address': member_address,
                    'member_email': member_email,
                    'member_phone': member_phone
                },
                'customer': {
                    'cart': [], # 購物車
                    'order_history': [] # 已完成訂單
                },
                'seller': {
                    'Listings': [], # 上架商品
                    'Pending_orders': [], # 待處理訂單
                    'order_history': [] # 完成訂單
                }
            }
            
            save_user_session(account, session_data)
            session['account'] = account
            return redirect(url_for('login'))
            
        except AssertionError as e:
            log_error(e)
            return render_template('register.html', error=str(e))
        except Exception as e:
            log_error(e)
            return render_template('error.html'), 500
        finally:
            conn and conn.close()


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE account = ? AND password = ?", (account, password))
            results = cursor.fetchone()
            if results:
                session['account'] = results['account']
                return redirect(url_for('index'))
            else:
                error = '請輸入正確的帳號密碼'
                return render_template('login.html', error=error)
        except Exception as e:
            log_error(e)
            return render_template('error.html'), 500
        finally:
            conn and conn.close()
    return render_template('login.html')

@app.route('/myAccount', methods=['GET', 'POST'])
def myAccount():
    if 'account' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        account = session['account']
        cursor.execute("SELECT * FROM users WHERE account = ?", (account,))
        results = cursor.fetchone()
        return render_template('myAccount.html', rec=results)
    except Exception as e:
        log_error(e)
        return render_template('error.html'), 500
    finally:
        conn and conn.close()


@app.route('/editProfile', methods=['GET', 'POST'])
def editProfile():
    if 'account' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Enable foreign key support
        cursor.execute("PRAGMA foreign_keys = ON;")

        if request.method == 'POST':
            old_account = session['account']
            account = request.form.get('account')
            password = request.form.get('password')
            member_name = request.form.get('member_name')
            member_address = request.form.get('member_address')
            member_email = request.form.get('member_email')
            member_phone = request.form.get('member_phone')
            
            # Ensure account uniqueness (excluding current user)
            cursor.execute("SELECT * FROM users WHERE account = ? AND account != ?", (account, old_account))
            existing_user = cursor.fetchone()
            if existing_user:
                raise Exception(f"Account '{account}' already exists.")
            
            # Start transaction
            conn.execute('BEGIN')

            try:
                cursor.execute(
                    """
                    UPDATE users
                    SET password = ?, member_name = ?, member_address = ?, member_email = ?, member_phone = ?
                    WHERE account = ?
                    """, 
                    (password, member_name, member_address, member_email, member_phone, old_account)
                )
                # 如果需要更新 account，需要确保在其他表中同步更新
                # 假设原 account 为 old_account，新的 account 为 new_account
                #account = request.form.get('account')

                if old_account != account:
                    #print('Updating account...')
            
                    # 更新引用表（sessions 和 products）
                    
                    
                    # 最后更新主表（users）
                    cursor.execute(
                        "UPDATE users SET account = ? WHERE account = ?",
                        (account, old_account)
                    )
                    #print('Users table updated successfully')

                # Commit transaction
                conn.commit()

            except sqlite3.IntegrityError as e:
                log_error(e)
                conn.rollback()
                return render_template('error.html', error_message="A database integrity error occurred. Please try again."), 500
            
            except Exception as e:
                log_error(e)
                conn.rollback()
                return render_template('error.html', error_message=str(e)), 500

            # Update session data
            session_data = get_user_session(account)
            if session_data:
                session_data['memberInfo'].update({
                    'account': account,
                    'password': password,
                    'member_name': member_name,
                    'member_address': member_address,
                    'member_email': member_email,
                    'member_phone': member_phone
                })
                save_user_session(account, session_data)
                session.pop('account')
                session['account'] = account
                return redirect(url_for('myAccount'))

        cursor.execute("SELECT * FROM users WHERE account = ?", (session['account'],))
        results = cursor.fetchone()
        return render_template('editProfile.html', rec=results)
    
    except sqlite3.IntegrityError as e:
        log_error(e)
        return render_template('error.html', error_message="A database integrity error occurred. Please try again."), 500
    
    except Exception as e:
        log_error(e)
        return render_template('error.html', error_message=str(e)), 500
    
    finally:
        if conn:
            conn.close()


@app.route('/')
def index():
    if 'account' not in session:
        return redirect(url_for('login'))
    
    account = session['account']
    session_data = get_user_session(account)
    #print('in index session_data:',session_data)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products')
        rows = cursor.fetchall()
        products = [
            {
                'id': row['product_id'],
                'name': row['name'],
                'description': row['description'],
                'price': row['price'],
                'seller': row['seller']
            }
            for row in rows
        ]
        return render_template('index.html', products=products)
    except Exception as e:
        log_error(e)
        return render_template('error.html'), 500
    finally:
        conn and conn.close()


@app.route('/prod/<product_code>', methods=['GET', 'POST'])
def product(product_code):
    if request.method == 'POST':
        account = session.get('account')
        if not account:
            return redirect(url_for('login'))

        session_data = get_user_session(account)
        # 添加商品到購物車
        if product_code not in session_data['customer']['cart']:
            session_data['customer']['cart'].append(product_code)
            save_user_session(account, session_data)

        prod_id_list = session_data['customer']['cart']

        # 根據商品ID清單提取商品詳細信息
        products = get_products(prod_id_list)
        # 計算總價
        total_price = calculate_total_price(products)
        
        # 將購物車商品和總價傳遞給模板
        return render_template('cart.html', products=products, total_price=total_price)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_code,))
        datas = cursor.fetchone()
        return render_template('product.html', data=datas)
    except Exception as e:
        log_error(e)
        return render_template('error.html'), 500
    finally:
        conn and conn.close()


@app.route('/cart')
def cart():
    if 'account' not in session:
        return redirect(url_for('login'))
    
    account = session['account']
    session_data = get_user_session(account)

    # 提取購物車中所有商品的ID清單
    prod_id_list = session_data['customer']['cart']

    # 根據商品ID清單提取商品詳細信息
    products = get_products(prod_id_list)
    # 計算總價
    total_price = calculate_total_price(products)
    
    # 將購物車商品和總價傳遞給模板
    return render_template('cart.html', products=products, total_price=total_price)


@app.route('/logout')
def logout():
    session.pop('account', None)
    return redirect(url_for('index'))


@app.route('/purchaseComplete', methods=['GET', 'POST'])
def purchaseComplete():
    account = session.get('account')
    session_data = get_user_session(account)
    
    selected_products = request.form.getlist('selected_products')
    selected_sellers = request.form.getlist('selected_sellers')

    # 下單之後跑到賣家的待處理清單
    for product_id, seller in zip(selected_products, selected_sellers):
        seller_session = get_user_session(seller)
        if seller_session:
            seller_session['seller']['Pending_orders'].append({
                'product_id': product_id,
                'customer': account
            })
        save_user_session(seller, seller_session)
        #print('in purchase complete seller_session: ',seller_session)    

    # 更新買家購物車
    session_data['customer']['cart'] = [product_id for product_id in session_data['customer']['cart'] if str(product_id) not in selected_products]
    save_user_session(account, session_data)
    #print('in purchase complete buyer_session: ',get_user_session(account)) 
    return render_template('purchaseComplete.html')


@app.route('/orderHistory')
def orderHistory():
    account = session.get('account')
    session_data = get_user_session(account)
    
    products = get_products(session_data['customer']['order_history'])
    return render_template('orderHistory.html', products=products)


@app.route('/seller')
def seller():
    if 'account' not in session:
        return redirect(url_for('login'))

    conn = None
    try:
        seller = session['account']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE seller = ?', (seller,))
        products = cursor.fetchall()
        return render_template('seller.html', products=products)
    except Exception as e:
        log_error(e)
        return render_template('error.html'), 500
    finally:
        conn and conn.close()


@app.route('/publish', methods=['GET', 'POST'])
def publish():
    if request.method == 'POST':
        conn = None
        try:
            product_id = request.form.get('product_id')  # 確保接收到 product_id
            name = request.form.get('name')
            description = request.form.get('description')
            price = request.form.get('price')
            seller = session['account']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO products (product_id, name, description, price, seller) VALUES (?, ?, ?, ?, ?);",
                (product_id, name, description, price, seller)
            )
            conn.commit()

            return redirect(url_for('seller'))
        except Exception as e:
            log_error(e)
            return render_template('error.html'), 500
        finally:
            conn and conn.close()
    
    return render_template('publish.html')

@app.route('/sold_product')
def soldProduct():
    account = session['account']
    session_data = get_user_session(account)
    
    products = get_products(session_data['seller']['order_history'])
    return render_template('soldProduct.html', products=products)


@app.route('/pending_orders', methods=['GET', 'POST'])
def pendingOrders():
    #如果按出貨之後
    if request.method == 'POST':
        account = session['account']
        session_data = get_user_session(account)
        pending_orders = session_data['seller']['Pending_orders']
        #print('pending_orders: ',pending_orders)# 先看有啥訂單
        selected_products = request.form.getlist('selected_products')
        selected_customers = request.form.getlist('selected_customers')

        # 更新賣家待處理清單和訂單紀錄
        completed_orders = []
        for product_id in selected_products:
            for customer in selected_customers:
                for order in pending_orders:
                    if order['product_id'] == product_id and order['customer'] == customer:
                        completed_orders.append(order)
        
        # 更新卖家的待处理订单和订单记录
        session_data['seller']['Pending_orders'] = [order for order in pending_orders if order not in completed_orders]
        session_data['seller']['order_history'] += completed_orders
        save_user_session(account, session_data)

        # 更新买家的订单记录
        for order in completed_orders:
            customer_account = order['customer']
            customer_session = get_user_session(customer_account)
            customer_session['customer']['order_history'].append({'product_id': order['product_id'], 'seller': session['account']})
            save_user_session(customer_account, customer_session)
            print('customer_session: ',customer_session)
        
        pending_orders = session_data['seller'].get('Pending_orders', [])
        products = get_products([order['product_id'] for order in pending_orders])
        pending_customers = [order['customer'] for order in pending_orders]

        save_user_session(account, session_data)
        return render_template('pendingOrders.html', products=products, customers=pending_customers)

    account = session['account']
    session_data = get_user_session(account)
    #print('seller_session_data: ', session_data)
    pending_orders = session_data['seller'].get('Pending_orders', [])

    products = get_products([order['product_id'] for order in pending_orders])
    pending_customers = [order['customer'] for order in pending_orders]
    
    return render_template('pendingOrders.html', products=products, customers=pending_customers)


@app.route('/test')
def test():
    return render_template('test.html')
