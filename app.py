import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, send_file, flash
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from io import BytesIO
from bson.objectid import ObjectId
from flask import render_template

app = Flask(__name__)
app.secret_key = "admission_portal_2026_secure_key"

# --- MongoDB Atlas Configuration ---
app.config["MONGO_URI"] = "mongodb+srv://shahriarkabircricket30:cDTl3F4ypWyjFGPP@earnify.mxftebt.mongodb.net/AdmissionDB?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
app.config['UPLOAD_FOLDER'] = 'static/uploads/'

# Ensure upload directory exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

mongo = PyMongo(app)

# --- Helper: Generate Numbers ---
def generate_numbers():
    reg = ''.join(random.choices(string.digits, k=8))
    roll = ''.join(random.choices(string.digits, k=5))
    return reg, roll

# --- Routes ---

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/admin/notices')
def admin_notices():
    # Fetch all notices from MongoDB, sorted by newest first
    notices = mongo.db.notices.find().sort("_id", -1)
    return render_template('admin_notices.html', notices=notices)

@app.route('/admin/add_notice', methods=['POST'])
def add_notice():
    import datetime
    notice_data = {
        "title": request.form.get('title'),
        "content": request.form.get('content'),
        "category": request.form.get('category'),
        "date": datetime.datetime.now().strftime("%b %d, %Y")
    }
    mongo.db.notices.insert_one(notice_data)
    return redirect(url_for('admin_notices'))

@app.route('/admin/delete_notice/<notice_id>')
def delete_notice(notice_id):
    mongo.db.notices.delete_one({"_id": ObjectId(notice_id)})
    return redirect(url_for('admin_notices'))

# Update your public notices route to pull from the database
@app.route('/notices')
def notices():
    all_notices = mongo.db.notices.find().sort("_id", -1)
    return render_template('notices.html', notices=all_notices)

from bson import ObjectId

import os
from flask import request, render_template, session, redirect, url_for, flash
from werkzeug.utils import secure_filename

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        # 1. Password Verification
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('apply'))

        # 2. Generate Registration and Roll Numbers
        reg_no, roll_no = generate_numbers()
        
        # 3. Handle File Uploads (Photo and Signature)
        # Handle Photo
        photo = request.files.get('photo')
        if photo and photo.filename != '':
            photo_name = secure_filename(f"photo_{roll_no}_{photo.filename}")
            photo.save(os.path.join(app.config['UPLOAD_FOLDER'], photo_name))
        else:
            photo_name = "default_photo.png"

        # Handle Signature
        sig = request.files.get('signature')
        if sig and sig.filename != '':
            sig_name = secure_filename(f"sig_{roll_no}_{sig.filename}")
            sig.save(os.path.join(app.config['UPLOAD_FOLDER'], sig_name))
        else:
            sig_name = "default_sig.png"

        # 4. Map all HTML fields to MongoDB Document
        student_data = {
            # Exam Info
            "exam_name": request.form.get('exam_name'),
            "center_code": request.form.get('center_code'),
            "category": request.form.get('category'), # Madrasah/School
            
            # Student Basic Info (English)
            "name_en": request.form.get('name_en'),
            "father_en": request.form.get('father_en'),
            "mother_en": request.form.get('mother_en'),
            "institute_en": request.form.get('institute_en'),
            "dob": request.form.get('dob'),
            "gender": request.form.get('gender'),
            "mobile": request.form.get('mobile'),
            
            # Student Basic Info (Bangla)
            "name_bn": request.form.get('name_bn'),
            "father_bn": request.form.get('father_bn'),
            "mother_bn": request.form.get('mother_bn'),
            "institute_bn": request.form.get('institute_bn'),
            
            # Academic & Contact
            "section": request.form.get('section'), # Science/Humanities/etc
            "religion": request.form.get('religion'),
            "email": request.form.get('email'),
            
            # Address Data
            "address": {
                "present": {
                    "village": request.form.get('pre_village'),
                    "post": request.form.get('pre_post'),
                    "thana": request.form.get('pre_thana'),
                    "dist": request.form.get('pre_dist')
                },
                "permanent": {
                    "village": request.form.get('per_village'),
                    "post": request.form.get('per_post'),
                    "thana": request.form.get('per_thana'),
                    "dist": request.form.get('per_dist')
                }
            },
            
            # System Data
            "password": password,
            "reg_no": reg_no,
            "roll_no": str(roll_no), 
            "photo": photo_name,
            "signature": sig_name,
            "status": "Pending",
            "verification": False,
            "marks": None,
            "tran_id": None
        }
        
        # 5. Insert into Database
        mongo.db.students.insert_one(student_data)
        
        # 6. Redirect to Success Page
        return render_template('success.html', reg=reg_no, roll=roll_no)

    return render_template('apply.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Safely get the values from the form
        roll = request.form.get('roll')
        pw = request.form.get('password')

        # 1. Validation Check: Ensure data isn't missing
        if not roll or not pw:
            flash("Please enter both Roll and Password.", "danger")
            return redirect(url_for('login'))

        # 2. Database Query: Check for both string and integer roll numbers
        # This prevents "Not Login" issues caused by data type mismatches
        user = mongo.db.students.find_one({
            "$or": [
                {"roll_no": roll}, 
                {"roll_no": int(roll) if roll.isdigit() else None}
            ],
            "password": pw
        })
        
        if user:
            # 3. Establish Session
            session.permanent = True
            session['user_id'] = str(user['_id'])
            flash("Welcome back!", "success")
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid Roll Number or Password.", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    
    if not student:
        session.clear()
        flash("Account error. Please login again.", "danger")
        return redirect(url_for('login'))
    
    is_verified = student.get('verification', False)

    if request.method == 'POST':
        tran_id = request.form.get('tran_id')
        mongo.db.students.update_one(
            {"_id": ObjectId(session['user_id'])},
            {"$set": {"tran_id": tran_id}}
        )
        flash("Transaction ID submitted! Waiting for approval.", "info")
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', student=student, is_verified=is_verified)

@app.route('/download-slip')
def download_slip():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    
    if not student or not student.get('verification'):
        flash("Access Denied: Account not verified.", "danger")
        return redirect(url_for('dashboard'))

    return render_template('payment_slip.html', student=student)

@app.route('/download_admit')
def download_admit():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})

    # VERIFICATION CHECK
    if user.get('status') != "Verified":
        return "<h3>Error: Your application is not yet verified by the Administrator.</h3><a href='/dashboard'>Go Back</a>"

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # PDF Design
    p.setStrokeColorRGB(0, 0.2, 0.4)
    p.setLineWidth(3)
    p.rect(20, 20, 555, 800)
    p.setFillColorRGB(0, 0.2, 0.4)
    p.rect(20, 730, 555, 70, fill=1)
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 20)
    p.drawCentredString(297, 770, "TBF ADMIT CARD")
    
    # Student Info in PDF
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica", 12)
    y = 650
    p.drawString(50, 680, f"Name: {user['name'].upper()}")
    p.drawString(50, 660, f"Roll No: {user['roll_no']}")
    p.drawString(50, 640, f"Reg No: {user['reg_no']}")
    p.drawString(50, 620, f"Class: {user['class']}")
    
    # Image in PDF
    img_path = os.path.join(app.config['UPLOAD_FOLDER'], user['photo'])
    try:
        p.drawImage(img_path, 430, 600, width=100, height=120)
    except:
        p.drawString(430, 650, "[Photo Error]")

    p.setDash([]) # Ensure solid lines for signatures
    p.drawString(50, 100, "__________________")
    p.drawString(50, 85, "Candidate Sign")
    p.drawString(400, 100, "__________________")
    p.drawString(400, 85, "Controller Sign")

    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"Admit_{user['roll_no']}.pdf")

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        message = request.form.get('message')
        return render_template('contact.html', success=True)
    return render_template('contact.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', 
        code=404, 
        message="Page Not Found", 
        description="The page you are looking for might have been removed, had its name changed, or is temporarily unavailable."), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', 
        code=500, 
        message="Internal Server Error", 
        description="Oops! Something went wrong on our end. Please try again later or contact support."), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', 
        code=403, 
        message="Access Forbidden", 
        description="You don't have permission to access this page. Please make sure you are logged in."), 403

# --- ADMIN LOGIN ---
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        
        # Hardcoded credentials as requested
        if user == "tbf123321" and pw == "123321":
            session['admin_logged_in'] = True
            flash("Welcome back, Admin!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Admin Credentials", "danger")
            
    return render_template('admin_login.html')

# --- ADMIN DASHBOARD ---
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Check if MongoDB is actually returning data
    student_cursor = mongo.db.students.find().sort("_id", -1)
    students = list(student_cursor)
    
    # Logic: If database is empty, create a fake record to see if it shows up
    if not students:
        print("DEBUG: No students found in MongoDB!")
    
    stats = {
        "total": len(students),
        "pending": mongo.db.students.count_documents({"status": "Pending"}),
        "verified": mongo.db.students.count_documents({"status": "Verified"})
    }
    
    return render_template('admin_panel.html', students=students, stats=stats)

# --- APPROVE STUDENT (Verification Logic) ---
@app.route('/admin/approve/<roll>')
def approve_student(roll):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
        
    # Update both status for Admit Card and verification for Payment Slip
    mongo.db.students.update_one(
        {"roll_no": roll},
        {"$set": {"status": "Verified", "verification": True}}
    )
    flash(f"Student {roll} has been verified and issued an admit card.", "success")
    return redirect(url_for('admin_dashboard'))

# --- BULK MARK ENTRY ---
@app.route('/admin/manage-marks', methods=['GET', 'POST'])
def manage_marks():
    if not session.get('admin_logged_in'): 
        return redirect(url_for('admin_login'))
    
    if request.method == 'POST':
        roll = request.form.get('roll')
        marks = request.form.get('marks')
        mongo.db.students.update_one({"roll_no": roll}, {"$set": {"marks": marks}})
        flash(f"Marks updated for Roll: {roll}", "success")

    # FIX: Wrap the find() result in list()
    students = list(mongo.db.students.find({"status": "Verified"}).sort("roll_no", 1))
    
    return render_template('admin_marks.html', students=students)

# --- ATTENDANCE SHEET (One clean route) ---
@app.route('/admin/attendance-sheet')
def attendance_sheet():
    if not session.get('admin_logged_in'): 
        return redirect(url_for('admin_login'))
    
    # Fetch students sorted by roll number for the exam hall list
    students = list(mongo.db.students.find({"status": "Verified"}).sort("roll_no", 1))
    return render_template('admin_attendance.html', students=students)

# --- SEAT PLAN ---
@app.route('/admin/seat-plan', methods=['GET', 'POST'])
def seat_plan():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get filter values from the dropdowns
    center = request.args.get('center')
    student_class = request.args.get('class')
    gender = request.args.get('gender')

    # Build the database query
    query = {"status": "Verified"}
    if center: query["center_code"] = center
    if student_class: query["class"] = student_class
    if gender: query["gender"] = gender

    # Fetch and sort by Roll Number
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    
    return render_template('admin_seat_plan.html', students=students)

# --- ADMIN LOGOUT ---
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
