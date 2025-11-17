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
    job_type = db.Column(db.String(50))
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
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this-in-production')
    
    # Use PostgreSQL for production, SQLite for local development
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///cv_drop.db"
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), "uploads")

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message_category = 'info'

    serializer = itsdangerous.URLSafeTimedSerializer(app.config['SECRET_KEY'])

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

 
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template("500.html"), 500

    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Database error: {e}")

    return app



app = create_app()


# Optional - Only local debug server runs this portion
if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
