# Import necessary libraries
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime, timedelta
matplotlib.use('Agg')
import seaborn as sns
from datetime import datetime
import os
from sqlalchemy import func

# Create the Flask app
app = Flask(__name__)

# Set secret key for security
app.config['SECRET_KEY'] = 'your-secret-key'

# Set database URI
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:6399@localhost/inventory_db'

# Disable track modifications to prevent app overhead
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager(app)

# Set login view
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    """Define the User model."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Category(db.Model):
    """Define the Category model."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    """Define the Product model."""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10)

class Order(db.Model):
    """Define the Order model."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), default='PENDING')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    items = db.relationship('OrderItem', backref='order', lazy=True)
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Correct usage of the session

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    product = db.relationship('Product', backref='order_items')

class Expenditure(db.Model):
    """Define the Expenditure model."""
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    description = db.Column(db.String(200))

class UserActivity(db.Model):
    """Define the UserActivity model to store user activities."""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Define a relationship to the User model
    user = db.relationship('User', backref='activities')
    

# Custom decorators for role-based access control
def admin_required(f):
    """Decorator for admin-only access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'ADMIN':
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function
'''
@app.route('/user-activity')
@admin_required
def user_activity():
    """User  activity route."""
    activities = UserActivity.query.join(User).all()  # Join with User to get user names
    return render_template('user_activity.html', activities=activities)
'''

def manager_required(f):
    """Decorator for manager-only access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['ADMIN', 'MANAGER']:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def supervisor_required(f):
    """Decorator for supervisor-only access."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['ADMIN', 'MANAGER', 'SUPERVISOR']:
            flash('You do not have permission to access this page.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_user_activity(action):
    """Function to log user activity."""
    activity = UserActivity(user_id=current_user.id, action=action)
    db.session.add(activity)
    db.session.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login route."""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            log_user_activity('logged in')
            return redirect(url_for('dashboard'))
            
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Logout route."""
    log_user_activity('logged out')  # Log the activity only if the user is authenticated
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard route."""
    log_user_activity('visited dashboard')
    # Fetch low stock products
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold).all()

    # Fetch total sales by product
    total_sales = db.session.query(
        Product.name,
        db.func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem).join(Order).group_by(Product.id).all()

    # Prepare data for visualization
    products = [item[0] for item in total_sales]
    sales_values = [item[1] if item[1] is not None else 0 for item in total_sales]

    # Create a bar plot for total sales by product
    plt.figure(figsize=(10, 6))
    sns.barplot(x=products, y=sales_values, palette='viridis')
    plt.title('Total Sales by Product')
    plt.xlabel('Product')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/total_sales.png')  
    plt.close()

    # Fetch monthly expenditure data
    monthly_expenditure = db.session.query(
        db.func.date_format(Expenditure.date, '%Y-%m').label('month'),
        db.func.sum(Expenditure.amount).label('total_expenditure')
    ).group_by('month').all()

    # Prepare data for visualization
    months = [item[0] for item in monthly_expenditure]
    expenditure_values = [item[1] if item[1] is not None else 0 for item in monthly_expenditure]

    # Create a line plot for monthly expenditure
    plt.figure(figsize=(12, 6))
    sns.lineplot(x=months, y=expenditure_values, marker='o')
    plt.title('Monthly Expenditure')
    plt.xlabel('Month')
    plt.ylabel('Expenditure')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/monthly_expenditure.png')  
    plt.close()

    # Fetch daily sales data
    daily_sales = db.session.query(
        db.func.date(Order.created_at).label('date'),  
        db.func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem).group_by(db.func.date(Order.created_at)).order_by(db.func.date(Order.created_at)).all()

    # Prepare data for visualization
    dates = [record.date.strftime('%Y-%m-%d') for record in daily_sales]
    daily_sales_values = [record.total_sales for record in daily_sales]

    # Create a line plot for daily sales
    plt.figure(figsize=(12, 6))
    sns.lineplot(x=dates, y=daily_sales_values, marker='o')
    plt.title('Daily Sales')
    plt.xlabel('Date')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)  
    plt.tight_layout()
    plt.savefig('static/daily_sales.png')  
    plt.close()

    return render_template('dashboard.html', low_stock=low_stock)

@app.route('/users')
@admin_required
def users():
    """Users route."""
    log_user_activity('visited users')
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_user():
    """Add user route."""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user = User(name=name, email=email, password=generate_password_hash(password), role=role)
        db.session.add(user)
        db.session.commit()
        
        flash('User added successfully')
        log_user_activity(f'added user {user.name}')
        return redirect(url_for('users'))
    
    return render_template('add_user.html')

@app.route('/products')
@login_required
def products():
    """Products route."""
    log_user_activity('visited products')
    products = Product.query.all()
    categories = Category.query.all()
    return render_template('products.html', products=products, categories=categories)

@app.route('/products/add', methods=['POST'])
@supervisor_required
def add_product():
    """Add product route."""
    name = request.form.get('name')
    description = request.form.get('description')
    quantity = int(request.form.get('quantity'))
    price = float(request.form.get('price'))
    category_id = int(request.form.get('category_id'))
    low_stock_threshold = int(request.form.get('low_stock_threshold'))
    
    product = Product(
        name=name,
        description=description,
        quantity=quantity,
        price=price,
        category_id=category_id,
        low_stock_threshold=low_stock_threshold
    )
    
    db.session.add(product)
    db.session.commit()
    
    flash('Product added successfully')
    log_user_activity(f'added product {product.name}')
    return redirect(url_for('products'))

@app.route('/categories')
@login_required
def categories():
    """Categories route."""
    log_user_activity('visited categories')
    categories = Category.query.all()
    return render_template('categories.html', categories=categories)

@app.route('/categories/add', methods=['POST'])
@manager_required
def add_category():
    """Add category route."""
    name = request.form.get('name')
    description = request.form.get('description')
    
    category = Category(name=name, description=description)
    db.session.add(category)
    db.session.commit()
    
    flash('Category added successfully')
    log_user_activity(f'added category {category.name}')
    return redirect(url_for('categories'))

@app.route('/orders')
@login_required
def orders():
    """Orders route."""
    log_user_activity('visited orders')
    if current_user.role in ['ADMIN', 'MANAGER']:
        orders = Order.query.join(User).add_columns(User.name, User.role).all()
    else:
        orders = Order.query.filter_by(user_id=current_user.id).join(User).add_columns(User.name, User.role).all()
    
    products = Product.query.all()
    return render_template('orders.html', orders=orders, products=products) 

@app.route('/orders/create', methods=['POST'])
@login_required
@manager_required
def create_order():
    """Create order route."""
    product_id = int(request.form.get('product_id'))
    quantity = int(request.form.get('quantity'))
    
    order = Order(user_id=current_user.id)
    order_item = OrderItem(product_id=product_id, quantity=quantity)
    order.items.append(order_item)
    
    db.session.add(order)
    db.session.commit()

    product = Product.query.get(product_id)
    if product:
        expenditure_amount = product.price * quantity
        expenditure = Expenditure(amount=expenditure_amount, 
                                  date=datetime.utcnow(), 
                                  description=f'Order created for {quantity} of {product.name}')
        db.session.add(expenditure)
        db.session.commit()
        log_user_activity(f'created order for {product.name}')
    else:
        print(f"Product with ID {product_id} not found. No expenditure recorded.")

    flash('Order created successfully')
    return redirect(url_for('orders'))

@app.route('/orders/<int:order_id>/update-status', methods=['POST'])
@manager_required
def update_order_status(order_id):
    """Update order status route."""
    order = Order.query.get_or_404(order_id)
    status = request.form.get('status')
    
    if status in ['PENDING', 'APPROVED', 'REJECTED', 'COMPLETED']:
        order.status = status
        db.session.commit()
        log_user_activity(f'updated order {order_id} status to {status}')
        flash('Order status updated successfully')
    
    return redirect(url_for('orders'))
'''
@app.route('/reports')
@manager_required
def reports():
    """Reports route."""
    log_user_activity('visited reports')
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold).all()
    total_inventory_value = db.session.query(db.func.sum(Product.quantity * Product.price)).scalar()
    
    total_sales = db.session.query(
        Product.name,
        db.func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem).join(Order).group_by(Product.id).all()

    order_counts = db.session.query(
        Order.status,
        db.func.count(Order.id).label('count')
    ).group_by(Order.status).all()

    order_counts_list = [{'status': status, 'count': count} for status, count in order_counts]

    products = [item[0] for item in total_sales]
    sales_values = [item[1] if item[1] is not None else 0 for item in total_sales]

    plt.figure(figsize=(10, 6))
    sns.barplot(x=products, y=sales_values, palette='viridis', hue=products)  
    plt.title('Total Sales by Product')
    plt.xlabel('Product')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/total_sales.png')  
    plt.close()

    monthly_expenditure = db.session.query(
        db.func.date_format(Expenditure.date, '%Y-%m').label('month'),
        db.func.sum(Expenditure.amount).label('total_expenditure')
    ).group_by('month').all()

    months = [item[0] for item in monthly_expenditure]
    expenditure_values = [item[1] if item[1] is not None else 0 for item in monthly_expenditure]

    plt.figure(figsize=(12, 6))
    sns.lineplot(x=months, y=expenditure_values, marker='o')
    plt.title('Monthly Expenditure')
    plt.xlabel('Month')
    plt.ylabel('Expenditure')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig('static/monthly_expenditure.png')  
    plt.close()

    daily_sales = db.session.query(
        db.func.date(Order.created_at).label('date'),  
        db.func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem).group_by(db.func.date(Order.created_at)).order_by(db.func.date(Order.created_at)).all()

    dates = [record.date.strftime('%Y-%m-%d') for record in daily_sales]
    daily_sales_values = [record.total_sales for record in daily_sales]

    plt.figure(figsize=(12, 6))
    sns.lineplot(x=dates, y=daily_sales_values, marker='o')
    plt.title('Daily Sales')
    plt.xlabel('Date')
    plt.ylabel('Total Sales')
    plt.xticks(rotation=45)  
    plt.tight_layout()
    plt.savefig('static/daily_sales.png')  
    plt.close()

    return render_template('reports.html', low_stock=low_stock, total_inventory_value=total_inventory_value, order_counts=order_counts_list)
'''
'''
@app.route('/reports')
@manager_required
def reports():
    """Reports route."""
    log_user_activity('visited reports')
    
    # Low Stock Items
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold).all()
    
    # Total Inventory Value
    total_inventory_value = db.session.query(db.func.sum(Product.quantity * Product.price)).scalar() or 0
    
    # Order Counts
    order_counts = db.session.query(
        Order.status,
        db.func.count(Order.id).label('count')
    ).group_by(Order.status).all()

    order_counts_list = [{'status': status, 'count': count} for status, count in order_counts]

    # Total Sales by Product
    total_sales_query = db.session.query(
        Product.name,
        db.func.sum(OrderItem.quantity).label('total_sales')
    ).join(OrderItem, Product.id == OrderItem.product_id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .group_by(Product.id, Product.name)\
     .all()

    products = [item[0] for item in total_sales_query]
    sales_values = [item[1] if item[1] is not None else 0 for item in total_sales_query]

    # Monthly Expenditure
    monthly_expenditure_query = db.session.query(
        db.func.date_format(Expenditure.date, '%Y-%m').label('month'),
        db.func.sum(Expenditure.amount).label('total_expenditure')
    ).group_by('month').all()

    months = [item[0] for item in monthly_expenditure_query]
    expenditure_values = [item[1] if item[1] is not None else 0 for item in monthly_expenditure_query]

    # Debugging print statements
    print("Products:", products)
    print("Sales Values:", sales_values)
    print("Months:", months)
    print("Expenditure Values:", expenditure_values)

    return render_template(
        'reports.html', 
        low_stock=low_stock, 
        total_inventory_value=total_inventory_value, 
        order_counts=order_counts_list,
        products=products,
        sales_values=sales_values,
        months=months,
        expenditure_values=expenditure_values
    )'''
@app.route('/reports')
@login_required
def reports():
    """Reports route."""
    log_user_activity('visited reports')
    
    # Existing report data
    low_stock = Product.query.filter(Product.quantity <= Product.low_stock_threshold).all()
    total_inventory_value = db.session.query(func.sum(Product.quantity * Product.price)).scalar() or 0
    
    # New detailed report data
    today = datetime.now().date()
    last_week = today - timedelta(days=7)
    last_month = today - timedelta(days=30)

    # Weekly usage
    weekly_usage = db.session.query(
        func.sum(OrderItem.quantity)
    ).join(Order).filter(Order.created_at >= last_week).scalar() or 0

    # Monthly usage
    monthly_usage = db.session.query(
        func.sum(OrderItem.quantity)
    ).join(Order).filter(Order.created_at >= last_month).scalar() or 0

    # Top used items
    top_items = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.quantity * Product.price).label('total_cost')
    ).join(OrderItem).join(Order).filter(Order.created_at >= last_month).group_by(Product.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()

    # Recent expenditures
    recent_expenditures = Expenditure.query.order_by(Expenditure.date.desc()).limit(5).all()

    # Total expenditure
    total_expenditure = db.session.query(func.sum(Expenditure.amount)).scalar() or 0

    # Order counts (this was missing in the previous version)
    order_counts = db.session.query(Order.status, db.func.count(Order.id).label('count')).group_by(Order.status).all()
    order_counts_list = [{'status': status, 'count': count} for status, count in order_counts]

    return render_template(
        'reports.html', 
        low_stock=low_stock,
        total_inventory_value=total_inventory_value,
        weekly_usage=weekly_usage,
        monthly_usage=monthly_usage,
        top_items=top_items,
        recent_expenditures=recent_expenditures,
        total_expenditure=total_expenditure,
        order_counts=order_counts_list
    )

@app.route('/api/chart-data')
@login_required
def chart_data():
    # Fetch data for charts
    usage_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.sum(OrderItem.quantity).label('total_usage')
    ).join(OrderItem).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()

    expenditure_data = db.session.query(
        Expenditure.date,
        func.sum(Expenditure.amount).label('total_expenditure')
    ).group_by(Expenditure.date).order_by(Expenditure.date).all()

    category_data = db.session.query(
        Category.name,
        func.count(Product.id).label('count')
    ).join(Product).group_by(Category.id).all()

    stock_level_data = db.session.query(
        Product.name,
        Product.quantity.label('current_stock'),
        Product.low_stock_threshold.label('threshold')
    ).order_by(Product.quantity).limit(10).all()

    return jsonify({
        'usage': [{'date': str(item.date), 'total': int(item.total_usage)} for item in usage_data],
        'expenditures': [{'date': str(item.date), 'total': float(item.total_expenditure)} for item in expenditure_data],
        'categories': [{'name': item.name, 'count': int(item.count)} for item in category_data],
        'stock_levels': [{'name': item.name, 'current_stock': int(item.current_stock), 'threshold': int(item.threshold)} for item in stock_level_data]
    })

@app.route('/users/edit/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user route."""
    log_user_activity(f'edited user {user_id}')
    user = User.query.get_or_404(user_id)
    if request.method == 'POST':
        user.name = request.form.get('name')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        db.session.commit()
        flash('User updated successfully')
        return redirect(url_for('users'))
    return render_template('edit_user.html', user=user)

@app.route('/users/delete/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user route."""
    log_user_activity(f'deleted user {user_id}')
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully')
    return redirect(url_for('users'))

@app.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@supervisor_required
def edit_product(product_id):
    """Edit product route."""
    log_user_activity(f'edited product {product_id}')
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form.get('name')
        product.description = request.form.get('description')
        product.quantity = request.form.get('quantity')
        product.price = request.form.get('price')
        product.low_stock_threshold = request.form.get('low_stock_threshold')
        product.category_id = request.form.get('category_id')
        db.session.commit()
        flash('Product updated successfully')
        return redirect(url_for('products'))
    categories = Category.query.all()
    return render_template('edit_product.html', product=product, categories=categories)

@app.route('/products/delete/<int:product_id>', methods=['POST'])
@supervisor_required
def delete_product(product_id):
    """Delete product route."""
    log_user_activity(f'deleted product {product_id}')
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash('Product deleted successfully')
    return redirect(url_for('products'))

@app.route('/categories/edit/<int:category_id>', methods=['GET', 'POST'])
@manager_required
def edit_category(category_id):
    """Edit category route."""
    log_user_activity(f'edited category {category_id}')
    category = Category.query.get_or_404(category_id)
    if request.method == 'POST':
        category.name = request.form.get('name')
        category.description = request.form.get('description')
        db.session.commit()
        flash('Category updated successfully')
        return redirect(url_for('categories'))
    return render_template('edit_category.html', category=category)

@app.route('/categories/delete/<int:category_id>', methods=['POST'])
@manager_required
def delete_category(category_id):
    """Delete category route."""
    log_user_activity(f'deleted category {category_id}')
    category = Category.query.get_or_404(category_id)
    db.session.delete(category)
    db.session.commit()
    flash('Category deleted successfully')
    return redirect(url_for('categories'))

@app.route('/user-activity')
@admin_required
def user_activity():
    """User  activity route."""
    activities = UserActivity.query.join(User).all()  # Join with User to get user names
    return render_template('user_activity.html', activities=activities)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True,host="0.0.0.0", port=5000)