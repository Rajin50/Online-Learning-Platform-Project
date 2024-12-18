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
    course_name = StringField("Course Name",validators=[DataRequired()])
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
    return render_template('i_index.html')

@app.route('/i_register', methods=['GET', 'POST'])
def i_register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
        course_name = form.course_name.data
        address = form.address.data
        dob = form.dob.data
        bg = form.bg.data
        profile_picture = form.profile_picture.data  

        # Handle the profile picture file upload
        if profile_picture:
            filename = secure_filename(profile_picture.filename)  
            file_path = os.path.join('static/uploads', filename) 
            file_path = file_path.replace("\\", "/")

            profile_picture.save(file_path)
            
        else:
            file_path = None  

        # Store the user data in the database
        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO instructors (name, phone_no, email, password, course_name, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, course_name, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('i_login'))  # Redirect to login after successful registration

    return render_template('i_register.html', form=form)

@app.route('/i_login', methods=['GET', 'POST'])
def i_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Fetch student from the database using email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM instructors WHERE email=%s", (email,))
        instructor = cursor.fetchone()
        cursor.close()

        # Check if student exists and if the password matches directly (without bcrypt)
        if instructor and password == instructor[4]:  # instructor[4] is the password field in the database
            session['instructor_id'] = instructor[1]  # Store instructor_id in session
            session['instructor_name'] = instructor[0]
            return redirect(url_for('instructor_dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('i_login'))

    return render_template('i_login.html', form=form)

@app.route('/instructor_dashboard')
def instructor_dashboard():
    
    if 'instructor_id' in session:
        instructor_id = session['instructor_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM instructors where instructor_id=%s", (instructor_id,))
        instructor = cursor.fetchone()
        cursor.close()
           
        # Fetch courses for the instructor
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT course_name, course_picture FROM courses WHERE instructor_id=%s", (instructor_id,))
        courses = cursor.fetchall()
        cursor.close()
        
        if instructor:
            instructor_name = instructor[0]  # The first column is the instructor's name
            no_courses = len(courses) == 0
            return render_template(
                'instructor_dashboard.html', 
                instructor=instructor, 
                instructor_name=instructor_name, 
                courses=courses,
                no_courses=no_courses
            )
                
    return redirect(url_for('i_login'))


# Profile Page Route
@app.route('/i_profile', methods=['GET', 'POST'])
def i_profile():
    if 'instructor_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('i_login'))
    
    instructor_id = session['instructor_id']
    cursor = mysql.connection.cursor()
    
    # If the form is submitted (POST request), update the student's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_course_name = request.form['course_name']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']
        new_picture = request.files['profile_picture']
        
        # Fetch instructor data from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM instructors WHERE instructor_id = %s", (instructor_id,))
        instructor = cursor.fetchone()  # Fetch the instructor's record
        cursor.close()
        
        if not instructor:
            flash("Instructor not found", 'danger')
            return redirect(url_for('i_login'))
                
        # Handle profile picture upload
        if new_picture and new_picture.filename.strip():
            filename = secure_filename(new_picture.filename)
            file_path = os.path.join('static/uploads', filename)
            file_path = file_path.replace("\\", "/")
            new_picture.save(file_path)
        else:
            file_path = instructor[9]  # Keep old picture if no new one

        # Update the student's information in the database (except for student_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE instructors
            SET name = %s, password = %s, course_name = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE instructor_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_course_name, new_address, new_dob, new_blood_group, file_path, instructor_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('i_profile'))

    # Fetch instructor data from the database
    cursor.execute("SELECT * FROM instructors WHERE instructor_id = %s", (instructor_id,))
    instructor = cursor.fetchone()  # Fetch the instructor's record
    cursor.close()

    if instructor:  # Ensure instructor exists
        # Assign fetched data to variables
        instructor_id = instructor[1]  
        instructor_name = instructor[0]  
        phone_no = instructor[2]  
        email = instructor[3] 
        password = instructor[4] 
        course_name = instructor[5]  
        address = instructor[6]  
        date_of_birth = instructor[7] 
        blood_group = instructor[8]  
        profile_picture = instructor[9] 
        
        return render_template('i_profile.html', instructor=instructor, 
                               instructor_id=instructor_id, 
                               instructor_name=instructor_name, 
                               phone_no=phone_no,
                               email=email,
                               password=password,
                               course_name=course_name,
                               address=address,
                               date_of_birth=date_of_birth,
                               blood_group=blood_group,
                               profile_picture=profile_picture)
    
    else:
        flash("Instructor not found", 'danger')
        return redirect(url_for('i_login'))    
        
    # Render the profile template with instructor data
    return render_template('i_profile.html', instructor=instructor)


@app.route('/i_logout')
def i_logout():
    session.pop('instructor_name', None)  # Remove the instructor's name from the session
    return redirect(url_for('i_login'))

if __name__ == '__main__':
    app.run(debug=True)
