
from flask import Flask, render_template, request, redirect, url_for, jsonify
from numpy import string_
from wtforms import Form, StringField, DecimalField, IntegerField, DateField, validators
import mysql.connector
from mysql.connector import Error
import secrets
import datetime
import pymysql
from decimal import Decimal


app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Set a secret key for session management


# MySQL configurations
db_config = {
    'host': 'localhost',
    'port': 33020,
    'user': 'root',
    'password': '1234@',
    'database': 'inventory'
}

# Function to establish a MySQL connection
def connect_to_mysql():
    try:
        return mysql.connector.connect(**db_config)
    except Error as e:
        print("Error while connecting to MySQL:", e)

conn = mysql.connector.connect(**db_config)

class User:
    def __init__(self, username, role):
        self.username = username
        self.role = role

def authenticate(username, password):
    if username == 'admin' and password == 'admin':
        return User(username='admin', role='admin')
    else:
        cursor = conn.cursor(dictionary=True)
        query = "SELECT username, role FROM emp WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        user_data = cursor.fetchone()
        cursor.close()
        if user_data:
            return User(username=user_data['username'], role=user_data['role'])
        else:
            return None

@app.route('/')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login_post():
    username = request.form.get('username')
    password = request.form.get('password')

    user = authenticate(username, password)

    if user:
        if user.role == 'admin':
            return redirect(url_for('admin'))
        elif user.role == 'marketing':
            return redirect(url_for('marketing'))
        elif user.role == 'stock_manager':
            return redirect(url_for('stock_manager'))
        elif user.role == 'billing_person':
            return redirect(url_for('billing_person'))
    else:
        return render_template('login.html', error='Invalid credentials')
@app.route('/less_stock')
def less_stock():
    try:
        # Connect to MySQL
        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)

        # Retrieve data from the stock table where less_stock is greater than 0
        cursor.execute("SELECT * FROM stock WHERE less_stock > 0")
        stock_data = cursor.fetchall()

        # Close cursor and connection
        cursor.close()
        connection.close()

        # Convert stock_data to a list of dictionaries
        stock_list = list(stock_data)

        # Render the template with stock data
        return render_template('less_stock.html', less_stock_products=stock_list)

    except mysql.connector.Error as e:
        return f"Error accessing database: {e}"


@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/marketing')
def marketing():
    return render_template('marketing.html')

@app.route('/stock_manager')
def stock_manager():
    return render_template('stock_manager.html')

@app.route('/billing_person')
def billing_person():
    return render_template('billing_person.html')
def create_stock_table():
    connection = connect_to_mysql()
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock (
            id INT AUTO_INCREMENT PRIMARY KEY,
            sno INT NOT NULL,
            name VARCHAR(255) NOT NULL,
            type VARCHAR(255) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            qty INT NOT NULL,
            mfd DATE NOT NULL,
            exp DATE NOT NULL
        )
    ''')
    connection.commit()
    cursor.close()
    connection.close()
@app.route('/order')
def order():
    return render_template('order.html')


@app.route('/place_order', methods=['POST'])
def place_order():
    try:
        # Retrieve form data from the request
        sno = request.form.get('sno')
        qty = int(request.form.get('qty'))
        cuid = request.form.get('cuid')
        emp_id = request.form['emp_id']
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Check if there is sufficient stock available
        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM stock WHERE sno = %s', (sno,))
        stock = cursor.fetchone()

        if stock:
            # Calculate available stock after the order
            available_stock = stock['qty'] - qty
            less_stock = max(0, -available_stock)

            # Update stock quantity and less_stock
            cursor.execute('''
                UPDATE stock 
                SET qty = %s, less_stock = less_stock + %s 
                WHERE sno = %s
            ''', (max(0, available_stock), less_stock, sno))
            connection.commit()

            # Retrieve customer details from the database
            cursor.execute('SELECT * FROM customer WHERE cuid = %s', (cuid,))
            customer = cursor.fetchone()

            if customer:
                # Insert order data into the database
                cursor.execute('''
                    INSERT INTO orders 
                    (sno, name, type, price, qty, mfd, exp, cuid, customer_name, phone, email, address, state, city, order_time, emp_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''', (sno, stock['name'], stock['type'], stock['price'], qty, stock['mfd'], stock['exp'], cuid, customer['name'], customer['phone'], customer['email'], customer['address'], customer['state'], customer['city'], current_time, emp_id))
                connection.commit()
                
                # Retrieve the last inserted order ID
                cursor.execute('SELECT LAST_INSERT_ID() as last_id')
                last_order_id = cursor.fetchone()['last_id']
                
                return f'Order placed successfully. Order ID: {last_order_id}'
            else:
                return 'Customer not found.'
        else:
            return 'Invalid stock ID.'

    except Error as e:
        connection.rollback()
        return f"Error placing order: {e}"

    finally:
        cursor.close()
        connection.close()

# Function to fetch stock data from the database
def fetch_stock_data():
    connection = connect_to_mysql()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM stock')
    stock_data = cursor.fetchall()
    cursor.close()
    connection.close()
    return stock_data

class StockForm(Form):
    sno = IntegerField('SNO', [validators.NumberRange(min=1)])
    name = StringField('Name', [validators.Length(min=1, max=255)])
    type = StringField('Type', [validators.Length(min=1, max=255)])
    price = DecimalField('Price', [validators.NumberRange(min=0)])
    qty = IntegerField('Quantity', [validators.NumberRange(min=0)])
    mfd = DateField('Manufacture Date', format='%Y-%m-%d')
    exp = DateField('Expiry Date', format='%Y-%m-%d')


@app.route('/')
def index():
    return render_template('index.html')
@app.route('/customer_seller')
def customer_seller():
    return render_template('customer_seller.html')

 
@app.route('/view_stock')
def view_stock():
    stock_data = fetch_stock_data()
    return render_template('view_stock.html', stock_list=stock_data)

@app.route('/search_product')
def search_product_form():
    return render_template('search_product.html')
@app.route('/search')
def search_product():
    # Retrieve the SNO from the request parameters
    sno = request.args.get('sno')

    # Query the database to find the product by SNO
    connection = connect_to_mysql()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM stock WHERE sno = %s', (sno,))
    product = cursor.fetchone()
    cursor.close()
    connection.close()

    # If product found, return it as JSON response
    if product:
        return jsonify(product)
    else:
        # If product not found, return appropriate message
        return jsonify({'error': 'Product not found for SNO {}'.format(sno)}), 404


# Route to handle the form submission
product_data = {
    'sno': 123,
    'name': 'Product Name',
    'qty': 10
}


# Route to render the alter stock form
@app.route('/alter_stock')
def alter_stock_form():
    return render_template('alter_stock.html')

# Route to handle form submission and display product data
@app.route('/alter_stock', methods=['POST'])
def alter_stock():
    sno = request.form['sno']

    # Retrieve product data from the database
    connection = connect_to_mysql()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute('SELECT name, qty ,SNO FROM stock WHERE sno = %s', (sno,))
        product_data = cursor.fetchone()
        if product_data:
            return render_template('alter_stock.html', product_data=product_data)
        else:
            return render_template('alter_stock.html', error='Product not found')
    except Error as e:
        return f"Error retrieving product data: {e}"
    finally:
        cursor.close()
        connection.close()
def fetch_data():
    # Connect to the database and obtain a cursor
    cursor = connect_to_mysql()

    try:
        # Execute SQL query
        cursor.execute("SELECT * FROM stock")

        # Fetch data
        data = cursor.fetchall()

        # Process the data
        for row in data:
            print(row)

    except Exception as e:
        print(f"Error: {e}")

    finally:
        # Close cursor and connection
        cursor.close()
@app.route('/edit_products/<int:sno>', methods=['POST'])
def save_changes(sno):
    try:
            # Retrieve form data from the request
            name = request.form.get('name')
            product_type = request.form.get('type')
            price = request.form.get('price')
            qty = request.form.get('qty')
            mfd = request.form.get('mfd')
            exp = request.form.get('exp')

            # Update product data in the database
            if update_product_data(sno, name, product_type, price, qty, mfd, exp):
                return "Product updated successfully"
            else:
                return "Failed to update product"
    except Exception as e:
            return f"Error updating product: {e}"

@app.route('/edit_product/<int:sno>', methods=['GET', 'POST'])
def edit_product(sno):
    if request.method == 'GET':
        try:
            # Connect to the database and retrieve product data based on the sno
            product_data = fetch_product_data(sno)
            if product_data:
                # Render the edit_product.html template with the retrieved product data
                return render_template('edit_product.html', product_data=product_data)
            else:
                return "Product not found"
        except Exception as e:
            return f"Error retrieving product data: {e}"
    
    
# Function to fetch product data based on sno
def fetch_product_data(sno):
    try:
        connection = connect_to_mysql()
        
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM stock WHERE sno = %s", (sno,))
        product_data = cursor.fetchone()

        return product_data

    except Error as e:
        print(f"Error fetching product data: {e}")
        return None

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()

# Function to update product data in the database
def update_product_data(sno, name, product_type, price, qty, mfd, exp,):
    try:
        connection = connect_to_mysql()
       

        cursor = connection.cursor()
        cursor.execute("""
            UPDATE stock
            SET name = %s, type = %s, price = %s, qty = %s, mfd = %s, exp = %s
            WHERE sno = %s
        """, (name, product_type, price, qty, mfd, exp, sno,))

        connection.commit()

        return True

    except Error as e:
        print(f"Error updating product data: {e}")
        return False

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()
@app.route('/stock_update', methods=['GET', 'POST'])
def stock_update():
    form = StockForm(request.form)
    if request.method == 'POST' and form.validate():
        # Retrieve form data from the request
        sno = form.sno.data
        name = form.name.data
        stype = form.type.data
        price = form.price.data
        qty = form.qty.data
        mfd = form.mfd.data
        exp = form.exp.data

        # Insert new stock data into the database
        connection = connect_to_mysql()
        cursor = connection.cursor()
        try:
            # Check if the product with the given sno, name, and mfd already exists
            cursor.execute('''
                SELECT * FROM stock 
                WHERE sno = %s AND mfd = %s AND exp = %s
            ''', (sno, mfd, exp))
            existing_product = cursor.fetchone()

            if existing_product:
                # Update the existing stock entry with the new quantity and subtract from less_stock
                existing_qty = existing_product[4]  # Assuming quantity is at index 4, adjust if needed
                new_qty = int(existing_qty) + int(qty)
                less_stock = int(existing_product[6].strftime('%d')) - qty  # Assuming less_stock is at index 6, adjust if needed
                if less_stock < 0:
                    less_stock = 0  # Ensuring less_stock is not negative
                cursor.execute('''
                    UPDATE stock
                    SET qty = %s, less_stock = %s
                    WHERE sno = %s AND mfd = %s AND exp = %s
                ''', (new_qty, less_stock, sno, mfd, exp))
            else:
                # Insert a new stock entry
                cursor.execute('''
                    INSERT INTO stock (sno, name, type, price, qty, mfd, exp, less_stock)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
                ''', (sno, name, stype, price, qty, mfd, exp))
            
            connection.commit()
            return 'Stock update successful.'
        
        except mysql.connector.Error as e:
            connection.rollback()
            return f"Error updating stock: {e}"
        
        finally:
            cursor.close()
            connection.close()
    else:
        return render_template('stock_update.html', form=form)


@app.route('/delete_product/<int:sno>', methods=['GET', 'POST'])
def delete_product(sno):
    try:
        if request.method == 'POST':
            # Retrieve the sno from the form data
            #sno = request.form['sno']
            

            # Perform the deletion operation in the database
            # Assuming you have a function connect_to_mysql() to establish a database connection
            connection = connect_to_mysql()
            cursor = connection.cursor()

            # Use DELETE query to remove the product with the specified sno
            cursor.execute("DELETE FROM stock WHERE sno = %s", (sno,))
            connection.commit()

            return "Product deleted successfully"

    except Exception as e:
        return f"Error deleting product: {e}"

    finally:
        cursor.close()
        connection.close()
# Create 'customer' table if it doesn't exist
def create_customer_table():
    connection = connect_to_mysql()
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customer (
    cuid INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address VARCHAR(255) NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    phone VARCHAR(15) NOT NULL,
    email VARCHAR(255) NOT NULL,
    address_id INT,  -- Add the missing columns
    name_id INT,
    contact_info_id INT
)

    ''')
    connection.commit()
    cursor.close()
    connection.close()

# Create 'customer' table if it doesn't exist
create_customer_table()

class CustomerForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=255)])
    address = StringField('Address', [validators.Length(min=1, max=255)])
    city = StringField('City', [validators.Length(min=1, max=100)])
    state = StringField('State', [validators.Length(min=1, max=100)])
    phone = StringField('Phone', [validators.Length(min=1, max=15)])
    email = StringField('Email', [validators.Length(min=1, max=255)])

@app.route('/new_customer', methods=['GET', 'POST'])
def new_customer():
    form = CustomerForm(request.form)

    if request.method == 'POST' and form.validate():
        name = request.form.get('name')
        address = request.form.get('address')
        city = request.form.get('city')
        state = request.form.get('state')
        phone = request.form.get('phone')
        email = request.form.get('email')

        connection = connect_to_mysql()
        cursor = connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO customer (name, address, city, state, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (name, address, city, state, phone, email))
            connection.commit()
            return 'Customer added successfully.'
        except Error as e:
            return f"Error adding customer: {e}"
        finally:
            cursor.close()
            connection.close()

    return render_template('new_customer.html', form=form)
def view_customer_details():
    # Fetch all customer details from the database
    connection = connect_to_mysql()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM customer')
    customers = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('customer_details.html', customers=customers)

# Route to handle the form submission for finding a customer by phone number
@app.route('/find_customer', methods=['GET', 'POST'])
def find_customer():
    if request.method == 'POST':
        # Retrieve the phone number from the form data
        phone = request.form.get('phone')
        
        # Query the database to find the customer by phone number
        connection = connect_to_mysql()
        cursor = connection.cursor(dictionary=True)
        cursor.execute('SELECT * FROM customer WHERE phone = %s', (phone,))
        customer = cursor.fetchone()
        cursor.close()
        connection.close()

        if customer:
            # If customer found, render template with customer details
            return render_template('found_customer.html', customer=customer)
        else:
            # If customer not found, display error message
            return 'Customer not found.'

    # If method is GET, render the form to find customer
    return render_template('find_customer.html')
@app.route('/customer_details')
def customer_details():
    connection = connect_to_mysql()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM customer')
    customer_data = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('customer_details.html', customers=customer_data)


# Route to render the employee creation form
@app.route('/employee')
def employee_form():
    return render_template('employee.html')

# Route to handle form submission and store employee data
@app.route('/create_employee', methods=['POST'])
def create_employee():
    if request.method == 'POST':
        # Retrieve form data
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        role = request.form['role']
        password = request.form['password']
        phone = request.form['phone']
        country = request.form['country']
        state = request.form['state']
        address = request.form['address']
        pincode = request.form['pincode']
        salary = request.form['salary']
        
        # Generate emp_id
        emp_id = first_name[0] + last_name[0] + phone[-2:]

        # Save employee data to the database
        connection = connect_to_mysql()
        cursor = connection.cursor()
        try:
            cursor.execute('''
                INSERT INTO emp (emp_id, first_name, last_name, username, role, password, phone, country, state, address, pincode, salary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (emp_id, first_name, last_name, username, role, password, phone, country, state, address, pincode, salary))
            connection.commit()
            return 'Employee created successfully. Emp ID: {}'.format(emp_id)
        except Error as e:
            return f"Error creating employee: {e}"
        finally:
            cursor.close()
            connection.close()
def execute_query(query, params=None, fetch_one=False):
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    
    try:
        cursor.execute(query, params)
        connection.commit()
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        return result
    finally:
        cursor.close()
        connection.close()
def execute_query(query, params=None, fetch_one=False):
    connection = pymysql.connect(**db_config)
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    
    try:
        cursor.execute(query, params)
        connection.commit()
        
        if fetch_one:
            result = cursor.fetchone()
        else:
            result = cursor.fetchall()
        
        return result
    finally:
        cursor.close()
        connection.close()

@app.route('/billing')
def billing_page():
     return render_template('billing.html')




@app.route('/generate_bill', methods=['POST'])
def generate_bill():
    if request.method == 'POST':
        # Get order details from the form
        order_id = request.form['order_id']
        discount = Decimal(request.form['discount'])  # Convert discount to Decimal
        
        # Get payment method and transaction ID from the form
        payment_method = request.form.get('payment_method')
        transaction_id = request.form.get('transaction_id')
        
        # Query the database to get order data
        query = 'SELECT * FROM orders WHERE order_id = %s'
        order_data = execute_query(query, (order_id,), fetch_one=True)
        
        if order_data:
            # Calculate the total amount with discount
            total_amount = Decimal(order_data['qty']) * Decimal(order_data['price']) - discount
            
            # Render the bill details template with the data
            return render_template('bill_details.html', order_data=order_data, total_amount=total_amount, discount=discount, payment_method=payment_method, transaction_id=transaction_id)
        else:
            return 'Order not found.'



@app.route('/find_order', methods=['POST'])
def find_order():
    if request.method == 'POST':
        phone_number = request.form.get('phone_number')

        try:
            # Perform database query to find the order by phone number
            connection = connect_to_mysql()
            cursor = connection.cursor(dictionary=True)
            cursor.execute('SELECT * FROM orders WHERE phone = %s', (phone_number,))
            order = cursor.fetchone()

            if order:
                # If order is found, return order details
                return render_template('order_details.html', order=order)
            else:
                # If order is not found, return an appropriate message
                return "Order not found."

        except mysql.connector.Error as e:
            # Handle database errors
            return f"Error finding order: {e}"

        finally:
            # Close cursor and connection
            try:
                cursor.close()
                connection.close()
            except Exception as e:
                pass  # Handle exceptions while closing cursor and connection



if __name__ == '__main__':
    app.run(debug=True)
