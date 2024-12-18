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
    address = StringField("Address",validators=[DataRequired()])
    dob = DateField("Date of Birth", format='%Y-%m-%d', validators=[DataRequired()])
    bg = StringField("Blood Group",validators=[DataRequired()])
    profile_picture = FileField("Profile Picture", validators=[FileRequired(), FileAllowed(['jpg', 'jpeg'], 'Images only (.jpg, .jpeg)')])
    submit = SubmitField("Register")
    
class InstructorRegisterForm(FlaskForm):
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
    return render_template('a_index.html')

@app.route('/a_register', methods=['GET', 'POST'])
def a_register():
    form = RegisterForm()

    if form.validate_on_submit():
        name = form.name.data
        phone = form.phone.data
        email = form.email.data
        password = form.password.data
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
        cursor.execute("INSERT INTO admin (name, phone_no, email, password, address, date_of_birth, blood_group, profile_picture) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                       (name, phone, email, password, address, dob, bg, file_path))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('a_login'))  # Redirect to login after successful registration

    return render_template('a_register.html', form=form)

@app.route('/i_register', methods=['GET', 'POST'])
def i_register():
    form = InstructorRegisterForm()

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

        return redirect(url_for('admin_dashboard'))  # Redirect to login after successful registration

    return render_template('i_register.html', form=form)

@app.route('/a_login', methods=['GET', 'POST'])
def a_login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        # Fetch student from the database using email
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE email=%s", (email,))
        admin = cursor.fetchone()
        cursor.close()

        # Check if student exists and if the password matches directly (without bcrypt)
        if admin and password == admin[4]:  # instructor[4] is the password field in the database
            session['admin_id'] = admin[1]  # Store instructor_id in session
            session['admin_name'] = admin[0]
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('a_login'))

    return render_template('a_login.html', form=form)

@app.route('/admin_dashboard')
def admin_dashboard():
    
    if 'admin_id' in session:
        admin_id = session['admin_id']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin where admin_id=%s", (admin_id,))
        admin = cursor.fetchone()
        cursor.close()

        if admin:
            admin_name = admin[0]
            return render_template('admin_dashboard.html',admin=admin, admin_name=admin_name)
                   
    return redirect(url_for('a_login'))


# Profile Page Route
@app.route('/a_profile', methods=['GET', 'POST'])
def a_profile():
    if 'admin_id' not in session:
        flash("You need to login first!", 'danger')
        return redirect(url_for('a_login'))
    
    admin_id = session['admin_id']
    cursor = mysql.connection.cursor()
    
    # If the form is submitted (POST request), update the admin's information
    if request.method == 'POST':
        # Get updated data from the form
        new_name = request.form['name']
        new_password = request.form['password']
        new_address = request.form['address']
        new_dob = request.form['date_of_birth']
        new_blood_group = request.form['blood_group']
        new_picture = request.files['profile_picture']
        
        # Fetch admin data from the database
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
        admin = cursor.fetchone()  # Fetch the admin's record
        cursor.close()
        
        if not admin:
            flash("Admin not found", 'danger')
            return redirect(url_for('a_login'))
                
        # Handle profile picture upload
        if new_picture and new_picture.filename.strip():
            filename = secure_filename(new_picture.filename)
            file_path = os.path.join('static/uploads', filename)
            file_path = file_path.replace("\\", "/")
            new_picture.save(file_path)
        else:
            file_path = admin[8]  # Keep old picture if no new one

        # Update the admin's information in the database (except for admin_id, phone_no, and email)
        cursor = mysql.connection.cursor()
        
        update_query = """
            UPDATE admin
            SET name = %s, password = %s, address = %s,
                date_of_birth = %s, blood_group = %s, profile_picture = %s
            WHERE admin_id = %s
        """
        cursor.execute(update_query, (new_name, new_password, new_address, new_dob, new_blood_group, file_path, admin_id))
        mysql.connection.commit()
        cursor.close()

        flash('Profile updated successfully!', 'success')
        return redirect(url_for('a_profile'))

    # Fetch admin data from the database
    cursor.execute("SELECT * FROM admin WHERE admin_id = %s", (admin_id,))
    admin = cursor.fetchone()  # Fetch the admin's record
    cursor.close()

    if admin:  # Ensure admin exists
        # Assign fetched data to variables
        admin_id = admin[1]  
        admin_name = admin[0]  
        phone_no = admin[2]  
        email = admin[3] 
        password = admin[4]   
        address = admin[5]  
        date_of_birth = admin[6] 
        blood_group = admin[7]  
        profile_picture = admin[8] 
        
        return render_template('a_profile.html', admin=admin, 
                               admin_id=admin_id, 
                               admin_name=admin_name, 
                               phone_no=phone_no,
                               email=email,
                               password=password,
                               address=address,
                               date_of_birth=date_of_birth,
                               blood_group=blood_group,
                               profile_picture=profile_picture)
    
    else:
        flash("Admin not found", 'danger')
        return redirect(url_for('a_login'))    
        

    # Render the profile template with admin data
    return render_template('a_profile.html', admin=admin)


@app.route('/a_logout')
def a_logout():
    session.pop('admin_name', None)  # Remove the admin's name from the session
    return redirect(url_for('a_login'))

if __name__ == '__main__':
    app.run(debug=True)
