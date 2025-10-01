# Cartify - Electronic Shop

A Flask-based storefront for browsing products, adding items to a cart, and checking out with a generated bill (including GST). Includes user auth, order history, an admin panel for catalog management, and an About page.

## Features
- Product catalog with category filters and search
- Session-based cart; checkout calculates GST (18%) and grand total
- User authentication: register, login, logout
- Order history page
- Admin panel: add/edit/delete products, see sales summary
- Clean UI with Bootstrap 5 and unified navbar/footer
- About page at `/about`

## Tech Stack
- Backend: Flask, Flask-Login, Flask-SQLAlchemy
- Database: SQLite (`instance/shop.db`)
- Frontend: Bootstrap 5, Bootstrap Icons

## Getting Started

### Prerequisites
- Python 3.9+
- pip

### Setup
- (Recommended) Create and activate a virtual environment
  - Windows PowerShell:
    ```bash
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    ```
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Run
```bash
python app.py
```
- App URL: `http://127.0.0.1:5000`
- Debug mode is enabled for development

### Default Admin
On first run, a default admin is created if missing:
- Username: `admin`
- Password: `admin123`
- Admin panel: `/admin`

## Project Structure
```
Project/
  app.py
  requirements.txt
  instance/
    shop.db
  templates/
    base.html
    index.html
    login.html
    register.html
    cart.html
    orders.html
    admin.html
    about.html
```

## App Pages
- `/` Home: product list UI (filter & search)
- `/about` About page
- `/login`, `/register`, `/logout` Auth
- `/cart` Cart UI
- `/orders` Orders UI (requires login)
- `/admin` Admin UI (requires admin)

## API Endpoints (JSON)
- Products
  - `GET /api/products?category_id=&search=`
- Categories
  - `GET /api/categories`
- Cart (requires login)
  - `POST /api/cart/add` { product_id, quantity }
  - `GET /api/cart`
  - `POST /api/cart/update` { product_id, quantity }
  - `POST /api/checkout`
- Orders (requires login)
  - `GET /api/orders` (users see their own; admins see all)
- Admin (requires admin)
  - `GET /api/admin/products`
  - `POST /api/admin/products`
  - `PUT /api/admin/products/<id>`
  - `DELETE /api/admin/products/<id>`

## Configuration
Development defaults are set in `app.py`:
- `SECRET_KEY`: `your-secret-key-change-this-in-production`
- `SQLALCHEMY_DATABASE_URI`: `sqlite:///shop.db`

For production, configure environment variables and deploy with a production WSGI server behind Nginx/Apache.

## Troubleshooting
- Upgrade tooling if installs fail:
  ```bash
  python -m pip install --upgrade pip wheel
  ```
- Port in use: change the port, e.g., `app.run(port=5001)`
- SQLAlchemy `LegacyAPIWarning` is informational with 2.x changes; the app still runs.

## License
Provided as-is for educational/demo purposes.
