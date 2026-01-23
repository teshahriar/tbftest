import os
import random
import string
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "admission_portal_2026_secure_key"

# MongoDB Config (tlsAllowInvalidCertificates=true রাখা হয়েছে কানেকশন নিশ্চিত করতে)
app.config["MONGO_URI"] = "mongodb+srv://shahriarkabircricket30:cDTl3F4ypWyjFGPP@earnify.mxftebt.mongodb.net/AdmissionDB?retryWrites=true&w=majority&tlsAllowInvalidCertificates=true"
app.config['UPLOAD_FOLDER'] = 'static/uploads'

# ফোল্ডার চেক
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mongo = PyMongo(app)

def generate_numbers():
    reg = ''.join(random.choices(string.digits, k=8))
    roll = ''.join(random.choices(string.digits, k=5))
    return reg, roll

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/apply', methods=['GET', 'POST'])
def apply():
    if request.method == 'POST':
        try:
            # ১. ফর্ম ডেটা এবং ফাইল ঠিকঠাক আসছে কি না তা কনসোলে দেখার জন্য (Debugging)
            print("Request Files:", request.files)
            print("Request Form:", request.form)

            # ২. পাসওয়ার্ড এবং কনফার্ম পাসওয়ার্ড চেক
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')

            if not password or password != confirm_password:
                flash("Passwords do not match or are empty!", "danger")
                return redirect(request.url)

            # ৩. ফাইল রিসিভ করা (HTML name='photo' এবং name='signature' হতে হবে)
            photo = request.files.get('photo')
            sig = request.files.get('signature')

            # ৪. ফাইল ভ্যালিডেশন (সবচেয়ে গুরুত্বপূর্ণ অংশ)
            # ফাইল যদি None হয় অথবা নাম খালি থাকে তবে এরর দিবে
            if not photo or photo.filename == '':
                flash("Photo is missing! Please select a 300x350px image.", "danger")
                return redirect(request.url)
            
            if not sig or sig.filename == '':
                flash("Signature is missing! Please select a 300x80px image.", "danger")
                return redirect(request.url)

            # ৫. রোল ও রেজিস্ট্রেশন নম্বর জেনারেট
            reg_no, roll_no = generate_numbers()

            # ৬. ফাইলের নাম তৈরি এবং সেভ করা
            # ফাইলের এক্সটেনশন ধরে রাখা নিরাপদ (.jpg, .png ইত্যাদি)
            photo_ext = os.path.splitext(photo.filename)[1]
            sig_ext = os.path.splitext(sig.filename)[1]
            
            p_name = secure_filename(f"photo_{roll_no}{photo_ext}")
            s_name = secure_filename(f"sig_{roll_no}{sig_ext}")
            
            # আপলোড ফোল্ডার তৈরি নিশ্চিত করা
            upload_path = app.config.get('UPLOAD_FOLDER', 'static/uploads')
            if not os.path.exists(upload_path):
                os.makedirs(upload_path)

            photo.save(os.path.join(upload_path, p_name))
            sig.save(os.path.join(upload_path, s_name))

            # ৭. ডাটাবেস অবজেক্ট তৈরি
            student_data = {
                "roll_no": str(roll_no),
                "reg_no": str(reg_no),
                "student_class": request.form.get('student_class'),
                "center_code": request.form.get('center_code'),
                "category": request.form.get('category'),
                "name_en": request.form.get('name_en'),
                "father_en": request.form.get('father_en'),
                "mother_en": request.form.get('mother_en'),
                "institute_en": request.form.get('institute_en'),
                "name_bn": request.form.get('name_bn'),
                "father_bn": request.form.get('father_bn'),
                "mother_bn": request.form.get('mother_bn'),
                "institute_bn": request.form.get('institute_bn'),
                "dob": request.form.get('dob'),
                "gender": request.form.get('gender'),
                "section": request.form.get('section', 'N/A'),
                "religion": request.form.get('religion'),
                "mobile": request.form.get('mobile'),
                "password": generate_password_hash(password), 
                "address_present": {
                    "village": request.form.get('pre_v'),
                    "post": request.form.get('pre_p'),
                    "upazila": request.form.get('pre_t'),
                    "district": request.form.get('pre_d')
                },
                "address_permanent": {
                    "village": request.form.get('per_v'),
                    "post": request.form.get('per_p'),
                    "upazila": request.form.get('per_t'),
                    "district": request.form.get('per_d')
                },
                "photo": p_name,
                "signature": s_name,
                "status": "Pending",
                "verification": False,
                "applied_at": datetime.datetime.now()
            }

            # ডাটাবেসে ইনসার্ট
            mongo.db.students.insert_one(student_data)
            flash("Application Submitted Successfully!", "success")
            
            return render_template("success.html", roll=roll_no, reg=reg_no, mobile=student_data["mobile"])

        except Exception as e:
            # যেকোনো এরর হলে টার্মিনালে প্রিন্ট হবে
            print(f"Server Error: {str(e)}")
            flash(f"System Error: {str(e)}", "danger")
            return redirect(request.url)

    return render_template("apply.html")

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

from werkzeug.security import check_password_hash

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll = request.form.get('roll')
        pw = request.form.get('password')

        if not roll or not pw:
            flash("Please enter both Roll and Password.", "danger")
            return redirect(url_for('login'))

        # ১. শুধু রোল নম্বর দিয়ে ইউজারকে খুঁজুন (পাসওয়ার্ড ছাড়া)
        # কারণ পাসওয়ার্ড হ্যাশ করা থাকলে কুয়েরিতে সরাসরি চেক করা যায় না
        user = mongo.db.students.find_one({
            "$or": [
                {"roll_no": roll}, 
                {"roll_no": int(roll) if roll.isdigit() else None}
            ]
        })
        
        # ২. ইউজার পাওয়া গেলে পাসওয়ার্ড চেক করুন
        if user:
            # যদি রেজিস্ট্রেশনের সময় generate_password_hash ব্যবহার করে থাকেন:
            is_valid = check_password_hash(user['password'], pw)
            
            # যদি রেজিস্ট্রেশনের সময় সাধারণ টেক্সটে সেভ করে থাকেন, তবে নিচের লাইনটি ব্যবহার করুন:
            # is_valid = (user['password'] == pw)

            if is_valid:
                session.permanent = True
                session['user_id'] = str(user['_id'])
                session['roll'] = user['roll_no'] # ড্যাশবোর্ডের জন্য রোল সেভ রাখা ভালো
                flash("Welcome back!", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid Password.", "danger")
        else:
            flash("Roll Number not found.", "danger")
            
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

@app.route('/download-admit', methods=['GET', 'POST'])
def download_admit():
    student = None
    error = None
    
    if request.method == 'POST':
        # Safely get the roll number and strip whitespace
        roll = request.form.get('roll_no', '').strip()
        
        if not roll:
            error = "Please enter your Roll Number."
        else:
            # Search for the student by roll number only
            student = mongo.db.students.find_one({"roll_no": roll})
            
            if not student:
                error = "Roll Number not found in our records."
            elif not student.get('admit_approved', False):
                # This ensures the 'Admin Approval' logic still guards the download
                error = "Your admit card has not been approved by the Admin yet."
                student = None
            
    return render_template('student_admit_portal.html', student=student, error=error)

@app.route('/print-admit/<student_id>')
def print_admit(student_id):
    # Fetch student by ID
    student = mongo.db.students.find_one({"_id": ObjectId(student_id)})
    
    # Check if student exists and has been approved by admin
    if not student or not student.get('admit_approved', False):
        return "Admit Card is not available for download or has not been approved yet.", 403

    return render_template('print_admit_template.html', student=student)

@app.route('/results', methods=['GET', 'POST'])
def public_results():
    student = None
    rank = None
    searched = False

    if request.method == 'POST':
        roll = request.form.get('roll_no', '').strip()
        searched = True
        
        if roll:
            # 1. Find the student
            student = mongo.db.students.find_one({"roll_no": roll, "marks": {"$exists": True}})
            
            if student:
                # 2. Calculate Merit Rank (Total students with higher marks + 1)
                student_total = (student.get('marks') or {}).get('total', 0)
                higher_scores = mongo.db.students.count_documents({
                    "marks.total": {"$gt": student_total}
                })
                rank = higher_scores + 1

    return render_template('public_results.html', student=student, rank=rank, searched=searched)

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
    
    # --- STEP 1: Get Filter Parameters from URL ---
    search_query = request.args.get('search', '')
    center_filter = request.args.get('center', '')
    class_filter = request.args.get('class', '')
    
    # --- STEP 2: Build MongoDB Query ---
    query = {}
    if search_query:
        query["$or"] = [
            {"name": {"$regex": search_query, "$options": "i"}},
            {"roll_no": {"$regex": search_query, "$options": "i"}},
            {"institute_bn": {"$regex": search_query, "$options": "i"}}
        ]
    if center_filter:
        query["center_code"] = center_filter
    if class_filter:
        query["student_class"] = class_filter


    # --- STEP 3: Fetch Data ---
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    
    # Stats should reflect the filtered view or global (Global is better for Admin)
    stats = {
        "total": mongo.db.students.count_documents({}),
        "pending": mongo.db.students.count_documents({"status": "Pending"}),
        "verified": mongo.db.students.count_documents({"status": "Verified"})
    }
    
    return render_template('admin_panel.html', students=students, stats=stats)

# --- DIRECT DATABASE UPDATE API (Point 2) ---
@app.route('/admin/api/update_status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'): return jsonify({"error": "Unauthorized"}), 403
    
    data = request.json
    roll = data.get('roll')
    new_status = data.get('status')
    
    verification = True if new_status == "Verified" else False
    
    mongo.db.students.update_one(
        {"roll_no": roll},
        {"$set": {"status": new_status, "verification": verification}}
    )
    return jsonify({"success": True})


# --- ATTENDANCE SHEET (One clean route) ---
@app.route('/admin/attendance-sheet')
def attendance_sheet():
    if not session.get('admin_logged_in'): 
        return redirect(url_for('admin_login'))
    
    # Get center filter from URL
    center_code = request.args.get('center', '')
    
    # Query: Only Verified students for the specific center
    query = {"status": "Verified"}
    if center_code:
        query["center_code"] = center_code
    
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    
    return render_template('admin_attendance.html', 
                           students=students, 
                           current_center=center_code or "All Centers")
# --- SEAT PLAN ---
@app.route('/admin/seat-plan')
def seat_plan():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # Get filter values
    center = request.args.get('center')
    student_class = request.args.get('class')
    gender = request.args.get('gender')

    # Build the database query dynamically
    query = {"status": "Verified"}
    if center: 
        query["center_code"] = center
    if student_class: 
        query["student_class"] = student_class
    if gender: 
        query["gender"] = gender

    # Fetch and sort by Roll Number (crucial for physical seating order)
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    
    return render_template('admin_seat_plan.html', students=students)

# --- SEARCH-FIRST MARK ENTRY (The one you requested) ---
@app.route('/admin/entry-marks', methods=['GET', 'POST'])
def entry_marks():
    # 1. Security Check
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    student = None
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        roll = request.form.get('roll_no')

        # --- ACTION 1: SEARCH STUDENT ---
        if form_type == 'search':
            # We search for the student and ensure they are 'Verified'
            student = mongo.db.students.find_one({"roll_no": roll, "status": "Verified"})
            if not student:
                flash(f"Verified student with Roll {roll} not found. Please check Verification status.", "danger")
        
        # --- ACTION 2: SAVE MARKS & GRADE ---
        elif form_type == 'save':
            try:
                # Extract subject marks from form
                m_ban = float(request.form.get('ban', 0))
                m_eng = float(request.form.get('eng', 0))
                m_math = float(request.form.get('math', 0))
                m_gk = float(request.form.get('gk', 0))
                
                # Extract Scholarship Grade
                s_grade = request.form.get('scholarship_grade', 'None')
                
                # Backend Calculation for Security
                total = m_ban + m_eng + m_math + m_gk

                # Update MongoDB
                mongo.db.students.update_one(
                    {"roll_no": roll},
                    {"$set": {
                        "marks": {
                            "bangla": m_ban, 
                            "english": m_eng, 
                            "math": m_math, 
                            "gk": m_gk, 
                            "total": total
                        },
                        "scholarship_grade": s_grade,
                        "result_published": True  # Flag to allow student to see result
                    }}
                )
                flash(f"Successfully finalized results for Roll {roll}. Grade: {s_grade}", "success")
                
            except ValueError:
                flash("Invalid input: Please enter numerical values for marks.", "danger")
            except Exception as e:
                flash(f"System Error: {str(e)}", "danger")
            
            # Redirect back to clear the form for the next student search
            return redirect(url_for('entry_marks'))

    return render_template('admin_marks_entry.html', student=student)

#admin view all results
@app.route('/admin/manage-results')
def manage_results():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    
    # 1. Get Filters from URL
    f_grade = request.args.get('grade', '')
    f_class = request.args.get('class', '')
    f_center = request.args.get('center', '')
    f_school = request.args.get('school', '')
    sort_by = request.args.get('sort', 'merit')

    # 2. Build Query - Only show students who have the 'marks' field
    query = {"marks": {"$exists": True}}
    if f_grade: query["scholarship_grade"] = f_grade
    if f_class: query["student_class"] = f_class
    if f_center: query["center_code"] = f_center
    if f_school: query["institute_bn"] = f_school

    # 3. Fetch Data
    results = list(mongo.db.students.find(query))

    # 4. Calculate Stats with Triple-Safety Logic
    total_count = len(results)
    sum_marks = 0
    for s in results:
        # The 'or {}' trick prevents the 'NoneType' error
        marks_data = s.get('marks') or {}
        sum_marks += marks_data.get('total', 0)
    
    avg_score = (sum_marks / total_count) if total_count > 0 else 0

    # 5. Professional Sorting
    if sort_by == 'merit':
        # Sort by Total -> Math -> English -> Bangla (Tie breakers)
        results.sort(key=lambda x: (
            (x.get('marks') or {}).get('total', 0),
            (x.get('marks') or {}).get('math', 0),
            (x.get('marks') or {}).get('english', 0),
            (x.get('marks') or {}).get('bangla', 0)
        ), reverse=True)
    elif sort_by == 'roll':
        results.sort(key=lambda x: x.get('roll_no', ''))
    elif sort_by == 'name':
        results.sort(key=lambda x: x.get('name_en', '').lower())

    # 6. Dropdown Options
    schools = mongo.db.students.distinct("institute_bn")
    centers = mongo.db.students.distinct("center_code")

    return render_template('admin_manage_results.html', 
                           results=results, 
                           schools=schools, 
                           centers=centers,
                           total_count=total_count, 
                           sum_marks=sum_marks, 
                           avg_score=avg_score)

# --- ADMIN: APPROVE ADMIT CARDS ---
@app.route('/admin/approve-admits', methods=['GET', 'POST'])
def approve_admits():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        # Get list of student IDs from checked boxes
        student_ids = request.form.getlist('selected_students')
        action = request.form.get('action') # 'approve' or 'revoke'
        
        if student_ids:
            status = True if action == 'approve' else False
            # Update all selected students at once
            mongo.db.students.update_many(
                {"_id": {"$in": [ObjectId(sid) for sid in student_ids]}},
                {"$set": {"admit_approved": status}}
            )
            flash(f"Successfully {action}d {len(student_ids)} students.", "success")
        
        return redirect(url_for('approve_admits'))

    students = list(mongo.db.students.find().sort("roll_no", 1))
    return render_template('admin_approve_admits.html', students=students)

# --- ADMIN LOGOUT ---
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)
