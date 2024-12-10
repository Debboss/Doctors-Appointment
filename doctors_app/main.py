from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime, timedelta, time

app = Flask(__name__)

# Configurations
app.secret_key = 'your_secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///appointments.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Database and Migrate Initialization
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Models
class Doctor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    availabilities = db.relationship('Availability', backref='doctor', lazy=True)

    def __repr__(self):
        return f'<Doctor {self.name}>'


class Appointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Appointment {self.name} with Doctor ID {self.doctor_id} on {self.date} at {self.time}>'

class Availability(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('doctor.id'), nullable=False)
    day_of_week = db.Column(db.String(20), nullable=False)  # Example: "Monday", "Tuesday", etc.
    start_time = db.Column(db.Time, nullable=False)         # Start time for the available slot
    end_time = db.Column(db.Time, nullable=False)           # End time for the available slot

    def __repr__(self):
        return f"<Availability doctor_id={self.doctor_id} day={self.day_of_week} from {self.start_time} to {self.end_time}>"


# Routes
@app.route('/')
def home():
    doctors = Doctor.query.all()
    print(f"Doctors: {doctors}")  # Print fetched doctors to check
    return render_template('appointment.html', doctors=doctors)



@app.route('/get_availability/<int:doctor_id>/<string:date>', methods=['GET'])
def get_availability(doctor_id, date):
    # Parse the date
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    day_of_week = selected_date.strftime('%A')

    # Get all availabilities for the doctor on that day
    availabilities = Availability.query.filter_by(doctor_id=doctor_id, day_of_week=day_of_week).all()

    # Get existing appointments for the doctor on that date
    existing_appointments = Appointment.query.filter_by(doctor_id=doctor_id, date=selected_date).all()
    booked_times = {appt.time for appt in existing_appointments}

    # Generate available time slots based on availability and existing appointments
    available_slots = []
    slot_duration = timedelta(minutes=30)  # Define slot duration (e.g., 30 minutes)

    for avail in availabilities:
        current_time = datetime.combine(selected_date, avail.start_time)
        end_datetime = datetime.combine(selected_date, avail.end_time)

        while current_time + slot_duration <= end_datetime:
            slot_start = current_time.time()
            slot_end = (current_time + slot_duration).time()
            if slot_start not in booked_times:
                available_slots.append({'start': slot_start.strftime("%H:%M"), 'end': slot_end.strftime("%H:%M")})
            current_time += slot_duration

    return jsonify(available_slots)


@app.route('/book_appointment', methods=['POST'])
def book_appointment():
    name = request.form['name']
    date = request.form['date']
    time_str = request.form['time']
    doctor_id = request.form['doctor_id']

    # Convert to datetime objects for validation
    selected_date = datetime.strptime(date, "%Y-%m-%d").date()
    selected_time = datetime.strptime(time_str, "%H:%M").time()
    day_of_week = selected_date.strftime('%A')

    # Check availability
    availability = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.day_of_week == day_of_week,
        Availability.start_time <= selected_time,
        Availability.end_time > selected_time  # Ensure the time slot is within availability
    ).first()

    # Check if the time slot is already booked
    existing_appointment = Appointment.query.filter_by(
        doctor_id=doctor_id, 
        date=selected_date, 
        time=selected_time
    ).first()

    if not availability:
        flash("The doctor is not available at this time. Please choose another slot.", 'danger')
        return redirect(url_for('home'))

    if existing_appointment:
        flash("This time slot is already booked. Please choose another time.", 'danger')
        return redirect(url_for('home'))

    # Create appointment if valid
    new_appointment = Appointment(
        name=name, 
        date=selected_date, 
        time=selected_time, 
        doctor_id=doctor_id
    )
    db.session.add(new_appointment)
    db.session.commit()
    flash("Appointment successfully booked!", 'success')
    return redirect(url_for('home'))

@app.route('/appointments')
def appointments():
    all_appointments = Appointment.query.all()
    return render_template('appointments.html', appointments=all_appointments)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
