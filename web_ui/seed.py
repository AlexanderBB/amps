from app import create_app, db, User
import sys

app = create_app()

def seed():
    with app.app_context():
        # Create tables
        db.create_all()
        
        # Check if admin exists
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = User(email='admin@example.com', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            
        # Check if regular user exists
        user = User.query.filter_by(email='user@example.com').first()
        if not user:
            user = User(email='user@example.com', role='user')
            user.set_password('user123')
            db.session.add(user)
            
        db.session.commit()
        print("Database seeded!")

if __name__ == '__main__':
    seed()
