import os
import secrets
from datetime import datetime as dt, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators, IntegerField, FloatField, TextAreaField, FileField
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect, generate_csrf, validate_csrf

# App setup
app = Flask(__name__)
# Fixed secret keys (generate your own)
app.config['SECRET_KEY'] = '79537b3e0a7a5a4a6d6b2a7d4f3a2c5a'
app.config['WTF_CSRF_SECRET_KEY'] = '49537b3e0a7a5a4a6d6b2a7d4f3a2c5b'

# CSRF configuration
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_TIME_LIMIT'] = 3600  # 1 hour
app.config['WTF_CSRF_SSL_STRICT'] = False  # Set to True in production with HTTPS

# Get absolute path to the project directory
basedir = os.path.abspath(os.path.dirname(__file__))

# Database configuration
db_path = os.path.join(basedir, 'instance', 'stockbit.db')
# Replace database configuration with:
if os.environ.get('DATABASE_URL'):
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL'].replace("postgres://", "postgresql://", 1)
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024  # 2MB max upload
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Ensure directories exist
os.makedirs(os.path.dirname(db_path), exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
csrf = CSRFProtect(app)  # CSRF protection

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    business_name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    is_premium = db.Column(db.Boolean, default=False)
    premium_since = db.Column(db.DateTime)
    phone = db.Column(db.String(20))
    subscription_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)  # Add this line

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    quantity = db.Column(db.Integer, default=0)
    reorder_level = db.Column(db.Integer, default=5)
    cost_price = db.Column(db.Float)
    sale_price = db.Column(db.Float)
    last_updated = db.Column(db.DateTime, default=dt.utcnow)
    barcode = db.Column(db.String(50))

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sale_price = db.Column(db.Float, nullable=False)
    sale_date = db.Column(db.DateTime, default=dt.utcnow)
    product = db.relationship('Product', backref='sales')

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    contact = db.Column(db.String(100))
    email = db.Column(db.String(100))

class PaymentVerification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_id = db.Column(db.String(100), nullable=False)
    screenshot = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=dt.utcnow)
    user = db.relationship('User', backref='payments')

# Forms
class RegistrationForm(FlaskForm):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Email(), validators.Length(min=6, max=120)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Confirm Password')
    business_name = StringField('Business Name', [validators.Length(min=2, max=100)])
    phone = StringField('Phone Number', [validators.Length(min=10, max=15)])

class LoginForm(FlaskForm):
    username = StringField('Username', [validators.DataRequired()])
    password = PasswordField('Password', [validators.DataRequired()])

class ProductForm(FlaskForm):
    name = StringField('Product Name', [validators.Length(min=2, max=100)])
    description = TextAreaField('Description')
    quantity = IntegerField('Quantity', [validators.NumberRange(min=0)])
    reorder_level = IntegerField('Reorder Level', [validators.NumberRange(min=1)])
    cost_price = FloatField('Cost Price', [validators.NumberRange(min=0)])
    sale_price = FloatField('Sale Price', [validators.NumberRange(min=0)])
    barcode = StringField('Barcode')

class SupplierForm(FlaskForm):
    name = StringField('Supplier Name', [validators.Length(min=2, max=100)])
    contact = StringField('Contact Info')
    email = StringField('Email', [validators.Email()])

class PaymentVerificationForm(FlaskForm):
    amount = FloatField('Amount Paid', [validators.NumberRange(min=5, message="Minimum amount is ₦500")])
    transaction_id = StringField('Transaction ID', [validators.DataRequired()])
    screenshot = FileField('Payment Screenshot')
class AdminUserForm(FlaskForm):
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Email(), validators.Length(min=6, max=120)])
    business_name = StringField('Business Name', [validators.Length(min=2, max=100)])
    phone = StringField('Phone Number', [validators.Length(min=10, max=15)])
    is_premium = ('Premium User')
    subscription_active = ('Subscription Active')
    is_admin = ('Administrator')

# Initialize database
with app.app_context():
    db.create_all()
    print(f"Database initialized at: {db_path}")

# Helper functions
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# CSRF Protection Setup
@app.before_request
def check_csrf():
    # Skip CSRF validation for these routes
    exempt_routes = ['logout', 'delete_product', 'delete_supplier']
    if request.endpoint in exempt_routes:
        return
    
    # Validate CSRF for state-changing methods
    if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        csrf_token = request.form.get('csrf_token')
        if not csrf_token:
            flash('CSRF token is missing', 'danger')
            return redirect(request.referrer or url_for('dashboard'))
        try:
            validate_csrf(csrf_token)
        except:
            flash('Invalid CSRF token. Please refresh the page and try again.', 'danger')
            return redirect(request.referrer or url_for('dashboard'))

@app.after_request
def set_csrf_cookie(response):
    # Set CSRF token in cookie for JavaScript access
    response.set_cookie('csrf_token', generate_csrf())
    return response

# Authentication Routes
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = generate_password_hash(form.password.data)
        business_name = form.business_name.data
        phone = form.phone.data

        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'danger')
            return redirect(url_for('register'))

        new_user = User(
            username=username,
            email=email,
            password=password,
            business_name=business_name,
            phone=phone
        )
        db.session.add(new_user)
        db.session.commit()

        flash('Account created! Please login', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
            
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Application Routes
@app.route('/dashboard')
@login_required
def dashboard():
    # Get all products for this user
    all_products = Product.query.filter_by(user_id=current_user.id).all()

    # Get low-stock products
    low_stock = Product.query.filter(
        Product.user_id == current_user.id,
        Product.quantity <= Product.reorder_level
    ).all()

    # Get recent sales
    recent_sales = Sale.query.join(Product).filter(
        Product.user_id == current_user.id
    ).order_by(Sale.sale_date.desc()).limit(5).all()

    # Calculate inventory value
    inventory_value = 0
    for product in all_products:
        if product.cost_price and product.quantity:
            inventory_value += product.quantity * product.cost_price

    # Calculate total products
    total_products = len(all_products)

    return render_template('dashboard.html',
                           low_stock=low_stock,
                           recent_sales=recent_sales,
                           inventory_value=round(inventory_value, 2),
                           total_products=total_products)

@app.route('/products')
@login_required
def products():
    all_products = Product.query.filter_by(user_id=current_user.id).all()
    return render_template('products.html', products=all_products)

@app.route('/add_product', methods=['GET', 'POST'])
@login_required
def add_product():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Product(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            quantity=form.quantity.data,
            reorder_level=form.reorder_level.data,
            cost_price=form.cost_price.data,
            sale_price=form.sale_price.data,
            barcode=form.barcode.data
        )
        db.session.add(new_product)
        db.session.commit()
        flash('Product added successfully!', 'success')
        return redirect(url_for('products'))
    return render_template('add_product.html', form=form)

@app.route('/edit_product/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if product.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('products'))

    form = ProductForm(obj=product)
    if form.validate_on_submit():
        form.populate_obj(product)
        product.last_updated = dt.utcnow()
        db.session.commit()
        flash('Product updated!', 'success')
        return redirect(url_for('products'))

    return render_template('edit_product.html', form=form, product=product)

@app.route('/delete_product/<int:id>')
@login_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    if product.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('products'))

    db.session.delete(product)
    db.session.commit()
    flash('Product deleted', 'success')
    return redirect(url_for('products'))

@app.route('/add_sale/<int:product_id>', methods=['POST'])
@login_required
def add_sale(product_id):
    product = Product.query.get_or_404(product_id)
    if product.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('products'))

    try:
        quantity = int(request.form['quantity'])
    except ValueError:
        flash('Invalid quantity', 'danger')
        return redirect(url_for('products'))

    if quantity > product.quantity:
        flash('Not enough stock!', 'danger')
        return redirect(url_for('products'))

    # Update product quantity
    product.quantity -= quantity
    product.last_updated = dt.utcnow()

    # Record sale
    new_sale = Sale(
        product_id=product_id,
        quantity=quantity,
        sale_price=product.sale_price
    )
    db.session.add(new_sale)
    db.session.commit()

    flash('Sale recorded!', 'success')
    return redirect(url_for('products'))

@app.route('/suppliers')
@login_required
def suppliers():
    all_suppliers = Supplier.query.filter_by(user_id=current_user.id).all()
    return render_template('suppliers.html', suppliers=all_suppliers)

@app.route('/add_supplier', methods=['GET', 'POST'])
@login_required
def add_supplier():
    form = SupplierForm()
    if form.validate_on_submit():
        new_supplier = Supplier(
            user_id=current_user.id,
            name=form.name.data,
            contact=form.contact.data,
            email=form.email.data
        )
        db.session.add(new_supplier)
        db.session.commit()
        flash('Supplier added!', 'success')
        return redirect(url_for('suppliers'))
    return render_template('add_supplier.html', form=form)

@app.route('/edit_supplier/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if supplier.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('suppliers'))

    form = SupplierForm(obj=supplier)
    if form.validate_on_submit():
        form.populate_obj(supplier)
        db.session.commit()
        flash('Supplier updated!', 'success')
        return redirect(url_for('suppliers'))

    return render_template('edit_supplier.html', form=form, supplier=supplier)

@app.route('/delete_supplier/<int:id>')
@login_required
def delete_supplier(id):
    supplier = Supplier.query.get_or_404(id)
    if supplier.user_id != current_user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('suppliers'))

    db.session.delete(supplier)
    db.session.commit()
    flash('Supplier deleted', 'success')
    return redirect(url_for('suppliers'))

@app.route('/reports')
@login_required
def reports():
    # Get all products for this user
    all_products = Product.query.filter_by(user_id=current_user.id).all()
    total_products = len(all_products)  # Add this line

    # Top selling products
    top_products = db.session.query(
        Product.name,
        db.func.sum(Sale.quantity).label('total_sold')
    ).join(Sale).filter(
        Product.user_id == current_user.id
    ).group_by(Product.id).order_by(db.desc('total_sold')).limit(5).all()

    # Sales revenue
    revenue = db.session.query(
        db.func.sum(Sale.quantity * Sale.sale_price)
    ).join(Product).filter(
        Product.user_id == current_user.id
    ).scalar() or 0

    # Inventory value
    inventory_value = 0
    for product in all_products:
        if product.cost_price and product.quantity:
            inventory_value += product.quantity * product.cost_price

    # Low stock items
    low_stock_count = Product.query.filter(
        Product.user_id == current_user.id,
        Product.quantity <= Product.reorder_level
    ).count()

    # Initialize premium variables to None
    profit_margin = None
    best_category = None
    stock_turnover = None
    
    # Only calculate premium metrics for premium users
    if current_user.is_premium:
        # Calculate profit margin
        total_cost = sum(p.cost_price * p.quantity for p in all_products)
        profit_margin = ((revenue - total_cost) / revenue * 100) if revenue > 0 else 0
        
        # Find best selling product category
        best_category = top_products[0].name if top_products else "No data"
        
        # Calculate stock turnover
        average_inventory = inventory_value / 2  # Simplified calculation
        stock_turnover = revenue / average_inventory if average_inventory > 0 else 0

    return render_template('reports.html',
                           top_products=top_products,
                           revenue=round(revenue, 2),
                           inventory_value=round(inventory_value, 2),
                           profit_margin=round(profit_margin, 1) if profit_margin is not None else None,
                           best_category=best_category,
                           stock_turnover=round(stock_turnover, 1) if stock_turnover is not None else None,
                           low_stock_count=low_stock_count,
                           total_products=total_products)  # Added this line
# Subscription Management
@app.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html')

# Premium Features
@app.route('/premium')
@login_required
def premium_features():
    return render_template('premium.html')

@app.route('/upgrade/instructions')
@login_required
def upgrade_instructions():
    return render_template('upgrade_instructions.html')

@app.route('/upgrade/verify', methods=['GET', 'POST'])
@login_required
def upgrade_verify():
    form = PaymentVerificationForm()
    if form.validate_on_submit():
        # Handle file upload
        screenshot = None
        if 'screenshot' in request.files:
            file = request.files['screenshot']
            if file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                screenshot = filename

        # Create payment verification record
        payment = PaymentVerification(
            user_id=current_user.id,
            amount=float(form.amount.data),
            transaction_id=form.transaction_id.data,
            screenshot=screenshot,
            status='pending'
        )
        db.session.add(payment)
        db.session.commit()

        flash('Payment verification submitted! We will contact you shortly.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('upgrade_verify.html', form=form)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Admin routes
@app.route('/admin/payments')
@login_required
def admin_payments():
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))

    payments = PaymentVerification.query.filter_by(status='pending').all()
    return render_template('admin_payments.html', payments=payments)

@app.route('/admin/approve/<int:payment_id>', methods=['POST'])
@login_required
def admin_approve(payment_id):
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))

    payment = PaymentVerification.query.get_or_404(payment_id)
    user = payment.user
    user.is_premium = True
    user.subscription_active = True
    user.premium_since = dt.utcnow()
    payment.status = 'approved'
    db.session.commit()

    flash(f'Premium access granted to {user.username}', 'success')
    return redirect(url_for('admin_payments'))

@app.route('/admin/reject/<int:payment_id>', methods=['POST'])
@login_required
def admin_reject(payment_id):
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))

    payment = PaymentVerification.query.get_or_404(payment_id)
    payment.status = 'rejected'
    db.session.commit()

    flash('Payment rejected', 'warning')
    return redirect(url_for('admin_payments'))

@app.route('/admin/users')
@login_required
def admin_users():
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('admin_users.html', users=users)

# Admin user management
@app.route('/admin/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    form = AdminUserForm(obj=user)
    
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin_edit_user.html', form=form, user=user)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    # Prevent deleting yourself
    if user.id == current_user.id:
        flash('You cannot delete your own account!', 'danger')
        return redirect(url_for('admin_users'))
    
    # Prevent deleting the last admin
    if user.is_admin and User.query.filter_by(is_admin=True).count() == 1:
        flash('Cannot delete the last admin account!', 'danger')
        return redirect(url_for('admin_users'))
    
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/cancel_subscription/<int:user_id>', methods=['POST'])
@login_required
def admin_cancel_subscription(user_id):
    if not current_user.is_admin:
        flash('Admin access only', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    if user.is_premium:
        user.is_premium = False
        user.subscription_active = False
        db.session.commit()
        flash(f'Subscription canceled for {user.username}', 'success')
    else:
        flash('User is not a premium subscriber', 'warning')
    
    return redirect(url_for('admin_users'))

# Custom template filter
@app.template_filter('currency')
def currency_format(value):
    if value is None:
        return "₦0.00"
    return "₦{:,.2f}".format(value)

@app.context_processor
def inject_common_data():
    return {
        'admin_phone': '07072127949',
        'admin_whatsapp': '07072127949',
        'payment_account': '7010698264 (Opay, Prince Ekine)',
        'csrf_token': generate_csrf
    }

# ... [rest of your code] ...

if __name__ == '__main__':
    # Get port from environment variable or default to 5000 for local development
    port = int(os.environ.get("PORT", 5000))
    
    # Run the application
    app.run(
        host='0.0.0.0',  # Bind to all network interfaces
        port=port,        # Use the port specified by Render
        debug=False       # Always set to False in production
    )
