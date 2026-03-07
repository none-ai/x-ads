from flask import Flask, render_template_string, abort, request, jsonify

app = Flask(__name__)

# Sample ad data
ads = [
    {"id": 1, "post_text": "Check out this amazing new product!", "product_name": "Wireless Earbuds Pro", "price": "$79.99", "clicks": 1250},
    {"id": 2, "post_text": "Summer vibes with our latest collection", "product_name": "Beachwear Set", "price": "$49.99", "clicks": 890},
    {"id": 3, "post_text": "Upgrade your workspace today", "product_name": "Ergonomic Desk Chair", "price": "$199.99", "clicks": 567},
]

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>{{ title }}</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; }
        h1 { color: #333; }
        .ad-card { background: white; padding: 20px; margin: 20px 0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .product-name { color: #1da1f2; font-weight: bold; font-size: 1.2em; }
        .price { color: #28a745; font-size: 1.1em; }
        .clicks { color: #666; }
        nav { margin-bottom: 30px; }
        nav a { margin-right: 20px; color: #1da1f2; text-decoration: none; }
    </style>
</head>
<body>
    <div class="container">
        <nav>
            <a href="/">Home</a>
            <a href="/ads">All Ads</a>
        </nav>
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route('/')
def home():
    content = """
        <h1>X Ad Format Tester</h1>
        <p>This project demonstrates X's new ad format that connects posts with products.</p>
        <div class="ad-card">
            <h2>New Ad Format: Post-to-Product</h2>
            <p>X is testing a new advertising format that seamlessly connects social posts with shoppable products.</p>
            <p class="product-name">Feature: Direct Product Linking</p>
            <p>Users can now discover and purchase products directly from posts.</p>
        </div>
        <p><a href="/ads">View Active Campaigns</a></p>
    """
    return render_template_string(HTML_TEMPLATE, title="Home", content=content)

@app.route('/ads')
def ads_list():
    ads_html = "<h1>Active Ad Campaigns</h1>"
    for ad in ads:
        ads_html += f"""
        <div class="ad-card">
            <p class="product-name">{ad['product_name']}</p>
            <p>{ad['post_text']}</p>
            <p class="price">{ad['price']}</p>
            <p class="clicks">Clicks: {ad['clicks']}</p>
            <a href="/ads/{ad['id']}">View Details</a>
        </div>
        """
    return render_template_string(HTML_TEMPLATE, title="All Ads", content=ads_html)

@app.route('/ads/<int:ad_id>')
def ad_detail(ad_id):
    ad = next((a for a in ads if a['id'] == ad_id), None)
    if not ad:
        abort(404)

    content = f"""
        <h1>{ad['product_name']}</h1>
        <div class="ad-card">
            <h2>Post Content</h2>
            <p>"{ad['post_text']}"</p>
            <hr>
            <h2>Product Details</h2>
            <p class="product-name">{ad['product_name']}</p>
            <p class="price">Price: {ad['price']}</p>
            <p class="clicks">Total Clicks: {ad['clicks']}</p>
        </div>
        <p><a href="/ads">Back to All Ads</a></p>
    """
    return render_template_string(HTML_TEMPLATE, title=ad['product_name'], content=content)

@app.route('/api/ads', methods=['POST'])
def create_ad():
    """API endpoint to create a new ad campaign"""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400

    required_fields = ['post_text', 'product_name', 'price']
    missing = [f for f in required_fields if f not in data]
    if missing:
        return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

    new_id = max(ad['id'] for ad in ads) + 1 if ads else 1
    new_ad = {
        "id": new_id,
        "post_text": data['post_text'],
        "product_name": data['product_name'],
        "price": data['price'],
        "clicks": 0
    }
    ads.append(new_ad)
    return jsonify({"message": "Ad created successfully", "ad": new_ad}), 201

@app.route('/api/ads', methods=['GET'])
def list_ads_json():
    """API endpoint to list all ads in JSON format"""
    return jsonify(ads)

if __name__ == '__main__':
    app.run(debug=True)
