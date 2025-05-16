from flask import Flask, render_template, request, redirect, session, url_for, flash
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuration for file uploads
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    if 'username' in session:
        return redirect('/dashboard')
    return render_template('home.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')
    
    # Get counts for dashboard
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT COUNT(*) as count FROM Customers")
    customer_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM Products")
    product_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM Orders")
    order_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT SUM(total_amount) as revenue FROM Orders")
    revenue = cursor.fetchone()['revenue'] or 0
    
    cursor.close()
    conn.close()
    
    return render_template('dashboard.html', 
                         customer_count=customer_count,
                         product_count=product_count,
                         order_count=order_count,
                         revenue=revenue)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        role = request.form['role']
        staff_id = request.form['staff_id']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO accounts (staff_id, username, password_hash, role) VALUES (%s, %s, %s, %s)",
                           (staff_id, username, password, role))
            conn.commit()
            flash('Account created successfully!', 'success')
            return redirect('/login')
        except mysql.connector.Error as err:
            flash(f'Error: {err}', 'danger')
        finally:
            cursor.close()
            conn.close()
    
    # Get staff list for dropdown
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT staff_id, full_name FROM Staff")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return render_template('register.html', staff_list=staff_list)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM accounts WHERE username = %s", (username,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['account_id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash('Login successful!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect('/login')

# Customer Management
@app.route('/customers')
def customers():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Customers")
    customers = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('customers.html', customers=customers)

@app.route('/customer/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        data = (
            request.form['full_name'],
            request.form['phone'],
            request.form['email'],
            request.form['address'],
            request.form['date_of_birth'],
            request.form['skin_type']
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Customers (full_name, phone, email, address, date_of_birth, skin_type) 
            VALUES (%s, %s, %s, %s, %s, %s)
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Customer added successfully!', 'success')
        return redirect('/customers')
    return render_template('customer_form.html', action='Add')

@app.route('/customer/edit/<int:customer_id>', methods=['GET', 'POST'])
def edit_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = (
            request.form['full_name'],
            request.form['phone'],
            request.form['email'],
            request.form['address'],
            request.form['date_of_birth'],
            request.form['skin_type'],
            customer_id
        )
        cursor.execute("""
            UPDATE Customers SET full_name=%s, phone=%s, email=%s, address=%s, 
            date_of_birth=%s, skin_type=%s WHERE customer_id=%s
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Customer updated successfully!', 'success')
        return redirect('/customers')

    cursor.execute("SELECT * FROM Customers WHERE customer_id = %s", (customer_id,))
    customer = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('customer_form.html', action='Edit', customer=customer)

@app.route('/customer/delete/<int:customer_id>')
def delete_customer(customer_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Customers WHERE customer_id = %s", (customer_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Customer deleted successfully!', 'success')
    return redirect('/customers')

# Product Management
@app.route('/products')
def products():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Products")
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('products.html', products=products)

@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        # Handle file upload
        if 'image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            flash('No selected file', 'danger')
            return redirect(request.url)
            
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            
            data = (
                request.form['product_name'],
                request.form['brand'],
                request.form['category'],
                float(request.form['price']),
                int(request.form['stock_quantity']),
                request.form['description'],
                filename
            )
            
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO Products (product_name, brand, category, price, stock_quantity, description, image) 
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, data)
            conn.commit()
            cursor.close()
            conn.close()
            flash('Product added successfully!', 'success')
            return redirect('/products')
    
    return render_template('product_form.html', action='Add')

@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        # Handle file upload
        filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        
        # Get existing image if new one wasn't uploaded
        if not filename:
            cursor.execute("SELECT image FROM Products WHERE product_id = %s", (product_id,))
            result = cursor.fetchone()
            filename = result['image'] if result else None
        
        data = (
            request.form['product_name'],
            request.form['brand'],
            request.form['category'],
            float(request.form['price']),
            int(request.form['stock_quantity']),
            request.form['description'],
            filename,
            product_id
        )
        
        cursor.execute("""
            UPDATE Products SET product_name=%s, brand=%s, category=%s, price=%s,
            stock_quantity=%s, description=%s, image=%s WHERE product_id=%s
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Product updated successfully!', 'success')
        return redirect('/products')

    cursor.execute("SELECT * FROM Products WHERE product_id = %s", (product_id,))
    product = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('product_form.html', action='Edit', product=product)

@app.route('/product/delete/<int:product_id>')
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # First get image path to delete the file
    cursor.execute("SELECT image FROM Products WHERE product_id = %s", (product_id,))
    result = cursor.fetchone()
    if result and result[0]:
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], result[0]))
        except OSError:
            pass
    
    cursor.execute("DELETE FROM Products WHERE product_id = %s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Product deleted successfully!', 'success')
    return redirect('/products')

# Order Management
@app.route('/orders')
def orders():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT o.order_id, o.order_date, o.total_amount, 
               c.full_name as customer_name, s.full_name as staff_name
        FROM Orders o
        JOIN Customers c ON o.customer_id = c.customer_id
        JOIN Staff s ON o.staff_id = s.staff_id
        ORDER BY o.order_date DESC
    """)
    orders = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('orders.html', orders=orders)

@app.route('/order/view/<int:order_id>')
def view_order(order_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get order header
    cursor.execute("""
        SELECT o.*, c.full_name as customer_name, c.phone as customer_phone,
               s.full_name as staff_name
        FROM Orders o
        JOIN Customers c ON o.customer_id = c.customer_id
        JOIN Staff s ON o.staff_id = s.staff_id
        WHERE o.order_id = %s
    """, (order_id,))
    order = cursor.fetchone()
    
    # Get order items
    cursor.execute("""
        SELECT oi.*, p.product_name, p.brand, p.image
        FROM Order_Items oi
        JOIN Products p ON oi.product_id = p.product_id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('order_details.html', order=order, items=items)

@app.route('/order/create', methods=['GET', 'POST'])
def create_order():
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        staff_id = session.get('staff_id', 1)  # Default to admin if not set
        order_date = request.form['order_date']
        
        # First create the order header
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Orders (customer_id, staff_id, order_date, total_amount)
            VALUES (%s, %s, %s, 0)
        """, (customer_id, staff_id, order_date))
        order_id = cursor.lastrowid
        
        # Process order items
        total_amount = 0
        product_ids = request.form.getlist('product_id[]')
        quantities = request.form.getlist('quantity[]')
        
        for product_id, quantity in zip(product_ids, quantities):
            if not product_id or not quantity:
                continue
                
            # Get product price
            cursor.execute("SELECT price FROM Products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if not product:
                continue
                
            price = product[0]
            subtotal = price * int(quantity)
            
            # Add order item
            cursor.execute("""
                INSERT INTO Order_Items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, product_id, quantity, price))
            
            # Update product stock
            cursor.execute("""
                UPDATE Products SET stock_quantity = stock_quantity - %s
                WHERE product_id = %s
            """, (quantity, product_id))
            
            total_amount += subtotal
        
        # Update order total
        cursor.execute("""
            UPDATE Orders SET total_amount = %s WHERE order_id = %s
        """, (total_amount, order_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        flash('Order created successfully!', 'success')
        return redirect(f'/order/view/{order_id}')
    
    # Get data for dropdowns
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT customer_id, full_name FROM Customers")
    customers = cursor.fetchall()
    
    cursor.execute("SELECT product_id, product_name, price FROM Products WHERE stock_quantity > 0")
    products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('order_form.html', customers=customers, products=products)

# Staff Management
@app.route('/staff')
def staff():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Staff")
    staff_list = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('staff.html', staff_list=staff_list)

@app.route('/staff/add', methods=['GET', 'POST'])
def add_staff():
    if request.method == 'POST':
        data = (
            request.form['full_name'],
            request.form['role'],
            request.form['phone'],
            request.form['email']
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO Staff (full_name, role, phone, email) 
            VALUES (%s, %s, %s, %s)
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Staff member added successfully!', 'success')
        return redirect('/staff')
    return render_template('staff_form.html', action='Add')

@app.route('/staff/edit/<int:staff_id>', methods=['GET', 'POST'])
def edit_staff(staff_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        data = (
            request.form['full_name'],
            request.form['role'],
            request.form['phone'],
            request.form['email'],
            staff_id
        )
        cursor.execute("""
            UPDATE Staff SET full_name=%s, role=%s, phone=%s, email=%s 
            WHERE staff_id=%s
        """, data)
        conn.commit()
        cursor.close()
        conn.close()
        flash('Staff member updated successfully!', 'success')
        return redirect('/staff')

    cursor.execute("SELECT * FROM Staff WHERE staff_id = %s", (staff_id,))
    staff_member = cursor.fetchone()
    cursor.close()
    conn.close()
    return render_template('staff_form.html', action='Edit', staff=staff_member)

@app.route('/staff/delete/<int:staff_id>')
def delete_staff(staff_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM Staff WHERE staff_id = %s", (staff_id,))
    conn.commit()
    cursor.close()
    conn.close()
    flash('Staff member deleted successfully!', 'success')
    return redirect('/staff')

# Reports
@app.route('/reports/sales')
def sales_report():
    # Default to last 30 days
    date_from = request.args.get('from', '')
    date_to = request.args.get('to', '')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT o.order_date, COUNT(o.order_id) as order_count, 
               SUM(o.total_amount) as total_sales,
               GROUP_CONCAT(DISTINCT p.product_name) as products_sold
        FROM Orders o
        JOIN Order_Items oi ON o.order_id = oi.order_id
        JOIN Products p ON oi.product_id = p.product_id
    """
    
    params = []
    if date_from and date_to:
        query += " WHERE o.order_date BETWEEN %s AND %s"
        params.extend([date_from, date_to])
    
    query += " GROUP BY o.order_date ORDER BY o.order_date DESC"
    
    cursor.execute(query, params)
    sales_data = cursor.fetchall()
    
    # Get top products
    cursor.execute("""
        SELECT p.product_name, SUM(oi.quantity) as total_sold, 
               SUM(oi.quantity * oi.price) as revenue
        FROM Order_Items oi
        JOIN Products p ON oi.product_id = p.product_id
        GROUP BY p.product_name
        ORDER BY total_sold DESC
        LIMIT 5
    """)
    top_products = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('sales_report.html', 
                         sales_data=sales_data,
                         top_products=top_products,
                         date_from=date_from,
                         date_to=date_to)

@app.route('/reports/inventory')
def inventory_report():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Low stock items
    cursor.execute("""
        SELECT product_name, stock_quantity 
        FROM Products 
        WHERE stock_quantity < 10
        ORDER BY stock_quantity ASC
    """)
    low_stock = cursor.fetchall()
    
    # All inventory
    cursor.execute("SELECT product_name, stock_quantity FROM Products ORDER BY stock_quantity ASC")
    inventory = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('inventory_report.html', 
                         low_stock=low_stock,
                         inventory=inventory)

if __name__ == '__main__':
    # Create upload folder if it doesn't exist
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    
    app.run(debug=True)