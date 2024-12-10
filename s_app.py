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
        cursor.execute("SELECT * FROM students where student_id=%s", (student_id,))
        student = cursor.fetchone()
        cursor.close()

        if student:
            student_name = student[0]
            return render_template('student_dashboard.html',student=student, student_name=student_name)
                   
    return redirect(url_for('login'))


# Profile Page Route
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'student_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('login'))
    
    student_id = session['student_id']
    cursor = mysql.connection.cursor()

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
        
    # If the form is submitted (POST request), update the student's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_institute = request.form['current_institute']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']

        # Optionally handle profile picture if uploaded
        new_picture = None
        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file:
                new_picture = file.read()  # Save the uploaded picture (BLOB)
                
        # Handle profile picture upload
        # if new_picture:
        #     filename = secure_filename(new_picture.filename)
        #     file_path = os.path.join('static/uploads', filename)
        #     new_picture.save(file_path)
        # else:
        #     file_path = student['profile_picture']  # Keep old picture if no new one

        # Update the student's information in the database (except for student_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE students
            SET name = %s, password = %s, current_institute = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE student_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_institute, new_address, new_dob, new_blood_group, new_picture, student_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Render the profile template with student data
    return render_template('s_profile.html', student=student)


@app.route('/logout')
def logout():
    session.pop('student_name', None)  # Remove the student's name from the session
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True) 


