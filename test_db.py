from app import app, db, User, create_admin

def test_setup():
    with app.app_context():
        # Ensure DB is created
        db.create_all()
        create_admin()
        
        # Check Admin
        admin = User.query.filter_by(email='admin@hospital.com').first()
        if admin:
            print("PASS: Admin user exists.")
        else:
            print("FAIL: Admin user does not exist.")
            
        # Check Role
        if admin.role == 'admin':
            print("PASS: Admin role is correct.")
        else:
            print("FAIL: Admin role is incorrect.")

if __name__ == '__main__':
    test_setup()
