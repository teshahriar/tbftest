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

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        # 1. Generate Numbers
        reg_no, roll_no = generate_numbers()
        
        # 2. Handle File Upload
        file = request.files.get('photo')
        if file and file.filename != '':
            filename = secure_filename(f"{roll_no}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = "default.png"

        # 3. Create Student Document
        student_data = {
            "name": request.form.get('name'),
            "father_name": request.form.get('father_name'),
            "mother_name": request.form.get('mother_name'),
            "school": request.form.get('school'),
            "class": request.form.get('class'),
            "password": request.form.get('password'),
            "reg_no": reg_no,
            "roll_no": roll_no,
            "photo": filename,
            "status": "Pending"
        }
        
        # 4. Database Insert
        mongo.db.students.insert_one(student_data)
        
        # 5. Success Redirect
        return render_template('success.html', reg=reg_no, roll=roll_no)

    return render_template('apply.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll = request.form.get('roll')
        pw = request.form.get('password')
        
        user = mongo.db.students.find_one({"roll_no": roll, "password": pw})
        
        if user:
            session['user_id'] = str(user['_id'])
            return redirect(url_for('dashboard'))
        else:
            # This "flashes" the message to the next page load
            flash("Invalid Roll Number or Password. Please check your credentials and try again.", "danger")
            return redirect(url_for('login'))
            
    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Fetch student data
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    
    # Logic: If 'verification' key doesn't exist, default to False
    is_verified = student.get('verification', False)

    if request.method == 'POST':
        tran_id = request.form.get('tran_id')
        # When student submits ID, we ensure verification stays/is False
        mongo.db.students.update_one(
            {"_id": ObjectId(session['user_id'])},
            {"$set": {"tran_id": tran_id, "verification": False}}
        )
        flash("Transaction ID submitted! Waiting for approval.", "info")
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html', student=student, is_verified=is_verified)

# Type this in browser: /admin/approve/12345 (where 12345 is the Roll No)
@app.route('/admin/approve/<roll>')
def approve_student(roll):
    result = mongo.db.students.update_one(
        {"roll_no": roll},
        {"$set": {"verification": True}}
    )
    
    if result.modified_count > 0:
        return f"<h1>Success!</h1> Student with Roll {roll} is now VERIFIED."
    else:
        return "<h1>Error!</h1> Roll number not found.", 404

@app.route('/download-slip')
def download_slip():
    # 1. Security: Must be logged in
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 2. Fetch student from database
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    
    # 3. CRITICAL CHECK: Does verification == True?
    if not student or student.get('verification') != True:
        return "<h3>Access Denied: Your account is not verified yet.</h3>", 403

    # 4. If verified, show the printable slip
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

if __name__ == '__main__':
    app.run(debug=True)
