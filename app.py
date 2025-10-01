from flask import Flask, request, jsonify, render_template, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///shop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    orders = db.relationship('Order', backref='customer', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.String(200))
    products = db.relationship('Product', backref='category', lazy=True)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    image_url = db.Column(db.String(255), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Float, nullable=False)
    gst = db.Column(db.Float, nullable=False)
    grand_total = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, completed, cancelled
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route('/')
def index():
    categories = Category.query.all()
    return render_template('index.html', categories=categories)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        user = User(
            username=username,
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/cart')
@login_required
def cart():
    return render_template('cart.html')

# API Endpoints
@app.route('/api/products', methods=['GET'])
def get_products():
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('search', '')
    
    query = Product.query.filter_by(is_active=True)
    
    if category_id:
        query = query.filter_by(category_id=category_id)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.all()
    return jsonify([
        {
            'id': p.id, 
            'name': p.name, 
            'description': p.description,
            'price': p.price, 
            'stock': p.stock, 
            'image_url': p.image_url,
            'category': p.category.name if p.category else None
        }
        for p in products
    ])

@app.route('/api/cart/add', methods=['POST'])
@login_required
def add_to_cart():
    data = request.json
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)
    
    product = Product.query.get_or_404(product_id)
    
    if product.stock < quantity:
        return jsonify({'error': 'Insufficient stock'}), 400
    
    # Store cart in session
    cart = session.get('cart', {})
    if str(product_id) in cart:
        cart[str(product_id)] += quantity
    else:
        cart[str(product_id)] = quantity
    
    session['cart'] = cart
    return jsonify({'message': 'Added to cart', 'cart_count': len(cart)})

@app.route('/api/cart', methods=['GET'])
@login_required
def get_cart():
    cart = session.get('cart', {})
    cart_items = []
    total = 0
    
    for product_id, quantity in cart.items():
        product = Product.query.get(product_id)
        if product and product.is_active:
            item_total = product.price * quantity
            cart_items.append({
                'product_id': product.id,
                'name': product.name,
                'price': product.price,
                'quantity': quantity,
                'total': item_total,
                'image_url': product.image_url,
                'stock': product.stock
            })
            total += item_total
    
    return jsonify({
        'items': cart_items,
        'total': total,
        'gst': round(total * 0.18, 2),
        'grand_total': round(total * 1.18, 2)
    })

@app.route('/api/cart/update', methods=['POST'])
@login_required
def update_cart():
    data = request.json
    product_id = str(data.get('product_id'))
    quantity = data.get('quantity', 0)
    
    cart = session.get('cart', {})
    
    if quantity <= 0:
        cart.pop(product_id, None)
    else:
        product = Product.query.get(product_id)
        if product and product.stock >= quantity:
            cart[product_id] = quantity
        else:
            return jsonify({'error': 'Insufficient stock'}), 400
    
    session['cart'] = cart
    return jsonify({'message': 'Cart updated'})

@app.route('/api/checkout', methods=['POST'])
@login_required
def checkout():
    cart = session.get('cart', {})
    if not cart:
        return jsonify({'error': 'Cart is empty'}), 400
    
    # Validate stock and calculate totals
    items = []
    subtotal = 0
    
    for product_id, quantity in cart.items():
        product = Product.query.get(product_id)
        if not product or product.stock < quantity:
            return jsonify({'error': f'Insufficient stock for {product.name if product else "Unknown"}'}), 400
        
        item_total = product.price * quantity
        subtotal += item_total
        items.append({
            'product': product,
            'quantity': quantity,
            'price': product.price,
            'total': item_total
        })
    
    gst = round(subtotal * 0.18, 2)
    grand_total = subtotal + gst
    
    # Create order
    order = Order(
        user_id=current_user.id,
        total_amount=subtotal,
        gst=gst,
        grand_total=grand_total,
        status='completed'
    )
    db.session.add(order)
    db.session.flush()
    
    # Create order items and update stock
    for item in items:
        item['product'].stock -= item['quantity']
        order_item = OrderItem(
            order_id=order.id,
            product_id=item['product'].id,
            quantity=item['quantity'],
            price=item['price']
        )
        db.session.add(order_item)
    
    db.session.commit()
    
    # Clear cart
    session.pop('cart', None)
    
    return jsonify({
        'order_id': order.id,
        'bill': {
            'items': [
                {
                    'name': item['product'].name,
                    'quantity': item['quantity'],
                    'price': item['price'],
                    'total': item['total']
                }
                for item in items
            ],
            'subtotal': subtotal,
            'gst': gst,
            'grand_total': grand_total
        }
    })

@app.route('/api/categories', methods=['GET'])
def get_categories():
    categories = Category.query.all()
    return jsonify([
        {'id': c.id, 'name': c.name, 'description': c.description}
        for c in categories
    ])

@app.route('/orders')
@login_required
def orders():
    return render_template('orders.html')

@app.route('/api/orders', methods=['GET'])
@login_required
def get_orders():
    if current_user.is_admin:
        orders = Order.query.order_by(Order.date.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.date.desc()).all()
    
    return jsonify([
        {
            'id': order.id,
            'date': order.date.strftime('%Y-%m-%d %H:%M:%S'),
            'total_amount': order.total_amount,
            'gst': order.gst,
            'grand_total': order.grand_total,
            'status': order.status,
            'customer': order.customer.username if current_user.is_admin else None,
            'items': [
                {
                    'product': item.product.name,
                    'quantity': item.quantity,
                    'price': item.price
                } for item in order.items
            ]
        }
        for order in orders
    ])





# Admin routes
@app.route('/admin')
@login_required
def admin_panel():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('admin.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('index'))
    return render_template('dashboard.html')

# Admin API endpoints
@app.route('/api/admin/products', methods=['GET'])
@login_required
def api_get_products():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    products = Product.query.all()
    return jsonify([
        {
            'id': p.id, 
            'name': p.name, 
            'description': p.description,
            'price': p.price, 
            'stock': p.stock, 
            'image_url': p.image_url,
            'category': p.category.name if p.category else None,
            'is_active': p.is_active
        }
        for p in products
    ])

@app.route('/api/admin/products', methods=['POST'])
@login_required
def api_add_product():
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    data = request.json
    name = data.get('name')
    description = data.get('description', '')
    price = data.get('price')
    stock = data.get('stock')
    image_url = data.get('image_url')
    category_id = data.get('category_id')
    
    if not name or price is None or stock is None:
        return jsonify({'error': 'Missing required fields'}), 400
    
    product = Product(
        name=name,
        description=description,
        price=price,
        stock=stock,
        image_url=image_url,
        category_id=category_id
    )
    db.session.add(product)
    db.session.commit()
    return jsonify({'message': 'Product added', 'id': product.id})

@app.route('/api/admin/products/<int:product_id>', methods=['PUT'])
@login_required
def api_edit_product(product_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = Product.query.get_or_404(product_id)
    data = request.json
    
    product.name = data.get('name', product.name)
    product.description = data.get('description', product.description)
    product.price = data.get('price', product.price)
    product.stock = data.get('stock', product.stock)
    product.image_url = data.get('image_url', product.image_url)
    product.category_id = data.get('category_id', product.category_id)
    product.is_active = data.get('is_active', product.is_active)
    
    db.session.commit()
    return jsonify({'message': 'Product updated'})

@app.route('/api/admin/products/<int:product_id>', methods=['DELETE'])
@login_required
def api_delete_product(product_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Access denied'}), 403
    
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    return jsonify({'message': 'Product deleted'})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        # Create admin user if not exists
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@shop.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
        
        # Create default categories
        if Category.query.count() == 0:
            categories = [
                Category(name='Electronics', description='Electronic devices and gadgets'),
                Category(name='Appliances', description='Home appliances'),
                Category(name='Kitchen', description='Kitchen and cooking equipment'),
                Category(name='Gaming', description='Gaming consoles and accessories')
            ]
            db.session.bulk_save_objects(categories)
        
        # Create sample products if none exist
        if Product.query.count() == 0:
            electronics_cat = Category.query.filter_by(name='Electronics').first()
            appliances_cat = Category.query.filter_by(name='Appliances').first()
            kitchen_cat = Category.query.filter_by(name='Kitchen').first()
            
            products = [
                Product(
                    name='Smart TV 55"',
                    description='4K Ultra HD Smart TV with HDR',
                    price=45000,
                    stock=15,
                    image_url='https://images.unsplash.com/photo-1567690187548-f07b1d7bf5a9?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8MTV8fHR2fGVufDB8fDB8fHww',
                    category_id=electronics_cat.id
                ),
                Product(
                    name='Refrigerator',
                    description='Double door refrigerator with frost-free technology',
                    price=25000,
                    stock=10,
                    image_url='https://images.unsplash.com/photo-1649518755041-651c29b56309?q=80&w=687&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D',
                    category_id=appliances_cat.id
                ),
                Product(
                    name='Electric Cooker',
                    description='5L electric pressure cooker with multiple cooking modes',
                    price=3500,
                    stock=25,
                    image_url='https://images.unsplash.com/photo-1544233726-9f1d2b27be8b?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Nnx8Y29va2VyfGVufDB8fDB8fHww',
                    category_id=kitchen_cat.id
                ),
                Product(
                    name='Gaming Console',
                    description='Next-gen gaming console with wireless controller',
                    price=35000,
                    stock=8,
                    image_url='https://images.unsplash.com/photo-1486401899868-0e435ed85128?w=600&auto=format&fit=crop&q=60&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxzZWFyY2h8Mnx8Z2FtaW5nfGVufDB8fDB8fHww',
                    category_id=electronics_cat.id
                ),
                Product(
                    name='Washing Machine',
                    description='Front load washing machine with 8kg capacity',
                    price=22000,
                    stock=12,
                    image_url='https://media.istockphoto.com/id/1137138120/photo/photo-of-white-washing-machine-with-soft-and-fresh-bright-towels-on-top-standing-isolated.webp?a=1&b=1&s=612x612&w=0&k=20&c=NM7NdrjN62USl38qOJdCi8GQauFYjSYE6Xy2V4L7HtU=',
                    category_id=appliances_cat.id
                )
            ]
            db.session.bulk_save_objects(products)
        
        db.session.commit()
    
    app.run(debug=True)