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

        # 使用字典來處理重複的product_id
        product_dict = {}
        for row in rows:
            product = {
                'id': row['product_id'],
                'name': row['name'],
                'description': row['description'],
                'price': row['price'],
                'quantity': row['quantity'],
                'seller': row['seller']
            }
            if row['product_id'] in product_dict:
                product_dict[row['product_id']].append(product)
            else:
                product_dict[row['product_id']] = [product]

        # 生成產品列表，保持輸入ID列表的順序和重複項
        products = [product for prod_id in prod_id_list for product in product_dict.get(prod_id, [])]

        return products
    except Exception as e:
        log_error(e)
        return []
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
            user_type = '會員'

            assert password == AGpassword, '密碼與確認密碼不相符!'
            assert re.match(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', member_email), '請輸入正確的Email!'
            assert re.match(r'^09\d{8}$', member_phone), '請輸入有效的手機號碼'
            
            cursor.execute("SELECT * FROM users WHERE account = ?", (account,))
            existing_user = cursor.fetchone()
            if existing_user:
                raise AssertionError (f"Account '{account}' already exists.")
                
            else:
                # 將 member 資料寫入 member 資料表
                cursor.execute(
                    "INSERT INTO users (account, password, member_name, member_address, member_email, member_phone, user_type) VALUES (?,?,?,?,?,?,?);",
                    (account, password, member_name, member_address, member_email, member_phone, user_type)
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
                        'member_phone': member_phone,
                        'user_type': user_type
                    },
                    'customer': {
                        'cart': [], # 購物車
                        'order_history': [] # 已完成訂單
                    }
                }
                
                save_user_session(account, session_data)
                session['account'] = account
                session['user_type'] = user_type
                return redirect(url_for('login'))
            
        except AssertionError as e:
            log_error(e)
            return render_template('register.html', error=str(e))
        
        except Exception as e:
            log_error(e)
            return render_template('error.html', user_type=session['user_type']), 500
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
            if results and results['user_type'] == '會員':
                session['account'] = results['account']
                session['user_type'] = results['user_type']
                return redirect(url_for('index'))
            else:
                error = '請輸入正確的會員帳號密碼'
                return render_template('login.html', error=error)
        except Exception as e:
            log_error(e)
            return render_template('error.html', user_type=session['user_type']), 500
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
        return render_template('error.html', user_type=session['user_type']), 500
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

        cursor.execute("PRAGMA foreign_keys = ON;")
        enter = dict()
        if request.method == 'POST':
            old_account = session['account']
            account = request.form.get('account')
            password = request.form.get('password')
            member_name = request.form.get('member_name')
            member_address = request.form.get('member_address')
            member_email = request.form.get('member_email')
            member_phone = request.form.get('member_phone')


            enter = {
                'account': '',
                'password': password,
                'member_name': member_name,
                'member_address': member_address,
                'member_email': member_email,
                'member_phone': member_phone,
            }
            
            assert re.match(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', member_email), '請輸入正確的Email!'
            assert re.match(r'^09\d{8}$', member_phone), '請輸入有效的手機號碼'
            
            cursor.execute("SELECT * FROM users WHERE account = ? AND account != ?", (account, old_account))
            existing_user = cursor.fetchone()
            if existing_user:
                raise AssertionError (f"Account '{account}' already exists.")
            
            else:
                try:
                    conn.execute('BEGIN')
                    cursor.execute(
                        """
                        UPDATE users
                        SET password = ?, member_name = ?, member_address = ?, member_email = ?, member_phone = ?
                        WHERE account = ?
                        """, 
                        (password, member_name, member_address, member_email, member_phone, old_account)
                    )

                    if old_account != account:
                        cursor.execute(
                            "UPDATE users SET account = ? WHERE account = ?",
                            (account, old_account)
                        )

                    conn.commit()

                except sqlite3.IntegrityError as e:
                    log_error(e)
                    conn.rollback()
                    return render_template('error.html', user_type=session['user_type'], error_message="A database integrity error occurred. Please try again."), 500

                except Exception as e:
                    log_error(e)
                    conn.rollback()
                    return render_template('error.html', user_type=session['user_type'], error_message=str(e)), 500

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
        return render_template('error.html', user_type=session['user_type'], error_message="A database integrity error occurred. Please try again."), 500
    
    except AssertionError as e:
        log_error(e)
        return render_template('editProfile.html', error=str(e),rec=enter)
    
    except Exception as e:
        log_error(e)
        return render_template('error.html', user_type=session['user_type'], error_message=str(e)), 500
    
    finally:
        if conn:
            conn.close()


@app.route('/')
def index():
    if 'account' not in session:
        return redirect(url_for('login'))
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
                'quantity': row['quantity'],
                'seller': row['seller']
            }
            for row in rows
        ]
        return render_template('index.html', products=products)
    except Exception as e:
        log_error(e)
        return render_template('error.html', user_type=session['user_type']), 500
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
        action = request.form.get('action')
        if action == 'purchase':
            # 立即購買
            # 根據商品ID清單提取商品詳細信息
            products = get_products(prod_id_list)
            # 計算總價
            return redirect(url_for('cart'))
        
        elif action == 'add_to_cart':
            # 加入購物車
            return redirect(url_for('index'))

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_code,))
        datas = cursor.fetchone()
        return render_template('product.html', data=datas)
    except Exception as e:
        log_error(e)
        return render_template('error.html', user_type=session['user_type']), 500
    finally:
        conn and conn.close()

def calculate_total_price(products):
    return sum(product['price'] for product in products)

@app.route('/cart', methods=['GET','POST'])
def cart():
    if 'account' not in session:
        return redirect(url_for('login'))
    
    account = session['account']
    session_data = get_user_session(account)
    print('cart: ', session_data['customer']['cart'])
    if request.method == 'POST':
        # 获取发送过来的产品 ID
        product_id = request.form.get('remove_product_id')
        
        session_data['customer']['cart'].remove(product_id)
        save_user_session(account, session_data)
        

        print("要移除的产品 ID:", product_id)
        print('cart: ', session_data['customer']['cart'])

        prod_id_list = session_data['customer']['cart']

        # 根據商品ID清單提取商品詳細信息
        products = get_products(prod_id_list)
        print(products)
        print('xd')
        return render_template('cart.html', products=products)


    # 提取購物車中所有商品的ID清單
    prod_id_list = session_data['customer']['cart']

    # 根據商品ID清單提取商品詳細信息
    products = get_products(prod_id_list)
    # 計算總價
    msg = request.args.get('msg')
    
    if msg is not None:
        return render_template('cart.html', products=products, msg=msg)
    else:
        return render_template('cart.html', products=products)


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

    selected_quantities = []

    for product_id in selected_products:
        quantity = request.form.get(f'quantity_{product_id}')
        selected_quantities.append(quantity)
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # 下單之後跑到賣家的待處理清單
        for product_id, seller , quantity in zip(selected_products, selected_sellers, selected_quantities):
            
            #更新資料庫中的商品數量
            cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
            product = cursor.fetchone()
            if product:
                new_quantity = product['quantity'] - int(quantity)
                if new_quantity < 0:
                    return redirect(url_for('cart', msg='庫存不足，請重新選擇數量'))
                else:
                    cursor.execute("UPDATE products SET quantity = ? WHERE product_id = ?", (new_quantity, product_id))
                    conn.commit()
            
            seller_session = get_user_session(seller)
            if seller_session:
                seller_session['seller']['Pending_orders'].append({
                    'product_id': product_id,
                    'customer': account,
                    'quantity': quantity
                })
            save_user_session(seller, seller_session)
            
        # 更新買家購物車
        session_data['customer']['cart'] = [product_id for product_id in session_data['customer']['cart'] if str(product_id) not in selected_products]
        save_user_session(account, session_data)

        return render_template('purchaseComplete.html')

    except Exception as e:
        log_error(e)
        return render_template('error.html', user_type=session['user_type']), 500
    finally:
        conn and conn.close()


@app.route('/orderHistory')
def orderHistory():
    account = session['account']
    session_data = get_user_session(account)
    orders = session_data['customer'].get('order_history', [])
    products = get_products([order['product_id'] for order in orders])

    for idx, order in enumerate(orders):
        product = products[idx].copy()
        product['quantity'] = int(order['quantity'])
        products[idx] = product
    
    return render_template('orderHistory.html', products=products)


@app.route('/seller', methods=['GET', 'POST'])
def seller():
    if 'account' not in session:
        return redirect(url_for('login'))
    
    conn = None
    if request.method == 'POST':
        try:
            seller = session['account']
            data = request.get_json()
            product_id = data['productId']
            new_quantity = data['newStockQuantity']
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE products SET quantity = ? WHERE product_id = ?",(new_quantity, product_id,))
            conn.commit()
            print('xdd')
            
            return redirect(url_for('seller'))
        except Exception as e:
            log_error(e)
            return render_template('error.html', user_type=session['user_type']), 500
        finally:
            conn and conn.close()

    
    try:
        seller = session['account']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM products WHERE seller = ?', (seller,))
        products = cursor.fetchall()
        return render_template('seller.html', products=products)
    except Exception as e:
        log_error(e)
        return render_template('error.html', user_type=session['user_type']), 500
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
            quantity = request.form.get('quantity')
            seller = session['account']
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO products (product_id, name, description, price, quantity, seller) VALUES (?, ?, ?, ?, ?, ?);",
                (product_id, name, description, price, quantity, seller)
            )
            conn.commit()

            return redirect(url_for('seller'))
        except Exception as e:
            log_error(e)
            return render_template('error.html', user_type=session['user_type']), 500
        finally:
            conn and conn.close()
    
    return render_template('publish.html')


@app.route('/sold_product')
def soldProduct():
    account = session['account']
    session_data = get_user_session(account)
    orders = session_data['seller'].get('order_history', [])
    products = get_products([order['product_id'] for order in orders])

    for idx, order in enumerate(orders):
        product = products[idx].copy()  
        product['quantity'] = int(order['quantity'])
        products[idx] = product 
        products[idx]['customer'] = order['customer']
    return render_template('soldProduct.html', products=products)


@app.route('/pending_orders', methods=['GET', 'POST'])
def pendingOrders():
    #如果按出貨之後
    if request.method == 'POST':
        account = session['account']
        session_data = get_user_session(account)
        pending_orders = session_data['seller']['Pending_orders']
        selected_products = request.form.getlist('selected_products')
        selected_customers = request.form.getlist('selected_customers')
        selected_quantities = []
    

        for product_id in selected_products:
            quantity = request.form.get(f'quantity_{product_id}')
            selected_quantities.append(quantity)
        
        # 更新賣家待處理清單和訂單紀錄
        completed_orders = []
        added_orders = set()  # 用集合来跟踪已添加的订单

        for product_id in selected_products:
            for customer in selected_customers:
                for order in pending_orders:
                    order_tuple = (order['product_id'], order['customer'], order['quantity'])
                    if order_tuple not in added_orders and order['product_id'] == product_id and order['customer'] == customer:
                        completed_orders.append(order)
                        added_orders.add(order_tuple)

        # 更新賣家的待處理訂單
        session_data['seller']['Pending_orders'] = [order for order in pending_orders if order not in completed_orders]

        # 更新賣家的訂單紀錄
        for order in completed_orders:
            session_data['seller']['order_history'].append({'product_id': order['product_id'], 'customer': order['customer'], 'quantity': order['quantity']})
            save_user_session(account, session_data)
        
        # 更新買家的訂單紀錄
        for order in completed_orders:
            customer_account = order['customer']
            customer_session = get_user_session(customer_account)
            customer_session['customer']['order_history'].append({'product_id': order['product_id'], 'seller': session['account'], 'quantity': order['quantity']})
            save_user_session(customer_account, customer_session)
        
        pending_orders = session_data['seller'].get('Pending_orders', [])
        products = get_products([order['product_id'] for order in pending_orders])
        pending_customers = [order['customer'] for order in pending_orders]

        save_user_session(account, session_data)
        return render_template('pendingOrders.html', products=products, customers=pending_customers)

    account = session['account']
    session_data = get_user_session(account)
    pending_orders = session_data['seller'].get('Pending_orders', [])

    products = get_products([order['product_id'] for order in pending_orders])
    pending_customers = [order['customer'] for order in pending_orders]
    quantitys = [order['quantity'] for order in pending_orders]
    return render_template('pendingOrders.html', products=products, customers=pending_customers, quantitys=quantitys)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        account = request.form.get('account')
        password = request.form.get('password')
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE account = ? AND password = ?", (account, password))
            results = cursor.fetchone()
            if results and results['user_type'] == '管理員':
                session['account'] = results['account']
                session['user_type'] = results['user_type']
                return redirect(url_for('seller'))
            else:
                error = '請輸入正確的管理員帳號密碼'
                return render_template('admin.html', error=error)
        except Exception as e:
            log_error(e)
            return render_template('error.html', user_type=session['user_type']), 500
        finally:
            conn and conn.close()
    return render_template('admin.html')
