from flask import Flask, render_template_string, abort, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
import logging
import uuid
from functools import wraps

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///xads.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Request ID middleware
@app.before_request
def before_request():
    g.request_id = str(uuid.uuid8())[:8]
    logger.info(f"[{g.request_id}] {request.method} {request.path}")

@app.after_request
def after_request(response):
    logger.info(f"[{g.request_id}] Status: {response.status_code}")
    response.headers['X-Request-ID'] = g.request_id
    return response

# Health check endpoint
@app.route('/health')
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'healthy', 'request_id': g.request_id}), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 503

# Global error handlers
@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Resource not found', 'request_id': g.request_id}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({'error': 'Internal server error', 'request_id': g.request_id}), 500

# Database Models
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ads = db.relationship('Ad', backref='category', lazy=True)

class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_text = db.Column(db.Text, nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.String(50), nullable=False)
    clicks = db.Column(db.Integer, default=0)
    impressions = db.Column(db.Integer, default=0)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    status = db.Column(db.String(20), default='active')  # active, paused, completed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ClickEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ad_id = db.Column(db.Integer, db.ForeignKey('ad.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    source = db.Column(db.String(50))  # api, web, direct

# Create database tables
with app.app_context():
    db.create_all()
    # Add default categories if none exist
    if Category.query.count() == 0:
        categories = [
            Category(name='Electronics'),
            Category(name='Fashion'),
            Category(name='Home & Garden'),
            Category(name='Sports'),
            Category(name='Food & Beverage')
        ]
        db.session.add_all(categories)
        db.session.commit()

    # Add sample ads if database is empty
    if Ad.query.count() == 0:
        sample_ads = [
            Ad(post_text="Check out this amazing new product!", product_name="Wireless Earbuds Pro", price="$79.99", clicks=1250, impressions=15000, category_id=1, status='active'),
            Ad(post_text="Summer vibes with our latest collection", product_name="Beachwear Set", price="$49.99", clicks=890, impressions=8000, category_id=2, status='active'),
            Ad(post_text="Upgrade your workspace today", product_name="Ergonomic Desk Chair", price="$199.99", clicks=567, impressions=5000, category_id=3, status='active'),
        ]
        db.session.add_all(sample_ads)
        db.session.commit()

# HTML Templates
BASE_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }} - X Ad Manager</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 0; background: #f0f2f5; }
        .navbar { background: #1da1f2; padding: 15px 30px; display: flex; justify-content: space-between; align-items: center; }
        .navbar a { color: white; text-decoration: none; margin: 0 15px; font-weight: 500; }
        .navbar .brand { font-size: 1.3em; font-weight: bold; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .card { background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1, h2, h3 { color: #333; margin-bottom: 15px; }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }
        .stat-card { background: white; padding: 20px; border-radius: 10px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .stat-number { font-size: 2em; font-weight: bold; color: #1da1f2; }
        .stat-label { color: #666; margin-top: 5px; }
        .ad-card { border-left: 4px solid #1da1f2; }
        .ad-card.paused { border-left-color: #ffc107; }
        .ad-card.completed { border-left-color: #28a745; }
        .product-name { color: #1da1f2; font-weight: bold; font-size: 1.2em; }
        .price { color: #28a745; font-size: 1.3em; font-weight: bold; }
        .meta { color: #666; font-size: 0.9em; margin-top: 10px; }
        .badge { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: bold; }
        .badge-active { background: #e3f2fd; color: #1976d2; }
        .badge-paused { background: #fff3e0; color: #f57c00; }
        .badge-completed { background: #e8f5e9; color: #388e3c; }
        .btn { padding: 10px 20px; border: none; border-radius: 6px; cursor: pointer; font-weight: 500; text-decoration: none; display: inline-block; }
        .btn-primary { background: #1da1f2; color: white; }
        .btn-primary:hover { background: #1a91da; }
        .btn-secondary { background: #657786; color: white; }
        .btn-danger { background: #e0245e; color: white; }
        .btn-success { background: #28a745; color: white; }
        .btn-sm { padding: 5px 12px; font-size: 0.85em; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 500; }
        .form-group input, .form-group textarea, .form-group select { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-size: 1em; }
        .form-group textarea { min-height: 100px; }
        .actions { display: flex; gap: 10px; margin-top: 15px; }
        .search-bar { display: flex; gap: 10px; margin-bottom: 20px; }
        .search-bar input { flex: 1; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 1em; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #eee; }
        th { background: #f8f9fa; font-weight: 600; }
        .chart-container { height: 300px; margin: 20px 0; }
        .empty-state { text-align: center; padding: 60px 20px; color: #666; }
    </style>
</head>
<body>
    <nav class="navbar">
        <div>
            <a href="/" class="brand">X Ad Manager</a>
        </div>
        <div>
            <a href="/">Dashboard</a>
            <a href="/ads">Ads</a>
            <a href="/ads/new">New Ad</a>
            <a href="/analytics">Analytics</a>
            <a href="/categories">Categories</a>
        </div>
    </nav>
    <div class="container">
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route('/')
def dashboard():
    total_ads = Ad.query.count()
    active_ads = Ad.query.filter_by(status='active').count()
    total_clicks = db.session.query(db.func.sum(Ad.clicks)).scalar() or 0
    total_impressions = db.session.query(db.func.sum(Ad.impressions)).scalar() or 0
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    recent_ads = Ad.query.order_by(Ad.created_at.desc()).limit(5).all()

    content = f"""
        <h1>Dashboard</h1>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{total_ads}</div>
                <div class="stat-label">Total Ads</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{active_ads}</div>
                <div class="stat-label">Active Campaigns</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{total_clicks:,}</div>
                <div class="stat-label">Total Clicks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{ctr:.2f}%</div>
                <div class="stat-label">Avg CTR</div>
            </div>
        </div>

        <div class="card">
            <h2>Recent Campaigns</h2>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Status</th>
                        <th>Clicks</th>
                        <th>CTR</th>
                    </tr>
                </thead>
                <tbody>
    """
    for ad in recent_ads:
        ad_ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
        cat_name = ad.category.name if ad.category else 'Uncategorized'
        content += f"""
                    <tr>
                        <td><a href="/ads/{ad.id}">{ad.product_name}</a></td>
                        <td>{cat_name}</td>
                        <td><span class="badge badge-{ad.status}">{ad.status}</span></td>
                        <td>{ad.clicks:,}</td>
                        <td>{ad_ctr:.2f}%</td>
                    </tr>
        """
    content += """
                </tbody>
            </table>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title="Dashboard", content=content)

@app.route('/ads')
def ads_list():
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)
    status_filter = request.args.get('status', '')

    query = Ad.query
    if search:
        query = query.filter(
            (Ad.product_name.ilike(f'%{search}%')) |
            (Ad.post_text.ilike(f'%{search}%'))
        )
    if category_id:
        query = query.filter_by(category_id=category_id)
    if status_filter:
        query = query.filter_by(status=status_filter)

    ads = query.order_by(Ad.created_at.desc()).all()
    categories = Category.query.all()

    content = """
        <h1>Ad Campaigns</h1>
        <div class="search-bar">
            <form method="get" style="display:flex;gap:10px;width:100%;">
                <input type="text" name="search" placeholder="Search ads..." value="{search}">
                <select name="category">
                    <option value="">All Categories</option>
    """.format(search=search)

    for cat in categories:
        selected = 'selected' if category_id == cat.id else ''
        content += f'<option value="{cat.id}" {selected}>{cat.name}</option>'

    content += """
                </select>
                <select name="status">
                    <option value="">All Status</option>
                    <option value="active">Active</option>
                    <option value="paused">Paused</option>
                    <option value="completed">Completed</option>
                </select>
                <button type="submit" class="btn btn-primary">Filter</button>
            </form>
        </div>
    """

    if not ads:
        content += '<div class="empty-state"><h3>No ads found</h3><p>Create your first ad campaign to get started!</p><a href="/ads/new" class="btn btn-primary">Create Ad</a></div>'
    else:
        for ad in ads:
            ad_ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
            cat_name = ad.category.name if ad.category else 'Uncategorized'
            content += f"""
        <div class="card ad-card {ad.status}">
            <div style="display:flex;justify-content:space-between;align-items:start;">
                <div>
                    <p class="product-name">{ad.product_name}</p>
                    <p>{ad.post_text}</p>
                    <p class="price">{ad.price}</p>
                    <p class="meta">Category: {cat_name} | Clicks: {ad.clicks:,} | Impressions: {ad.impressions:,} | CTR: {ad_ctr:.2f}%</p>
                </div>
                <div style="text-align:right;">
                    <span class="badge badge-{ad.status}">{ad.status}</span>
                    <div class="actions">
                        <a href="/ads/{ad.id}" class="btn btn-sm btn-primary">View</a>
                        <a href="/ads/{ad.id}/edit" class="btn btn-sm btn-secondary">Edit</a>
                        <a href="/ads/{ad.id}/delete" class="btn btn-sm btn-danger" onclick="return confirm('Delete this ad?')">Delete</a>
                    </div>
                </div>
            </div>
        </div>
            """

    return render_template_string(BASE_TEMPLATE, title="Ads", content=content)

@app.route('/ads/new', methods=['GET', 'POST'])
def ad_create():
    categories = Category.query.all()

    if request.method == 'POST':
        new_ad = Ad(
            post_text=request.form['post_text'],
            product_name=request.form['product_name'],
            price=request.form['price'],
            category_id=request.form.get('category_id', type=int) or None,
            status=request.form.get('status', 'active'),
            clicks=0,
            impressions=0
        )
        db.session.add(new_ad)
        db.session.commit()
        return redirect(url_for('ads_list'))

    content = """
        <h1>Create New Ad Campaign</h1>
        <div class="card">
            <form method="post">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" name="product_name" required placeholder="Enter product name">
                </div>
                <div class="form-group">
                    <label>Post Text</label>
                    <textarea name="post_text" required placeholder="Write your ad copy..."></textarea>
                </div>
                <div class="form-group">
                    <label>Price</label>
                    <input type="text" name="price" required placeholder="$0.00">
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select name="category_id">
                        <option value="">Select Category</option>
    """
    for cat in categories:
        content += f'<option value="{cat.id}">{cat.name}</option>'

    content += """
                    </select>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <option value="active">Active</option>
                        <option value="paused">Paused</option>
                        <option value="completed">Completed</option>
                    </select>
                </div>
                <div class="actions">
                    <button type="submit" class="btn btn-primary">Create Campaign</button>
                    <a href="/ads" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title="New Ad", content=content)

@app.route('/ads/<int:ad_id>')
def ad_detail(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    ad_ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
    cat_name = ad.category.name if ad.category else 'Uncategorized'

    content = f"""
        <h1>{ad.product_name}</h1>
        <div class="card ad-card {ad.status}">
            <p class="product-name" style="font-size:1.5em;">{ad.product_name}</p>
            <p style="font-size:1.2em;margin:15px 0;">"{ad.post_text}"</p>
            <p class="price">{ad.price}</p>
            <p class="meta">Category: {cat_name}</p>
            <div class="stats-grid" style="margin-top:20px;">
                <div class="stat-card">
                    <div class="stat-number">{ad.clicks:,}</div>
                    <div class="stat-label">Clicks</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{ad.impressions:,}</div>
                    <div class="stat-label">Impressions</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{ad_ctr:.2f}%</div>
                    <div class="stat-label">CTR</div>
                </div>
            </div>
            <div class="actions">
                <a href="/ads/{ad.id}/edit" class="btn btn-primary">Edit</a>
                <a href="/ads/{ad.id}/delete" class="btn btn-danger" onclick="return confirm('Delete this ad?')">Delete</a>
                <a href="/ads" class="btn btn-secondary">Back to Ads</a>
            </div>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title=ad.product_name, content=content)

@app.route('/ads/<int:ad_id>/edit', methods=['GET', 'POST'])
def ad_edit(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    categories = Category.query.all()

    if request.method == 'POST':
        ad.product_name = request.form['product_name']
        ad.post_text = request.form['post_text']
        ad.price = request.form['price']
        ad.category_id = int(request.form['category_id']) if request.form['category_id'] else None
        ad.status = request.form['status']
        db.session.commit()
        return redirect(url_for('ad_detail', ad_id=ad.id))

    content = f"""
        <h1>Edit Campaign</h1>
        <div class="card">
            <form method="post">
                <div class="form-group">
                    <label>Product Name</label>
                    <input type="text" name="product_name" required value="{ad.product_name}">
                </div>
                <div class="form-group">
                    <label>Post Text</label>
                    <textarea name="post_text" required>{ad.post_text}</textarea>
                </div>
                <div class="form-group">
                    <label>Price</label>
                    <input type="text" name="price" required value="{ad.price}">
                </div>
                <div class="form-group">
                    <label>Category</label>
                    <select name="category_id">
                        <option value="">Select Category</option>
    """
    for cat in categories:
        selected = 'selected' if ad.category_id == cat.id else ''
        content += f'<option value="{cat.id}" {selected}>{cat.name}</option>'

    status_active = 'selected' if ad.status == 'active' else ''
    status_paused = 'selected' if ad.status == 'paused' else ''
    status_completed = 'selected' if ad.status == 'completed' else ''

    content += f"""
                    </select>
                </div>
                <div class="form-group">
                    <label>Status</label>
                    <select name="status">
                        <option value="active" {status_active}>Active</option>
                        <option value="paused" {status_paused}>Paused</option>
                        <option value="completed" {status_completed}>Completed</option>
                    </select>
                </div>
                <div class="actions">
                    <button type="submit" class="btn btn-success">Save Changes</button>
                    <a href="/ads/{ad.id}" class="btn btn-secondary">Cancel</a>
                </div>
            </form>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title="Edit Ad", content=content)

@app.route('/ads/<int:ad_id>/delete')
def ad_delete(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    return redirect(url_for('ads_list'))

@app.route('/ads/<int:ad_id>/track-click')
def track_click(ad_id):
    """Track a click on an ad"""
    ad = Ad.query.get_or_404(ad_id)
    ad.clicks += 1

    # Record click event
    click_event = ClickEvent(ad_id=ad.id, source=request.args.get('source', 'direct'))
    db.session.add(click_event)
    db.session.commit()

    return jsonify({"success": True, "clicks": ad.clicks})

@app.route('/analytics')
def analytics():
    # Get top performing ads
    top_ads = Ad.query.order_by(Ad.clicks.desc()).limit(10).all()

    # Get category performance
    cat_stats = db.session.query(
        Category.name,
        db.func.sum(Ad.clicks).label('clicks'),
        db.func.sum(Ad.impressions).label('impressions')
    ).join(Ad).group_by(Category.id, Category.name).all()

    # Get click events for today
    today = datetime.utcnow().date()
    today_clicks = ClickEvent.query.filter(
        db.func.date(ClickEvent.timestamp) == today
    ).count()

    total_clicks = db.session.query(db.func.sum(Ad.clicks)).scalar() or 0
    total_impressions = db.session.query(db.func.sum(Ad.impressions)).scalar() or 0
    ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    content = """
        <h1>Analytics Dashboard</h1>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">""" + str(total_clicks) + """</div>
                <div class="stat-label">Total Clicks</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + str(total_impressions) + """</div>
                <div class="stat-label">Total Impressions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + f"{ctr:.2f}%" + """</div>
                <div class="stat-label">Overall CTR</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">""" + str(today_clicks) + """</div>
                <div class="stat-label">Clicks Today</div>
            </div>
        </div>

        <div class="card">
            <h2>Top Performing Ads</h2>
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Clicks</th>
                        <th>Impressions</th>
                        <th>CTR</th>
                    </tr>
                </thead>
                <tbody>
    """

    for ad in top_ads:
        ad_ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
        content += f"""
                    <tr>
                        <td>{ad.product_name}</td>
                        <td>{ad.clicks:,}</td>
                        <td>{ad.impressions:,}</td>
                        <td>{ad_ctr:.2f}%</td>
                    </tr>
        """

    content += """
                </tbody>
            </table>
        </div>

        <div class="card">
            <h2>Performance by Category</h2>
            <table>
                <thead>
                    <tr>
                        <th>Category</th>
                        <th>Clicks</th>
                        <th>Impressions</th>
                        <th>CTR</th>
                    </tr>
                </thead>
                <tbody>
    """

    for cat_name, clicks, impressions in cat_stats:
        cat_ctr = (clicks / impressions * 100) if impressions > 0 else 0
        content += f"""
                    <tr>
                        <td>{cat_name}</td>
                        <td>{clicks:,}</td>
                        <td>{impressions:,}</td>
                        <td>{cat_ctr:.2f}%</td>
                    </tr>
        """

    content += """
                </tbody>
            </table>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title="Analytics", content=content)

@app.route('/categories')
def categories_list():
    categories = Category.query.all()

    content = """
        <h1>Categories</h1>
        <div class="card">
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>Ads Count</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    """

    for cat in categories:
        ads_count = Ad.query.filter_by(category_id=cat.id).count()
        content += f"""
                    <tr>
                        <td>{cat.name}</td>
                        <td>{ads_count}</td>
                        <td><a href="/categories/{cat.id}/ads" class="btn btn-sm btn-primary">View Ads</a></td>
                    </tr>
        """

    content += """
                </tbody>
            </table>
        </div>
        <div class="card">
            <h3>Add New Category</h3>
            <form method="post" action="/categories/new" style="display:flex;gap:10px;">
                <input type="text" name="name" placeholder="Category name" required style="flex:1;">
                <button type="submit" class="btn btn-primary">Add Category</button>
            </form>
        </div>
    """
    return render_template_string(BASE_TEMPLATE, title="Categories", content=content)

@app.route('/categories/new', methods=['POST'])
def category_create():
    name = request.form.get('name')
    if name:
        new_cat = Category(name=name)
        db.session.add(new_cat)
        db.session.commit()
    return redirect(url_for('categories_list'))

@app.route('/categories/<int:cat_id>/ads')
def category_ads(cat_id):
    category = Category.query.get_or_404(cat_id)
    ads = Ad.query.filter_by(category_id=cat_id).all()

    content = f"""
        <h1>Ads in "{category.name}"</h1>
    """

    for ad in ads:
        ad_ctr = (ad.clicks / ad.impressions * 100) if ad.impressions > 0 else 0
        content += f"""
        <div class="card ad-card {ad.status}">
            <p class="product-name">{ad.product_name}</p>
            <p>{ad.post_text}</p>
            <p class="price">{ad.price}</p>
            <p class="meta">Clicks: {ad.clicks:,} | CTR: {ad_ctr:.2f}%</p>
            <a href="/ads/{ad.id}" class="btn btn-primary btn-sm">View Details</a>
        </div>
        """

    if not ads:
        content += '<div class="empty-state"><h3>No ads in this category</h3></div>'

    content += '<p><a href="/categories" class="btn btn-secondary">Back to Categories</a></p>'

    return render_template_string(BASE_TEMPLATE, title=category.name, content=content)

# API Endpoints
@app.route('/api/ads', methods=['GET'])
def api_list_ads():
    ads = Ad.query.all()
    return jsonify([{
        'id': ad.id,
        'post_text': ad.post_text,
        'product_name': ad.product_name,
        'price': ad.price,
        'clicks': ad.clicks,
        'impressions': ad.impressions,
        'status': ad.status,
        'category': ad.category.name if ad.category else None
    } for ad in ads])

@app.route('/api/ads', methods=['POST'])
def api_create_ad():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_fields = ['post_text', 'product_name', 'price']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    new_ad = Ad(
        post_text=data['post_text'],
        product_name=data['product_name'],
        price=data['price'],
        category_id=data.get('category_id'),
        status=data.get('status', 'active')
    )
    db.session.add(new_ad)
    db.session.commit()

    return jsonify({
        "message": "Ad created successfully",
        "ad": {
            'id': new_ad.id,
            'post_text': new_ad.post_text,
            'product_name': new_ad.product_name,
            'price': new_ad.price,
            'status': new_ad.status
        }
    }), 201

@app.route('/api/ads/<int:ad_id>', methods=['GET'])
def api_get_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    return jsonify({
        'id': ad.id,
        'post_text': ad.post_text,
        'product_name': ad.product_name,
        'price': ad.price,
        'clicks': ad.clicks,
        'impressions': ad.impressions,
        'status': ad.status,
        'category': ad.category.name if ad.category else None,
        'created_at': ad.created_at.isoformat()
    })

@app.route('/api/ads/<int:ad_id>', methods=['PUT'])
def api_update_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    data = request.get_json()

    if 'post_text' in data:
        ad.post_text = data['post_text']
    if 'product_name' in data:
        ad.product_name = data['product_name']
    if 'price' in data:
        ad.price = data['price']
    if 'status' in data:
        ad.status = data['status']
    if 'category_id' in data:
        ad.category_id = data['category_id']

    db.session.commit()
    return jsonify({"message": "Ad updated successfully", "ad": {
        'id': ad.id,
        'post_text': ad.post_text,
        'product_name': ad.product_name,
        'price': ad.price,
        'status': ad.status
    }})

@app.route('/api/ads/<int:ad_id>', methods=['DELETE'])
def api_delete_ad(ad_id):
    ad = Ad.query.get_or_404(ad_id)
    db.session.delete(ad)
    db.session.commit()
    return jsonify({"message": "Ad deleted successfully"})

@app.route('/api/analytics')
def api_analytics():
    total_clicks = db.session.query(db.func.sum(Ad.clicks)).scalar() or 0
    total_impressions = db.session.query(db.func.sum(Ad.impressions)).scalar() or 0

    cat_stats = db.session.query(
        Category.name,
        db.func.sum(Ad.clicks).label('clicks'),
        db.func.sum(Ad.impressions).label('impressions')
    ).join(Ad).group_by(Category.id, Category.name).all()

    return jsonify({
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'ctr': (total_clicks / total_impressions * 100) if total_impressions > 0 else 0,
        'category_performance': [{'category': name, 'clicks': clicks, 'impressions': impressions} for name, clicks, impressions in cat_stats]
    })

@app.route('/api/categories', methods=['GET'])
def api_list_categories():
    categories = Category.query.all()
    return jsonify([{
        'id': cat.id,
        'name': cat.name,
        'ads_count': Ad.query.filter_by(category_id=cat.id).count()
    } for cat in categories])

@app.route('/api/categories', methods=['POST'])
def api_create_category():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Missing category name"}), 400

    new_cat = Category(name=data['name'])
    db.session.add(new_cat)
    db.session.commit()

    return jsonify({"message": "Category created", "category": {'id': new_cat.id, 'name': new_cat.name}}), 201

# Enhanced stats endpoint
@app.route('/api/stats')
def api_stats():
    """Enhanced statistics endpoint with more metrics"""
    total_ads = Ad.query.count()
    active_ads = Ad.query.filter_by(status='active').count()
    paused_ads = Ad.query.filter_by(status='paused').count()
    completed_ads = Ad.query.filter_by(status='completed').count()
    
    total_clicks = db.session.query(db.func.sum(Ad.clicks)).scalar() or 0
    total_impressions = db.session.query(db.func.sum(Ad.impressions)).scalar() or 0
    
    return jsonify({
        'total_ads': total_ads,
        'active_ads': active_ads,
        'paused_ads': paused_ads,
        'completed_ads': completed_ads,
        'total_clicks': total_clicks,
        'total_impressions': total_impressions,
        'ctr': round(total_clicks / total_impressions * 100, 2) if total_impressions > 0 else 0,
        'avg_clicks_per_ad': round(total_clicks / total_ads, 2) if total_ads > 0 else 0
    })

if __name__ == '__main__':
    app.run(debug=True)
