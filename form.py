# Import package
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, EmailField, TextAreaField
from wtforms.validators import DataRequired, URL, Email
from flask_ckeditor import CKEditorField


# Configure form
class CreatePostForm(FlaskForm):
	title = StringField("Blog Post Title", validators=[DataRequired()])
	subtitle = StringField("Subtitle", validators=[DataRequired()])
	# author = StringField("Your Name", validators=[DataRequired()])
	img_url = StringField("Blog Image URL", validators=[DataRequired(), URL()])
	body = CKEditorField("Blog Content", validators=[DataRequired()])
	submit = SubmitField("Submit Post")


class CreateCommentForm(FlaskForm):
	comment_text = CKEditorField("Blog Comment", validators=[DataRequired()])
	submit = SubmitField("Submit Comment")


class ContactForm(FlaskForm):
	name = StringField("Name", validators=[DataRequired()])
	email = EmailField("Email", validators=[DataRequired(), Email()])
	phone = StringField("Phone", validators=[DataRequired()])
	message = TextAreaField("Message", validators=[DataRequired()])
	submit = SubmitField("Send me")


class RegisterForm(FlaskForm):
	name = StringField("Name", validators=[DataRequired()])
	email = EmailField("Email", validators=[DataRequired(), Email()])
	password = PasswordField("Password", validators=[DataRequired()])
	submit = SubmitField("Send me")


class LoginForm(FlaskForm):
	email = EmailField("Email", validators=[DataRequired(), Email()])
	password = PasswordField("Password", validators=[DataRequired()])
	submit = SubmitField("Send me")
