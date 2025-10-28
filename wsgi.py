from app import app, init_db, db

# Ensure database tables exist
with app.app_context():
    try:
        db.create_all()
        init_db()  # Initialize with sample data
    except Exception as e:
        print(f"Database initialization error: {e}")

if __name__ == "__main__":
    app.run()