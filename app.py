import os
import random
import string
from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from reportlab.pdfgen import canvas
from io import BytesIO
from bson.objectid import ObjectId

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
        reg_no, roll_no = generate_numbers()
        file = request.files['photo']
        if file:
            filename = secure_filename(f"{roll_no}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        else:
            filename = "default.png"

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
            "status": "Pending"  # Default status
        }
        mongo.db.students.insert_one(student_data)
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
        return "<h3>Invalid Credentials</h3><a href='/login'>Try Again</a>"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    return render_template('dashboard.html', user=user)

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

if __name__ == '__main__':
    app.run(debug=True)
