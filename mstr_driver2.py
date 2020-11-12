from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_wtf import FlaskForm
from flask_login import login_required, current_user, login_user, logout_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from hashlib import md5
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime
import imghdr  # for images
import mimetypes
import os
from os.path import basename
import smtplib
import imaplib
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.urls import url_parse
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, ValidationError, Email, EqualTo

app = Flask(__name__)
login = LoginManager(app)
app.secret_key = "masterKey"
# Stop from allowing huge uploads
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///databases/mstrDB.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember me')
    submit = SubmitField('Sign In')


class RegistrationForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_ver = PasswordField(
        "Verify Password", validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Username has already been taken, choose another username.")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    # password_hash = db.Column(db.String(80))
    password = db.Column(db.String(80))

    def __repr__(self):
        return f"User: {self.username}"

        # def set_password(self, password):
    #    self.password_hash = generate_password_hash(password)

    # def check_password(self, password):
    #    return check_password_hash(self.password_hash, password)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(2048))
    date = db.Column(db.DateTime, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"Email subject: {self.subject}"


@app.route("/", methods=["POST", "GET"])
@app.route("/mstrHome", methods=["POST", "GET"])
def mstrHome():
    # if request.method == "POST":
    # render_template("login.html")
    # return redirect(url_for("login"))
    # else:
    #  return render_template("index.html")
    return redirect(url_for("mstrLogin"))


@app.route("/mstrLogin", methods=["POST", "GET"])
def mstrLogin():
    # event if user is logged in and attempts to go to /login
    if current_user.is_authenticated:
        # print(f"Current_user: {current_user}")
        return redirect(url_for('mstrUser', username=current_user.username))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        print(f"DEBUG: {user}")
        if user is None:  # or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('mstrLogin'))
        login_user(user, remember=form.remember_me.data)
        # Now log into gmail server
        try:
            #flash("Log in successful!")
            # Set session variables after log in is successful
            session["username"] = user.username
            session["password"] = form.password.data
            return redirect(url_for('mstrUser', username=user.username))
        except smtplib.SMTPAuthenticationError as e:
            print(f"Error: {e}")
            flash("You have entered an invalid username or password, try again!")
            return render_template("mstrLogin.html", title="Sign In", form=form)
    else:
        return render_template("mstrLogin.html", title='Sign In', form=form)


@app.route("/mstrRegister", methods=["POST", "GET"])
def mstrRegister():
    #    if current_user.is_authenticated:
    #        print(f"You are already authenticated: {current_user}")
    #        return redirect(url_for(user))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, password=form.password.data)
        # user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("You are now registered as a new user.")
        return redirect(url_for('mstrLogin'))
    return render_template('mstrRegister.html', title='Register', form=form)


@app.route("/mstrUser/<username>", methods=["POST", "GET"])
@login_required
def mstrUser(username):
    # print(f"User from func: {username}")
    user = User.query.filter_by(username=username).first_or_404()


    return render_template("mstrUser.html", username=user)


@app.route("/mstrUser/mstrNotes.html", methods=["POST", "GET"])
@login_required
def mstrNotes():

    notelist = Note.query.filter_by(user_id=session['username'])

    return render_template("mstrNotes.html",username = session['username'], notelist=notelist)



@app.route("/mstrUser/readnotes/<noteid>", methods=["POST", "GET"])
@login_required
def readnotes(noteid):
    # inbox = get_inbox()
    # message = get_email(inbox, emailid)
    note = Note.query.filter_by(id=noteid, user_id = session['username']).first()
    # print(f"Message: {message}")
    return render_template('readnotes.html', note=note)


@app.route("/mstrUser/newNote", methods = ["POST", "GET"])
@login_required
def newNote():
    if request.method == "POST":
        body = request.form['note_body']
        note = Note(body = body, user_id = session['username'], date = datetime.utcnow())
        db.session.add(note)
        db.session.commit()
        return redirect(url_for('mstrNotes'))
    else:
        return render_template('newNote.html')


@app.route("/logout")
def logout():
    flash("You have been logged out")
    logout_user()
    return redirect(url_for('mstrLogin'))


def reset_db(db):
    users = User.query.all()
    notes = Note.query.all()
    for u in users:
        db.session.delete(u)
    for n in notes:
        db.session.delete(n)
    db.session.commit()


if __name__ == "__main__":
    #reset_db(db)
    app.run(debug=True, port=5001)



