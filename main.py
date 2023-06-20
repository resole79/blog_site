# Import package
import os
from form import ContactForm, CreateCommentForm, CreatePostForm, RegisterForm, LoginForm
from dotenv import load_dotenv
from functools import wraps
from flask import Flask, request, render_template, redirect, url_for, flash
from flask_ckeditor import CKEditor
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from flask_bootstrap import Bootstrap
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from flask_gravatar import Gravatar
from werkzeug.exceptions import HTTPException
from werkzeug.security import generate_password_hash, check_password_hash
import datetime
import smtplib

load_dotenv()

my_email = os.environ.get("MY_EMAIL")
to_addr = os.environ.get("TO_ADDR")
password = os.environ.get("PASSWORD_SMTP")

app = Flask(__name__)
db = SQLAlchemy()
Bootstrap(app)
login_manager = LoginManager()
ckeditor = CKEditor()

app.config['SECRET_KEY'] = os.urandom(24)
app.config['CKEDITOR_PKG_TYPE'] = 'basic'

# Connect to db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize app
db.init_app(app)
login_manager.init_app(app)
ckeditor.init_app(app)
gravatar = Gravatar(app)


# Configure table
class BlogUser(UserMixin, db.Model):
	__tablename__ = "user"
	
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(100), unique=True)
	password = db.Column(db.String(100))
	name = db.Column(db.String(1000))
	post = relationship("BlogPost", back_populates="author")
	comment = relationship("BlogComment", back_populates="author_comment")


class BlogPost(db.Model):
	__tablename__ = "posts"
	id = db.Column(db.Integer, primary_key=True)
	author_id = db.Column(db.Integer, ForeignKey("user.id"))
	author = relationship("BlogUser", back_populates="post")
	comment_post = relationship("BlogComment", back_populates="post_comment")
	title = db.Column(db.String(250), unique=True, nullable=False)
	subtitle = db.Column(db.String(250), nullable=False)
	date = db.Column(db.String(250), nullable=False)
	body = db.Column(db.Text, nullable=False)
	img_url = db.Column(db.String(250), nullable=False)


class BlogComment(db.Model):
	__tablename__ = "comments"
	id = db.Column(db.Integer, primary_key=True)
	author_comment_id = db.Column(db.Integer, ForeignKey("user.id"))
	author_comment = relationship("BlogUser", back_populates="comment")
	post_comment_id = db.Column(db.Integer, ForeignKey("posts.id"))
	post_comment = relationship("BlogPost", back_populates="comment_post")
	comment_text = db.Column(db.Text, nullable=False)


# Create all table
with app.app_context():
	db.create_all()


# decorator to give permission oly admin user
def admin_only(f):
	@wraps(f)
	def decorated_function(*args, **kwargs):
		if (current_user.is_authenticated and current_user.id != 1) or current_user.is_anonymous:
			return render_template('four_hundred_three.html', userlog=current_user), 403
		
		return f(*args, **kwargs)
	
	return decorated_function


# Function to check HTTP Exception
@app.errorhandler(HTTPException)
def handle_bad_request(e):
	data_error = {"code": e.code, "name": e.name, "description": e.description}
	return render_template('error.html', error=data_error, userlog=current_user), e.code


@login_manager.user_loader
def loading_user_def(user_id):
	return db.session.query(BlogUser).filter_by(id=user_id).one()


# Function to render 403 page
@app.route('/403')
def four_hundred_three():
	return render_template("four_hundred_three.html", userlog=current_user)


# Function to get all post
@app.route('/')
def get_all_posts():
	author_post = ""
	posts = db.session.query(BlogPost).all()
	for post in posts:
		author_post = db.session.query(BlogUser).where(BlogUser.id == post.author_id)
		print(author_post)
	return render_template("index.html", all_posts=posts, author_post=author_post, userlog=current_user)


# Function to create new post
@app.route('/new_post', methods=["GET", "POST"])
@login_required
@admin_only
def new_post():
	# Call class CreatePostForm
	create_post_form = CreatePostForm()
	
	year = datetime.datetime.now().year
	month = datetime.datetime.now().month
	day = datetime.datetime.now().day
	
	today = datetime.datetime(year, month, day)
	today_format = today.strftime("%b %d, %Y")
	
	# Check form validate
	if create_post_form.validate_on_submit() and request.method == 'POST':
		create_new_post = BlogPost(author_id=current_user.id, title=create_post_form.title.data,
								   subtitle=create_post_form.subtitle.data, date=today_format,
								   img_url=create_post_form.img_url.data, body=create_post_form.body.data)
		
		db.session.add(create_new_post)
		db.session.commit()
		
		return redirect(url_for('get_all_posts'))
	
	return render_template("make_post.html", form=create_post_form, userlog=current_user)


# Function to show post and comment by id post
@app.route("/post/<int:id_post>", methods=["GET", "POST"])
def show_post(id_post):
	# Call class CreateCommentForm
	create_comment_form = CreateCommentForm()
	# Create query to check comment by id_post
	all_comment = db.session.query(BlogComment).where(BlogComment.post_comment_id == id_post).all()
	# Check form validate
	if create_comment_form.validate_on_submit() and request.method == "POST":
		# check user is authenticated
		if current_user.is_authenticated:
			new_comment = BlogComment()
			new_comment.author_comment_id = current_user.id
			new_comment.post_comment_id = id_post
			new_comment.comment_text = create_comment_form.comment_text.data
			
			db.session.add(new_comment)
			db.session.commit()
			
			return redirect(url_for('show_post', id_post=id_post))
		else:
			flash("You need to login or register to comment")
			return redirect(url_for('login'))
	
	# Create query to check post by id_post
	requested_post = db.session.query(BlogPost).where(BlogPost.id == id_post).first()
	
	return render_template("post.html", form=create_comment_form, all_comment=all_comment, post=requested_post,
						   userlog=current_user)


# Function tu update post
@app.route("/edit-post/<int:id_post>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_post(id_post):
	# Call class CreatePostForm
	create_post_form = CreatePostForm()
	# Create query to check post by id_post
	requested_post = db.session.query(BlogPost).where(BlogPost.id == id_post).first()
	
	# Populate my form
	form_to_edit = CreatePostForm(
		title=requested_post.title,
		subtitle=requested_post.subtitle,
		img_url=requested_post.img_url,
		body=requested_post.body)
	
	# Check form validate
	if create_post_form.validate_on_submit() and request.method == 'POST':
		requested_post.title = create_post_form.title.data
		requested_post.subtitle = create_post_form.subtitle.data
		requested_post.body = create_post_form.body.data
		requested_post.img_url = create_post_form.img_url.data
		db.session.commit()
		
		return redirect(url_for('get_all_posts'))
	
	return render_template("make_post.html", id_post=id_post, form=form_to_edit, userlog=current_user)


# Function to delete post
@app.route("/delete/<int:id_post>", methods=["GET", "POST"])
@login_required
@admin_only
def delete_post(id_post):
	# Create query to check all post
	all_posts = db.session.query(BlogPost).all()
	
	# Check id_post
	if id_post:
		# Create query to check post to delete by id_post
		post_to_delete = db.session.query(BlogPost).where(BlogPost.id == id_post).first()
		if post_to_delete:
			db.session.delete(post_to_delete)
			db.session.commit()
			
			return redirect(url_for('get_all_posts'))
	
	return render_template("index.html", all_posts=all_posts, userlog=current_user)


# Function to register new user
@app.route('/register', methods=["GET", "POST"])
def register():
	# Call class RegisterForm
	register_form = RegisterForm()
	# Check form validate
	if register_form.validate_on_submit() and request.method == "POST":
		# Create query to check user by email
		user = db.session.query(BlogUser).where(BlogUser.email == register_form.email.data).first()
		# Check if user is not register
		if not user:
			new_user = BlogUser()
			new_user.name = register_form.name.data
			new_user.email = register_form.email.data
			new_user.password = generate_password_hash(register_form.password.data, method='pbkdf2:sha256', salt_length=8)
			db.session.add(new_user)
			db.session.commit()
			
			# login user
			login_user(new_user)
			
			return redirect(url_for('get_all_posts'))
		else:
			flash("You have already signed up with that email, log in instead!")
			return redirect(url_for("login"))
	
	return render_template("register.html", form=register_form, userlog=current_user)


# Function to log user
@app.route('/login', methods=["GET", "POST"])
def login():
	# Call class LoginForm
	login_form = LoginForm()
	# Check form validate
	if login_form.validate_on_submit() and request.method == "POST":
		# Create query to check user by email
		user = db.session.query(BlogUser).where(BlogUser.email == login_form.email.data).first()
		if user:
			# Check password is match
			if check_password_hash(user.password, login_form.password.data):
				# login user
				login_user(user)
				return redirect(url_for("get_all_posts"))
			else:
				flash("Password incorrect, please try again")
		else:
			flash("The email does not exist, please try again")
	
	return render_template("login.html", form=login_form, userlog=current_user)


# Function to log out user
@app.route('/logout')
def logout():
	logout_user()
	return redirect(url_for('get_all_posts'))


# Function to render about page
@app.route("/about")
def about():
	return render_template("about.html", userlog=current_user)


# Function to render contact page
@app.route('/contact', methods=["GET", 'POST'])
def contact_send_page():
	# Call class ContactForm
	contact_form = ContactForm()
	
	if contact_form.validate_on_submit() and request.method == 'POST':
		send_email(contact_form.name.data, contact_form.email.data, contact_form.phone.data, contact_form.message.data)
	
	return render_template('contact.html', form=contact_form, userlog=current_user)


# Function to send email
def send_email(name, email, phone, message):
	new_message = f"{name}\n{email}\n{phone}\n{message}"
	
	with smtplib.SMTP("smtp.gmail.com") as connection:
		connection.starttls()
		connection.login(my_email, password)
		connection.sendmail(my_email, to_addr, f"Subject: Contact from Blog\n\n{new_message}")
		flash("Form submission successful!")


if __name__ == "__main__":
	app.run(host='0.0.0.0', port=8080, debug=True)
