from app import create_app
from app.extensions import db
from app.utils.auth import hash_password
from flask_migrate import upgrade

app = create_app()

@app.cli.command("create_db")
def create_db():
    """Command to create the database tables."""
    db.create_all()

@app.cli.command("seed_db")
def seed_db():
    """Command to seed the database with initial data."""
    # Example seeding logic
    from app.models import User
    admin_user = User(email='admin@example.com', password_hash=hash_password('admin1234'), full_name='Admin', role='admin')
    db.session.add(admin_user)
    db.session.commit()
    print("Database seeded with initial data!")

@app.cli.command("upgrade_db")
def upgrade_db():
    """Command to apply migrations to the database."""
    upgrade()

