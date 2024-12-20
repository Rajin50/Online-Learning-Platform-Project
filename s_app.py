from flask import Flask, render_template, request, redirect, url_for, session, flash 
from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, DateField, FileField
from wtforms.validators import DataRequired, Email, ValidationError
from werkzeug.utils import secure_filename
import bcrypt
import os
from flask_mysqldb import MySQL

# Create an instance of the Flask class
app = Flask(__name__)

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'project_olp'
app.secret_key = 'your_secret_key_here'

mysql = MySQL(app)

class RegisterForm(FlaskForm):
    name = StringField("Name",validators=[DataRequired()])
    phone = StringField("Phone No",validators=[DataRequired()])
    email = StringField("Email",validators=[DataRequired(), Email()])
    password = PasswordField("Password",validators=[DataRequired()])
    current_institute = StringField("Current Institute",validators=[DataRequired()])
    address = StringField("Address",validators=[DataRequired()])
    dob = DateField("Date of Birth", format='%Y-%m-%d', validators=[DataRequired()])
    bg = StringField("Blood Group",validators=[DataRequired()])
    profile_picture = FileField("Profile Picture", validators=[FileRequired(), FileAllowed(['jpg', 'jpeg'], 'Images only (.jpg, .jpeg)')])
    submit = SubmitField("Register")
    
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")

# Home route 
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/s_register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        current_institute = form.current_institute.data
        address = form.address.data
        dob = form.dob.data
        bg = form.bg.data
        profile_picture = form.profile_picture.data  

        # Handle the profile picture file upload
        if profile_picture:
            filename = secure_filename(profile_picture.filename)  # Secure the file name
            file_path = os.path.join('static/uploads', filename)  # Define the file path
            file_path = file_path.replace("\\", "/")

            # Save the profile picture
            profile_picture.save(file_path)
        else:
            file_path = None  # If no picture is uploaded, set file_path to None

        # Store the user data in the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO students (name, phone_no, email, password, current_institute, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, current_institute, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))  # Redirect to login after successful registration

    return render_template('s_register.html', form=form)

@app.route('/s_login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Fetch student from the database using email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE email=%s", (email,))
        student = cursor.fetchone()
        cursor.close()

        # Check if student exists and if the password matches directly (without bcrypt)
        if student and password == student[4]:  # student[4] is the password field in the database
            session['student_id'] = student[1]  # Store student_id in session
            session['student_name'] = student[0]
            return redirect(url_for('student_dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('s_login.html', form=form)

@app.route('/student_dashboard')
def student_dashboard():
    if 'student_id' in session:
        student_id = session['student_id']
        
        cursor = mysql.connection.cursor()
        
        # Fetch student details
        cursor.execute("SELECT name FROM students WHERE student_id=%s", (student_id,))
        student = cursor.fetchone()
        
        if not student:
            return redirect(url_for('login'))  # Redirect if student not found
        
        student_name = student[0]
        
        # Fetch enrolled courses for the student
        cursor.execute("""
            SELECT c.course_code, c.course_name, c.course_picture
            FROM courses c
            INNER JOIN enrollment_status e ON c.course_code = e.course_code
            WHERE e.student_id = %s
        """, (student_id,))
        
        enrolled_courses = cursor.fetchall()
        cursor.close()
        
        if student:
            student_name = student[0]
            no_courses = len(enrolled_courses) == 0
        
            return render_template('student_dashboard.html', 
                                student_name=student_name, 
                                enrolled_courses=enrolled_courses,
                                no_courses=no_courses)
    
    return redirect(url_for('login'))


# Profile Page Route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('login'))
    
    student_id = session['student_id']
    cursor = mysql.connection.cursor()
    
    # If the form is submitted (POST request), update the student's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_institute = request.form['current_institute']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']
        new_picture = request.files['profile_picture'] 
        
        # Fetch current student data for fallback values
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
        student = cursor.fetchone()  # Fetch the student's record
        cursor.close()

        if not student:
            flash("Student not found!", "danger")
            return redirect(url_for('login'))
                
        # Handle profile picture upload
        if new_picture and new_picture.filename.strip():
            filename = secure_filename(new_picture.filename)
            file_path = os.path.join('static/uploads', filename)
            file_path = file_path.replace("\\", "/")
            new_picture.save(file_path)
        else:
            file_path = student[9]   # Keep old picture if no new one
            
        # Update the student's information in the database (except for student_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE students
            SET name = %s, password = %s, current_institute = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE student_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_institute, new_address, new_dob, new_blood_group, file_path, student_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Fetch student data from the database
    cursor.execute("SELECT * FROM students WHERE student_id = %s", (student_id,))
    student = cursor.fetchone()  # Fetch the student's record
    cursor.close()

    if student:  # Ensure student exists
        # Assign fetched data to variables
        student_id = student[1]  
        student_name = student[0]  
        phone_no = student[2]  
        email = student[3] 
        password = student[4] 
        current_institute = student[5]  
        address = student[6]  
        date_of_birth = student[7] 
        blood_group = student[8]  
        profile_picture = student[9] 
        
        return render_template('s_profile.html', student=student, 
                               student_id=student_id, 
                               student_name=student_name, 
                               phone_no=phone_no,
                               email=email,
                               password=password,
                               current_institute=current_institute,
                               address=address,
                               date_of_birth=date_of_birth,
                               blood_group=blood_group,
                               profile_picture=profile_picture)
    
    else:
        flash("Student not found", 'danger')
        return redirect(url_for('login'))    

    # Render the profile template with student data
    return render_template('s_profile.html', student=student)

@app.route('/view_course/<int:course_code>')
def view_course(course_code):
    # Fetch course details from courses table
    cursor = mysql.connection.cursor()
    course_query = """
        SELECT course_name, category, num_of_students, completation_rate
        FROM courses
        WHERE course_code = %s
    """
    cursor.execute(course_query, (course_code,))
    course = cursor.fetchone()  # (course_name, category, num_of_students, completion_rate)

    if not course:
        cursor.close()
        return "Course not found", 404

    # Fetch content details from content table
    content_query = """
        SELECT module_no, outline_pdf, pdf_file, module_video, assignment, deadline
        FROM content
        WHERE course_code = %s
        ORDER BY module_no ASC
    """
    cursor.execute(content_query, (course_code,))
    content = cursor.fetchall()  # List of content for the course
    
    # Fetch leaderboard for the course
    leaderboard_query = """
        SELECT p1, p2, p3, p4, p5
        FROM leaderboard
        WHERE course_code = %s
    """
    cursor.execute(leaderboard_query, (course_code,))
    leaderboard = cursor.fetchone()  # (p1, p2, p3, p4, p5)

    # Fetch student names for the leaderboard positions
    student_names = []
    if leaderboard:
        for position in leaderboard:
            if position:  # Check if the position is not None
                cursor.execute("SELECT name FROM students WHERE student_id = %s", (position,))
                student = cursor.fetchone()
                if student:
                    student_names.append(student[0])


    cursor.close()

    return render_template(
        's_view_course.html',
        course_code=course_code,
        course_name=course[0],
        course_category=course[1],
        num_of_students=course[2],
        completion_rate=course[3],
        content=content if content else [],  # Pass empty list if no modules
        leaderboard=student_names
    )

@app.route('/logout')
def logout():
    session.pop('student_name', None)  # Remove the student's name from the session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 


