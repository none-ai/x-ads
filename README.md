# X Ad Format Tester 📢

A Flask web application demonstrating an innovative ad format that connects social media posts (X/Twitter) with products for e-commerce integration.

## 🎯 Overview

X Ad Format Tester showcases a modern advertising format that bridges the gap between social media engagement and product sales, allowing advertisers to create seamless shopping experiences.

## ✨ Features

- **Ad Campaign Management** - Create and manage advertising campaigns
- **Product Integration** - Connect products to social media posts
- **Analytics Dashboard** - Track ad performance metrics
- **Campaign Details** - Detailed view of each ad campaign
- **RESTful API** - Full API support for programmatic access
- **Responsive Design** - Works on all devices

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/none-ai/x-ads.git
cd x-ads

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

Visit http://localhost:5000

## 📋 Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/` | GET | Home page with ad format overview |
| `/ads` | GET | List of all ad campaigns |
| `/ads/<id>` | GET | View specific ad campaign details |
| `/api/ads` | GET | List all ads in JSON format |
| `/api/ads` | POST | Create a new ad campaign |
| `/api/ads/<id>` | GET | Get specific ad details |

## 🛠️ Tech Stack

- **Backend**: Python 3, Flask
- **Database**: SQLite (default)
- **Frontend**: HTML, CSS, JavaScript
- **API**: RESTful JSON API

## 📊 API Examples

### Get All Ads
```bash
curl http://localhost:5000/api/ads
```

### Create New Ad
```bash
curl -X POST http://localhost:5000/api/ads \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Summer Sale",
    "product_id": "123",
    "post_id": "abc123"
  }'
```

## 📄 License

MIT License

---

Author: stlin256's openclaw
