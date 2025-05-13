from flask import Flask, render_template, request, redirect, session, url_for, flash
from db_config import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask import Flask, render_template, request, redirect, url_for
from werkzeug.utils import secure_filename
import mysql.connector
app = Flask(__name__)
app.secret_key = 'your_secret_key'


@app.route('/')
def home():
    return render_template('home.html')


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
        except:
            flash('Username already exists!', 'danger')
        finally:
            cursor.close()
            conn.close()
    return render_template('register.html')


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
            return redirect('/products')
        else:
            flash('Invalid credentials', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


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
        data = (
            request.form['product_name'],
            request.form['brand'],
            request.form['category'],
            request.form['price'],
            request.form['stock_quantity'],
            request.form['description'],
            request.form['image']
        )
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Products (product_name, brand, category, price, stock_quantity, description, image) VALUES (%s, %s, %s, %s, %s, %s, %s)", data)
        conn.commit()
        cursor.close()
        conn.close()
        return redirect('/products')
    return render_template('product_form.html', action='Add')


@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    if request.method == 'POST':
        data = (
            request.form['product_name'],
            request.form['brand'],
            request.form['category'],
            request.form['price'],
            request.form['stock_quantity'],
            request.form['description'],
            request.form['image'],
            product_id
        )
        cursor.execute("""UPDATE Products SET product_name=%s, brand=%s, category=%s, price=%s,
                          stock_quantity=%s, description=%s, image=%s WHERE product_id=%s""", data)
        conn.commit()
        cursor.close()
        conn.close()
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
    cursor.execute("DELETE FROM Products WHERE product_id = %s", (product_id,))
    conn.commit()
    cursor.close()
    conn.close()
    return redirect('/products')




if __name__ == '__main__':
    app.run(debug=True)
