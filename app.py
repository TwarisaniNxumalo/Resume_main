from flask import Flask, render_template, redirect, request, url_for, flash, current_app, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import uuid
import itsdangerous

db = SQLAlchemy()
login_manager = LoginManager()

# Define models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100))
    contact = db.Column(db.String(20))
    course = db.Column(db.String(100))
    institution = db.Column(db.String(100))
    graduation_status = db.Column(db.String(50))
    skills = db.Column(db.Text)
    experience = db.Column(db.Text)
    projects = db.Column(db.Text)
    certifications = db.Column(db.Text)
    awards = db.Column(db.Text)

class CV(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    upload_date = db.Column(db.DateTime, default=db.func.current_timestamp())

class JobPosting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    job_description = db.Column(db.Text, nullable=False)
    job_type = db.Column(db.String(50))  # Full-time, Part-time, Internship, etc.
    location = db.Column(db.String(100))
    salary_range = db.Column(db.String(100))
    requirements = db.Column(db.Text)
    application_link = db.Column(db.String(500), nullable=False)
    posted_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_active = db.Column(db.Boolean, default=True)
    click_count = db.Column(db.Integer, default=0)

class JobClick(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('job_posting.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    clicked_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    ip_address = db.Column(db.String(50))

class Company(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    industry = db.Column(db.String(100))
    description = db.Column(db.Text)
    website = db.Column(db.String(200))
    location = db.Column(db.String(100))
    company_size = db.Column(db.String(50))
    founded_year = db.Column(db.String(10))
    logo_url = db.Column(db.String(500))
    linkedin_url = db.Column(db.String(200))
    facebook_url = db.Column(db.String(200))
    twitter_url = db.Column(db.String(200))
    created_date = db.Column(db.DateTime, default=db.func.current_timestamp())
    is_featured = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)

class CompanyFollow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(db.Integer, db.ForeignKey('company.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    followed_date = db.Column(db.DateTime, default=db.func.current_timestamp())

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cv_drop.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'

    serializer = itsdangerous.URLSafeTimedSerializer(app.config['SECRET_KEY'])

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @app.route("/")
    def index():
        return render_template("index.html")

    # AUTH ROUTES
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('All fields are required.', 'danger')
                return render_template('register.html')
            
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                flash('Email already registered. Please log in or use a different email.', 'danger')
                return render_template('register.html')
            
            try:
                user = User(email=email, role='student')
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except Exception as e:
                db.session.rollback()
                flash('Registration failed. Please try again.', 'danger')
                
        return render_template('register.html')

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash('Email and password are required.', 'danger')
                return render_template('login.html')
            
            user = User.query.filter_by(email=email).first()
            
            if user and user.check_password(password):
                login_user(user)
                flash(f'Welcome back!', 'success')
                
                if user.role == 'student':
                    return redirect(url_for('student_dashboard'))
                elif user.role == 'employer':
                    return redirect(url_for('employer_dashboard'))
                else:
                    flash('Invalid user role.', 'danger')
                    logout_user()
                    return render_template('login.html')
            else:
                flash('Invalid email or password.', 'danger')
                
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('login'))

    # STUDENT ROUTES
    @app.route('/student/dashboard')
    @login_required
    def student_dashboard():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        
        profile = Profile.query.filter_by(user_id=current_user.id).first()
        cvs = CV.query.filter_by(user_id=current_user.id).all()
        
        return render_template('student/dashboard.html', profile=profile, cvs=cvs)

    @app.route('/student/profile', methods=['GET', 'POST'])
    @login_required
    def student_profile():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
            
        profile = Profile.query.filter_by(user_id=current_user.id).first()
        
        if request.method == 'POST':
            try:
                if not profile:
                    profile = Profile(user_id=current_user.id)
                    db.session.add(profile)
                
                profile.name = request.form.get('name', '').strip()
                profile.contact = request.form.get('contact', '').strip()
                profile.course = request.form.get('course', '').strip()
                profile.institution = request.form.get('institution', '').strip()
                profile.graduation_status = request.form.get('graduation_status', '')
                profile.skills = request.form.get('skills', '').strip()
                profile.experience = request.form.get('experience', '').strip()
                profile.projects = request.form.get('projects', '').strip()
                profile.certifications = request.form.get('certifications', '').strip()
                profile.awards = request.form.get('awards', '').strip()
                
                db.session.commit()
                flash('Profile updated successfully!', 'success')
                return redirect(url_for('student_profile'))
                
            except Exception as e:
                db.session.rollback()
                flash('Error saving profile. Please try again.', 'danger')
                
        return render_template('student/profile.html', profile=profile)

    @app.route('/student/upload_cv', methods=['GET', 'POST'])
    @login_required
    def student_upload_cv():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))

        if request.method == 'POST':
            try:
                existing_cv = CV.query.filter_by(user_id=current_user.id).first()
                if existing_cv:
                    flash('You have already uploaded a CV. Please delete your existing CV before uploading a new one.', 'warning')
                    return redirect(url_for('student_dashboard'))

                if 'cv' not in request.files:
                    flash('No file selected.', 'danger')
                    return redirect(request.url)

                file = request.files['cv']
                if file.filename == '':
                    flash('No file selected.', 'danger')
                    return redirect(request.url)

                allowed_extensions = {'pdf', 'doc', 'docx'}
                if not ('.' in file.filename and 
                        file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
                    flash('Invalid file type. Please upload PDF, DOC, or DOCX files only.', 'danger')
                    return redirect(request.url)

                filename = secure_filename(file.filename)
                unique_filename = f"{uuid.uuid4()}_{filename}"
                upload_folder = current_app.config['UPLOAD_FOLDER']

                if not os.path.exists(upload_folder):
                    os.makedirs(upload_folder)

                filepath = os.path.join(upload_folder, unique_filename)
                file.save(filepath)

                cv = CV(
                    user_id=current_user.id, 
                    filename=unique_filename, 
                    original_filename=filename
                )
                db.session.add(cv)
                db.session.commit()

                flash('CV uploaded successfully!', 'success')
                return redirect(url_for('student_dashboard'))

            except Exception as e:
                db.session.rollback()
                flash('Error uploading CV. Please try again.', 'danger')

        return render_template('student/upload_cv.html')

    @app.route('/student/download_cv/<int:cv_id>')
    @login_required
    def student_download_cv(cv_id):
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        cv = CV.query.get_or_404(cv_id)
        if cv.user_id != current_user.id:
            flash('You do not have permission to access this file.', 'danger')
            return redirect(url_for('student_dashboard'))
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, cv.filename)
        if not os.path.exists(filepath):
            flash('CV file not found.', 'danger')
            return redirect(url_for('student_dashboard'))
        try:
            return send_file(filepath, as_attachment=True, download_name=cv.original_filename)
        except Exception as e:
            flash('Error sending file.', 'danger')
            return redirect(url_for('student_dashboard'))

    @app.route('/student/delete_cv/<int:cv_id>', methods=['POST'])
    @login_required
    def student_delete_cv(cv_id):
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        cv = CV.query.get_or_404(cv_id)
        if cv.user_id != current_user.id:
            flash('You do not have permission to delete this file.', 'danger')
            return redirect(url_for('student_dashboard'))
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, cv.filename)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
            db.session.delete(cv)
            db.session.commit()
            flash('CV deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting CV. Please try again.', 'danger')
        return redirect(url_for('student_dashboard'))

    # JOB BROWSING FOR STUDENTS
    @app.route('/student/jobs')
    @login_required
    def student_jobs():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        
        jobs = JobPosting.query.filter_by(is_active=True).order_by(JobPosting.posted_date.desc()).all()
        return render_template('student/jobs.html', jobs=jobs)

    @app.route('/job/apply/<int:job_id>')
    @login_required
    def apply_job(job_id):
        job = JobPosting.query.get_or_404(job_id)
        
        # Track the click
        job.click_count += 1
        
        job_click = JobClick(
            job_id=job_id,
            student_id=current_user.id if current_user.is_authenticated else None,
            ip_address=request.remote_addr
        )
        
        db.session.add(job_click)
        db.session.commit()
        
        # Redirect to the application link
        return redirect(job.application_link)

    # EMPLOYER ROUTES
    @app.route('/employer/dashboard')
    @login_required
    def employer_dashboard():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        students = Profile.query.all() or []
        return render_template('employer/dashboard.html', students=students)

    @app.route('/employer/profile/<int:user_id>')
    @login_required
    def employer_view_profile(user_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        profile = Profile.query.filter_by(user_id=user_id).first()
        cvs = CV.query.filter_by(user_id=user_id).all() if profile else []
        if not profile:
            flash('Profile not found.', 'danger')
            return redirect(url_for('employer_dashboard'))
        return render_template('employer/view_profile.html', profile=profile, cvs=cvs)

    @app.route('/employer/download_cv/<int:cv_id>')
    @login_required
    def employer_download_cv(cv_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        cv = CV.query.get_or_404(cv_id)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, cv.filename)
        if not os.path.exists(filepath):
            flash('CV file not found.', 'danger')
            return redirect(url_for('employer_dashboard'))
        try:
            return send_file(filepath, as_attachment=True, download_name=cv.original_filename)
        except Exception as e:
            flash('Error sending file.', 'danger')
            return redirect(url_for('employer_dashboard'))
        
    @app.route('/employer/view_cv/<int:cv_id>')
    @login_required
    def employer_view_cv(cv_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        cv = CV.query.get_or_404(cv_id)
        upload_folder = current_app.config['UPLOAD_FOLDER']
        filepath = os.path.join(upload_folder, cv.filename)
        
        if not os.path.exists(filepath):
            flash('CV file not found.', 'danger')
            return redirect(url_for('employer_dashboard'))
        
        try:
            return send_file(filepath, as_attachment=False)
        except Exception as e:
            flash('Error displaying file.', 'danger')
            return redirect(url_for('employer_dashboard'))

    # JOB POSTING MANAGEMENT FOR EMPLOYERS
    @app.route('/employer/jobs')
    @login_required
    def employer_jobs():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        jobs = JobPosting.query.filter_by(employer_id=current_user.id).order_by(JobPosting.posted_date.desc()).all()
        return render_template('employer/jobs.html', jobs=jobs)

    @app.route('/employer/jobs/create', methods=['GET', 'POST'])
    @login_required
    def employer_create_job():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            try:
                job = JobPosting(
                    employer_id=current_user.id,
                    company_name=request.form.get('company_name', '').strip(),
                    job_title=request.form.get('job_title', '').strip(),
                    job_description=request.form.get('job_description', '').strip(),
                    job_type=request.form.get('job_type', ''),
                    location=request.form.get('location', '').strip(),
                    salary_range=request.form.get('salary_range', '').strip(),
                    requirements=request.form.get('requirements', '').strip(),
                    application_link=request.form.get('application_link', '').strip(),
                    is_active=True
                )
                
                db.session.add(job)
                db.session.commit()
                
                flash('Job posted successfully!', 'success')
                return redirect(url_for('employer_jobs'))
                
            except Exception as e:
                db.session.rollback()
                flash('Error creating job posting. Please try again.', 'danger')
        
        return render_template('employer/create_job.html')

    @app.route('/employer/jobs/edit/<int:job_id>', methods=['GET', 'POST'])
    @login_required
    def employer_edit_job(job_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        job = JobPosting.query.get_or_404(job_id)
        
        if job.employer_id != current_user.id:
            flash('You do not have permission to edit this job.', 'danger')
            return redirect(url_for('employer_jobs'))
        
        if request.method == 'POST':
            try:
                job.company_name = request.form.get('company_name', '').strip()
                job.job_title = request.form.get('job_title', '').strip()
                job.job_description = request.form.get('job_description', '').strip()
                job.job_type = request.form.get('job_type', '')
                job.location = request.form.get('location', '').strip()
                job.salary_range = request.form.get('salary_range', '').strip()
                job.requirements = request.form.get('requirements', '').strip()
                job.application_link = request.form.get('application_link', '').strip()
                
                db.session.commit()
                flash('Job updated successfully!', 'success')
                return redirect(url_for('employer_jobs'))
                
            except Exception as e:
                db.session.rollback()
                flash('Error updating job. Please try again.', 'danger')
        
        return render_template('employer/edit_job.html', job=job)

    @app.route('/employer/jobs/toggle/<int:job_id>', methods=['POST'])
    @login_required
    def employer_toggle_job(job_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        job = JobPosting.query.get_or_404(job_id)
        
        if job.employer_id != current_user.id:
            flash('You do not have permission to modify this job.', 'danger')
            return redirect(url_for('employer_jobs'))
        
        try:
            job.is_active = not job.is_active
            db.session.commit()
            status = 'activated' if job.is_active else 'deactivated'
            flash(f'Job {status} successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating job status.', 'danger')
        
        return redirect(url_for('employer_jobs'))

    @app.route('/employer/jobs/delete/<int:job_id>', methods=['POST'])
    @login_required
    def employer_delete_job(job_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        job = JobPosting.query.get_or_404(job_id)
        
        if job.employer_id != current_user.id:
            flash('You do not have permission to delete this job.', 'danger')
            return redirect(url_for('employer_jobs'))
        
        try:
            JobClick.query.filter_by(job_id=job_id).delete()
            db.session.delete(job)
            db.session.commit()
            flash('Job deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting job. Please try again.', 'danger')
        
        return redirect(url_for('employer_jobs'))
# COMPANY MANAGEMENT FOR EMPLOYERS
    @app.route('/employer/companies')
    @login_required
    def employer_companies():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        companies = Company.query.filter_by(employer_id=current_user.id).order_by(Company.created_date.desc()).all()
        return render_template('employer/companies.html', companies=companies)

    @app.route('/employer/companies/create', methods=['GET', 'POST'])
    @login_required
    def employer_create_company():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        if request.method == 'POST':
            try:
                company = Company(
                    employer_id=current_user.id,
                    company_name=request.form.get('company_name', '').strip(),
                    industry=request.form.get('industry', '').strip(),
                    description=request.form.get('description', '').strip(),
                    website=request.form.get('website', '').strip(),
                    location=request.form.get('location', '').strip(),
                    company_size=request.form.get('company_size', ''),
                    founded_year=request.form.get('founded_year', '').strip(),
                    logo_url=request.form.get('logo_url', '').strip(),
                    linkedin_url=request.form.get('linkedin_url', '').strip(),
                    facebook_url=request.form.get('facebook_url', '').strip(),
                    twitter_url=request.form.get('twitter_url', '').strip(),
                    is_featured=False
                )
                
                db.session.add(company)
                db.session.commit()
                
                flash('Company added successfully!', 'success')
                return redirect(url_for('employer_companies'))
                
            except Exception as e:
                db.session.rollback()
                flash('Error creating company. Please try again.', 'danger')
        
        return render_template('employer/create_company.html')

    @app.route('/employer/companies/edit/<int:company_id>', methods=['GET', 'POST'])
    @login_required
    def employer_edit_company(company_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        company = Company.query.get_or_404(company_id)
        
        if company.employer_id != current_user.id:
            flash('You do not have permission to edit this company.', 'danger')
            return redirect(url_for('employer_companies'))
        
        if request.method == 'POST':
            try:
                company.company_name = request.form.get('company_name', '').strip()
                company.industry = request.form.get('industry', '').strip()
                company.description = request.form.get('description', '').strip()
                company.website = request.form.get('website', '').strip()
                company.location = request.form.get('location', '').strip()
                company.company_size = request.form.get('company_size', '')
                company.founded_year = request.form.get('founded_year', '').strip()
                company.logo_url = request.form.get('logo_url', '').strip()
                company.linkedin_url = request.form.get('linkedin_url', '').strip()
                company.facebook_url = request.form.get('facebook_url', '').strip()
                company.twitter_url = request.form.get('twitter_url', '').strip()
                
                db.session.commit()
                flash('Company updated successfully!', 'success')
                return redirect(url_for('employer_companies'))
                
            except Exception as e:
                db.session.rollback()
                flash('Error updating company. Please try again.', 'danger')
        
        return render_template('employer/edit_company.html', company=company)

    @app.route('/employer/companies/delete/<int:company_id>', methods=['POST'])
    @login_required
    def employer_delete_company(company_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        company = Company.query.get_or_404(company_id)
        
        if company.employer_id != current_user.id:
            flash('You do not have permission to delete this company.', 'danger')
            return redirect(url_for('employer_companies'))
        
        try:
            CompanyFollow.query.filter_by(company_id=company_id).delete()
            db.session.delete(company)
            db.session.commit()
            flash('Company deleted successfully!', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting company. Please try again.', 'danger')
        
        return redirect(url_for('employer_companies'))

    # COMPANY BROWSING FOR STUDENTS
    @app.route('/student/companies')
    @login_required
    def student_companies():
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        
        companies = Company.query.order_by(Company.is_featured.desc(), Company.created_date.desc()).all()
        
        # Get companies the student is following
        followed_company_ids = [f.company_id for f in CompanyFollow.query.filter_by(student_id=current_user.id).all()]
        
        return render_template('student/companies.html', companies=companies, followed_company_ids=followed_company_ids)

    @app.route('/student/companies/<int:company_id>')
    @login_required
    def student_view_company(company_id):
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        
        company = Company.query.get_or_404(company_id)
        
        # Increment view count
        company.view_count += 1
        db.session.commit()
        
        # Get jobs from this company
        company_jobs = JobPosting.query.filter_by(company_name=company.company_name, is_active=True).all()
        
        # Check if student follows this company
        is_following = CompanyFollow.query.filter_by(company_id=company_id, student_id=current_user.id).first() is not None
        
        # Get follower count
        follower_count = CompanyFollow.query.filter_by(company_id=company_id).count()
        
        return render_template('student/view_company.html', 
                             company=company, 
                             company_jobs=company_jobs,
                             is_following=is_following,
                             follower_count=follower_count)

    @app.route('/student/companies/follow/<int:company_id>', methods=['POST'])
    @login_required
    def student_follow_company(company_id):
        if current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('login'))
        
        company = Company.query.get_or_404(company_id)
        
        existing_follow = CompanyFollow.query.filter_by(company_id=company_id, student_id=current_user.id).first()
        
        if existing_follow:
            # Unfollow
            db.session.delete(existing_follow)
            db.session.commit()
            flash(f'You unfollowed {company.company_name}', 'info')
        else:
            # Follow
            follow = CompanyFollow(company_id=company_id, student_id=current_user.id)
            db.session.add(follow)
            db.session.commit()
            flash(f'You are now following {company.company_name}!', 'success')
        
        return redirect(url_for('student_view_company', company_id=company_id))
    @app.route('/employer/jobs/analytics/<int:job_id>')
    @login_required
    def employer_job_analytics(job_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        
        job = JobPosting.query.get_or_404(job_id)
        
        if job.employer_id != current_user.id:
            flash('You do not have permission to view this job analytics.', 'danger')
            return redirect(url_for('employer_jobs'))
        
        clicks = JobClick.query.filter_by(job_id=job_id).order_by(JobClick.clicked_date.desc()).all()
        
        return render_template('employer/job_analytics.html', job=job, clicks=clicks)

    @app.route('/employer/delete_student/<int:user_id>', methods=['POST'])
    @login_required
    def employer_delete_student(user_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        try:
            user = User.query.get(user_id)
            if not user:
                flash('User not found.', 'danger')
                return redirect(url_for('employer_dashboard'))
            profile = Profile.query.filter_by(user_id=user_id).first()
            cvs = CV.query.filter_by(user_id=user_id).all()
            upload_folder = current_app.config['UPLOAD_FOLDER']
            for cv in cvs:
                filepath = os.path.join(upload_folder, cv.filename)
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
            CV.query.filter_by(user_id=user_id).delete()
            if profile:
                db.session.delete(profile)
            db.session.delete(user)
            db.session.commit()
            flash(f'Student profile and all associated data have been deleted.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting student profile. Please try again.', 'danger')
        return redirect(url_for('employer_dashboard'))

    @app.route('/employer/delete_cv/<int:cv_id>', methods=['POST'])
    @login_required
    def employer_delete_cv(cv_id):
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
        try:
            cv = CV.query.get(cv_id)
            if not cv:
                flash('CV not found.', 'danger')
                return redirect(url_for('employer_dashboard'))
            user_id = cv.user_id
            upload_folder = current_app.config['UPLOAD_FOLDER']
            filepath = os.path.join(upload_folder, cv.filename)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    pass
            db.session.delete(cv)
            db.session.commit()
            flash('CV deleted successfully.', 'success')
            return redirect(url_for('employer_view_profile', user_id=user_id))
        except Exception as e:
            db.session.rollback()
            flash('Error deleting CV. Please try again.', 'danger')
            return redirect(url_for('employer_dashboard'))

    @app.route('/employer/details')
    @login_required
    def employer_details():
        if current_user.role != 'employer':
            flash('Access denied. Employers only.', 'danger')
            return redirect(url_for('login'))
            
        employer_info = {
            "company_name": "Your Company Name Here",
            "contact_email": "contact@yourcompany.com",
            "instructions": "Please use these details to contact us or access employer resources."
        }
        return render_template('employer/details.html', employer_info=employer_info)
    
    @app.route('/forgot_password', methods=['GET', 'POST'])
    def forgot_password():
        if request.method == 'POST':
            email = request.form.get('email', '').strip()
            user = User.query.filter_by(email=email).first()
            if not user:
                flash('No account found with that email.', 'danger')
                return render_template('forgot_password.html')
            token = serializer.dumps(user.id)
            reset_url = url_for('reset_password', token=token, _external=True)
            flash(f'Password reset link (simulated): {reset_url}', 'info')
            flash('A password reset link has been sent to your email (simulated).', 'success')
            return redirect(url_for('login'))
        return render_template('forgot_password.html')

    @app.route('/reset_password/<token>', methods=['GET', 'POST'])
    def reset_password(token):
        try:
            user_id = serializer.loads(token, max_age=3600)
        except itsdangerous.BadSignature:
            flash('Invalid or expired token.', 'danger')
            return redirect(url_for('login'))
        user = User.query.get(user_id)
        if not user:
            flash('User not found.', 'danger')
            return redirect(url_for('login'))
        if request.method == 'POST':
            password = request.form.get('password', '')
            confirm = request.form.get('confirm', '')
            if not password or not confirm:
                flash('Please fill out all fields.', 'danger')
                return render_template('reset_password.html')
            if password != confirm:
                flash('Passwords do not match.', 'danger')
                return render_template('reset_password.html')
            user.set_password(password)
            db.session.commit()
            flash('Your password has been reset. Please log in.', 'success')
            return redirect(url_for('login'))
        return render_template('reset_password.html')

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('500.html'), 500

    with app.app_context():
        db.create_all()
        try:
            db.create_all()
            print("Database tables created successfully!")
            test_user = User.query.first()
            print(f"Database connection test: {test_user is not None or 'No users yet'}")
        except Exception as e:
            print(f"Database error: {e}")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host='127.0.0.1', port=5000)