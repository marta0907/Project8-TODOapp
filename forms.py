from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.fields.simple import EmailField, PasswordField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField

# RegisterForm to register new users
class RegisterForm(FlaskForm):
    name=StringField("Name", validators=[DataRequired()])
    email=EmailField("Email", validators=[DataRequired()])
    password=PasswordField("Password", validators=[(DataRequired())])
    submit = SubmitField("Submit registration")

# LoginForm to login existing users
class LoginForm(FlaskForm):
    email=EmailField("Email",validators=[DataRequired()])
    password=PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log In")
