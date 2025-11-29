from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Appointment, Availability
import os
from datetime import datetime, date, time

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here' # Change this in production
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hospital.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Initialization and Admin Seeding
def create_admin():
    with app.app_context():
        db.create_all()
        admin = User.query.filter_by(email='admin@hospital.com').first()
        if not admin:
            hashed_password = generate_password_hash('admin')
            new_admin = User(
                email='admin@hospital.com',
                password_hash=hashed_password,
                role='admin',
                name='Super Admin'
            )
            db.session.add(new_admin)
            db.session.commit()
            print("Admin account created successfully.")

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif current_user.role == 'doctor':
            return redirect(url_for('doctor_dashboard'))
        elif current_user.role == 'patient':
            return redirect(url_for('patient_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'doctor':
                return redirect(url_for('doctor_dashboard'))
            else:
                return redirect(url_for('patient_dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user:
            flash('Email already exists.', 'warning')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, name=name, password_hash=hashed_password, role='patient')
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Dashboards (Placeholders for now)
@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    # Stats
    doctor_count = User.query.filter_by(role='doctor').count()
    patient_count = User.query.filter_by(role='patient').count()
    appointment_count = Appointment.query.count()
    
    doctors = User.query.filter_by(role='doctor')
    search_query = request.args.get('search')
    if search_query:
        doctors = doctors.filter(
            (User.name.ilike(f'%{search_query}%')) | 
            (User.email.ilike(f'%{search_query}%'))
        )
    doctors = doctors.all()
    
    appointments = Appointment.query.all()
    
    return render_template('admin_dashboard.html', 
                           doctor_count=doctor_count, 
                           patient_count=patient_count, 
                           appointment_count=appointment_count,
                           doctors=doctors,
                           appointments=appointments)

@app.route('/edit_doctor/<int:doctor_id>', methods=['POST'])
@login_required
def edit_doctor(doctor_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    doctor = User.query.get_or_404(doctor_id)
    doctor.name = request.form.get('name')
    doctor.specialization = request.form.get('specialization')
    db.session.commit()
    flash('Doctor details updated.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/add_doctor', methods=['POST'])
@login_required
def add_doctor():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    email = request.form.get('email')
    name = request.form.get('name')
    specialization = request.form.get('specialization')
    password = request.form.get('password')
    
    user = User.query.filter_by(email=email).first()
    if user:
        flash('Email already exists.', 'warning')
    else:
        hashed_password = generate_password_hash(password)
        new_doctor = User(email=email, name=name, password_hash=hashed_password, role='doctor', specialization=specialization)
        db.session.add(new_doctor)
        db.session.commit()
        flash('Doctor added successfully!', 'success')
        
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
        
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete admin.', 'danger')
    else:
        db.session.delete(user)
        db.session.commit()
        flash('User deleted.', 'success')
        
    return redirect(url_for('admin_dashboard'))


@app.route('/doctor_dashboard')
@login_required
def doctor_dashboard():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
    
    appointments = Appointment.query.filter_by(doctor_id=current_user.id).order_by(Appointment.date_time).all()
    availabilities = Availability.query.filter_by(doctor_id=current_user.id).filter(Availability.date >= date.today()).order_by(Availability.date, Availability.start_time).all()
    return render_template('doctor_dashboard.html', appointments=appointments, availabilities=availabilities)

@app.route('/set_availability', methods=['POST'])
@login_required
def set_availability():
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    date_str = request.form.get('date')
    start_str = request.form.get('start_time')
    end_str = request.form.get('end_time')
    
    try:
        avail_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_str, '%H:%M').time()
        end_time = datetime.strptime(end_str, '%H:%M').time()
        
        if start_time >= end_time:
            flash('End time must be after start time.', 'danger')
        else:
            new_avail = Availability(
                doctor_id=current_user.id,
                date=avail_date,
                start_time=start_time,
                end_time=end_time
            )
            db.session.add(new_avail)
            db.session.commit()
            flash('Availability added.', 'success')
    except ValueError:
        flash('Invalid date or time format.', 'danger')
        
    return redirect(url_for('doctor_dashboard'))

@app.route('/complete_appointment/<int:appt_id>', methods=['POST'])
@login_required
def complete_appointment(appt_id):
    if current_user.role != 'doctor':
        return redirect(url_for('index'))
        
    appt = Appointment.query.get_or_404(appt_id)
    if appt.doctor_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('doctor_dashboard'))
        
    appt.diagnosis = request.form.get('diagnosis')
    appt.prescription = request.form.get('prescription')
    appt.status = 'Completed'
    db.session.commit()
    flash('Appointment completed successfully.', 'success')
    
    return redirect(url_for('doctor_dashboard'))

@app.route('/patient_history/<int:patient_id>')
@login_required
def patient_history(patient_id):
    if current_user.role not in ['doctor', 'patient']:
        return redirect(url_for('index'))
        
    # If patient, can only view own history
    if current_user.role == 'patient' and current_user.id != patient_id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('patient_dashboard'))
        
    patient = User.query.get_or_404(patient_id)
    history = Appointment.query.filter_by(patient_id=patient_id, status='Completed').order_by(Appointment.date_time.desc()).all()
    
    return render_template('patient_history.html', patient=patient, history=history)


@app.route('/patient_dashboard')
@login_required
def patient_dashboard():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
    
    doctors = User.query.filter_by(role='doctor')
    search_query = request.args.get('search')
    if search_query:
        doctors = doctors.filter(User.specialization.ilike(f'%{search_query}%'))
    doctors = doctors.all()
    
    appointments = Appointment.query.filter_by(patient_id=current_user.id).order_by(Appointment.date_time).all()
    
    return render_template('patient_dashboard.html', doctors=doctors, appointments=appointments)

@app.route('/get_available_slots/<int:doctor_id>/<string:date_str>')
@login_required
def get_available_slots(doctor_id, date_str):
    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        availabilities = Availability.query.filter_by(doctor_id=doctor_id, date=target_date, is_booked=False).all()
        slots = []
        for avail in availabilities:
            slots.append({
                'id': avail.id,
                'start_time': avail.start_time.strftime('%H:%M'),
                'end_time': avail.end_time.strftime('%H:%M')
            })
        return {'slots': slots}
    except ValueError:
        return {'slots': []}

@app.route('/cancel_appointment/<int:appt_id>', methods=['POST'])
@login_required
def cancel_appointment(appt_id):
    if current_user.role != 'patient':
        return redirect(url_for('index'))
        
    appt = Appointment.query.get_or_404(appt_id)
    if appt.patient_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('patient_dashboard'))
        
    appt.status = 'Cancelled'
    
    # Free up the availability slot if logic requires linking back to Availability ID
    # Since we are booking by time, we find the matching availability and unbook it
    # Note: In a real system, we'd link Appointment to Availability ID directly.
    # Here we infer from time.
    avail = Availability.query.filter_by(
        doctor_id=appt.doctor_id, 
        date=appt.date_time.date(),
        start_time=appt.date_time.time()
    ).first()
    
    if avail:
        avail.is_booked = False
        
    db.session.commit()
    flash('Appointment cancelled.', 'info')
    return redirect(url_for('patient_dashboard'))

@app.route('/edit_profile', methods=['POST'])
@login_required
def edit_profile():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
        
    current_user.name = request.form.get('name')
    password = request.form.get('password')
    if password:
        current_user.password_hash = generate_password_hash(password)
        
    db.session.commit()
    flash('Profile updated.', 'success')
    return redirect(url_for('patient_dashboard'))

@app.route('/book_appointment', methods=['POST'])
@login_required
def book_appointment():
    if current_user.role != 'patient':
        return redirect(url_for('index'))
        
    doctor_id = request.form.get('doctor_id')
    date_str = request.form.get('date')
    time_str = request.form.get('time') # This will now be the start time of the slot
    
    try:
        date_time_obj = datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M')
        
        # Verify availability
        avail = Availability.query.filter_by(
            doctor_id=doctor_id,
            date=date_time_obj.date(),
            start_time=date_time_obj.time(),
            is_booked=False
        ).first()
        
        if not avail:
            flash('Selected slot is no longer available.', 'danger')
            return redirect(url_for('patient_dashboard'))
            
        avail.is_booked = True
        
        new_appt = Appointment(
            patient_id=current_user.id,
            doctor_id=doctor_id,
            date_time=date_time_obj,
            status='Booked'
        )
        db.session.add(new_appt)
        db.session.commit()
        flash('Appointment booked successfully!', 'success')
        
    except ValueError:
        flash('Invalid date or time format.', 'danger')
    
    return redirect(url_for('patient_dashboard'))


if __name__ == '__main__':
    create_admin()
    app.run(debug=True)
