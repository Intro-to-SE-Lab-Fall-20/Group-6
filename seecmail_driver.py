#!/usr/bin/env python

from email.message import EmailMessage
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
#from email.mime.image import MIMEImage
from email import encoders
#from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
import email
from flask import Flask, redirect, url_for, render_template, request, session, flash
from flask_wtf import FlaskForm
from flask_login import login_required, current_user, login_user, logout_user, LoginManager, UserMixin
from flask_sqlalchemy import SQLAlchemy
from hashlib import md5
from sqlalchemy.exc import IntegrityError
from datetime import timedelta, datetime
import imghdr # for images 
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
app.secret_key = "testing"
# Stop from allowing huge uploads
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024  
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///databases/users.sqlite3'
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
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    password_ver = PasswordField(
        "Verify Password", validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError("Username has already been taken, choose another username.")

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError("Someone is already registered with this email address.  Choose another.")

class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    #password_hash = db.Column(db.String(80))
    password = db.Column(db.String(80))
    emails = db.relationship('SeecMail', backref='username', lazy='dynamic')

    def __repr__(self):
        return f"User: {self.username}" 

    #def set_password(self, password):
    #    self.password_hash = generate_password_hash(password)

    #def check_password(self, password):
    #    return check_password_hash(self.password_hash, password)

def refresh_inbox():
    emails = SeecMail.query.all()
    for e in emails: 
        db.session.delete(e)
    db.session.commit()
    #print(f"Inbox refreshed")

def get_inbox(folder='INBOX'):
    refresh_inbox()
    host = 'imap.gmail.com'
    mail = imaplib.IMAP4_SSL(host)
    mail.login(session["email"], session["password"])
    mail.select(folder)
    user = User.query.filter_by(email=session["email"]).first()
    print(f"Debug username: {user}")
    _, search_data = mail.search(None, "ALL")
    my_message = []
    for num in search_data[0].split():
        seecmail = SeecMail()
        _, data = mail.fetch(num, '(RFC822)')
        _, b = data[0]
        email_message = email.message_from_bytes(b)
        # Set subject, to, and sender (from)
        seecmail.subject = email_message['subject']
        seecmail.to = email_message['to']
        seecmail.sender = email_message['from']
        # Format and set time
        time_fmt = " ".join(email_message['date'].split()[:5])
        dt = datetime.strptime(time_fmt, '%a, %d %b %Y %H:%M:%S')
        seecmail.date = dt

        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                seecmail.body = part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                seecmail.html_body = part.get_payload(decode=True).decode()
        seecmail.mailbox = folder
        seecmail.emailid = md5(str(email_message).encode('utf-8')).hexdigest()
        seecmail.username = user
        db.session.add(seecmail)
    db.session.commit()

def search(searchTerm, folder="INBOX"):
    host = 'imap.gmail.com'
    mail = imaplib.IMAP4_SSL(host)
    mail.login(session["email"], session["password"])
    mail.select(folder)
    try:
        _, search_data = mail.search(None, "TEXT " + searchTerm)
    except:
        print("ERROR SEARCHING")

    my_message = []

    for num in search_data[0].split():
        email_data = {}
        # These codes are documented here:
        # https://tools.ietf.org/html/rfc3501
        _, data = mail.fetch(num, '(RFC822)')
        _, b = data[0]

        email_message = email.message_from_bytes(b)
        # Grabbing and formatting the data that we want to display
        for header in ['subject', 'to', 'from']: # , 'date']:
            email_data[header] = email_message[header]
        # Convert to datetime format for descending order
        time_fmt = " ".join(email_message['date'].split()[:5])
        dt = datetime.strptime(time_fmt, '%a, %d %b %Y %H:%M:%S')
        email_data['date'] = dt
        email_data['emailid'] = md5(str(email_message).encode('utf-8')).hexdigest()
        #print(f"Email_data_id: {email_data['emailid']}")
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                email_data['body'] = part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                email_data['html_body'] = part.get_payload(decode=True).decode()
        my_message.append(email_data)
    my_message.sort(key=lambda d: d['date'], reverse=True) # Reverse order, newest first
    return my_message

def get_inbox_messages(user):
    # Refresh the inbox database and grab emails
    inbox = get_inbox()
    return SeecMail.query.order_by(SeecMail.date.desc()).filter_by(username=user, mailbox='INBOX').all()

def get_sent_messages(user):
    folder = '"[Gmail]/Sent Mail"'
    inbox = get_inbox(folder)
    return SeecMail.query.order_by(SeecMail.date.desc()).filter_by(username=user, mailbox=folder).all()


class SeecMail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mailbox = db.Column(db.String(128))
    body = db.Column(db.String(2048))
    html_body = db.Column(db.String(2048))
    date = db.Column(db.DateTime, index=True)
    to = db.Column(db.String(128))
    sender = db.Column(db.String(128))
    subject = db.Column(db.String(1024))
    emailid = db.Column(db.String(128), unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return f"Email subject: {self.subject}"

@app.route("/", methods=["POST", "GET"])
@app.route("/home", methods=["POST", "GET"])
def home():
    #if request.method == "POST":
        #render_template("login.html")
       #return redirect(url_for("login"))
   # else:
      #  return render_template("index.html")
    return redirect(url_for("login"))


@app.route("/user/<username>/compose", methods=["POST", "GET"])
@login_required
def compose(username):
    # If they are hitting the send button
    #if not "email" in session:
    #    flash("You are not logged in.")
    #    return redirect(url_for("login"))
    if request.method == "POST":
        #msg = EmailMessage()
        # Mixed message
        msg = MIMEMultipart("alternative")
        msg["From"] = session["email"]
        msg["To"]= request.form["email_to"]
        msg["Subject"]= request.form["email_subject"]
        #msg.set_content(request.form["email_body"])
        text = request.form["email_body"]
        #msg.set_content(body)

        # Attaching the text as plain text and html 
        body_plain = MIMEText(text, 'plain')
        body_html = MIMEText(text, 'html')
        msg.attach(body_plain)
        msg.attach(body_html)
        
        # Finding out what/if there is an attachment
        upload = request.files['attachment']

        # Checking for an upload, if there is then Uploading file to our assets directory
        if upload.filename != '':  
            filename = secure_filename(upload.filename)
            assets_dir = os.path.join(os.getcwd(), 'uploads')
            # print(f"Assets: {assets_dir}")
            upload.save( os.path.join('uploads', filename) )
            # Read the file data
            with open(os.path.join(assets_dir, upload.filename), 'rb') as f:
                # Reading in the file we just saved to uploads and attaching it 
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', 'attachment; filename="%s"' % basename(upload.filename))
                msg.attach(part)


#            msg.add_attachment(file_data, maintype='image', subtype=file_type,
#                               filename=filename)
            msg.attach(part) 
            flash("File uploaded")


        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            # Actually sending the email
            smtp.login(session["email"], session["password"])
            #msg.set_type('text/html')
            #smtp.send_message(msg)
            smtp.sendmail(msg["From"], msg["To"], msg.as_string())

        flash("Message sent")
        return redirect(url_for("user", username=username))

    else:
        return render_template("compose.html", username=username)

@app.route("/login", methods=["POST", "GET"])
def login():
    # event if user is logged in and attempts to go to /login
    if current_user.is_authenticated:
        #print(f"Current_user: {current_user}")
        return redirect(url_for('user', username=current_user.username))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        print(f"DEBUG: {user}")
        if user is None: # or not user.check_password(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        # Now log into gmail server
        server = smtplib.SMTP(host='smtp.gmail.com', port=587)
        server.ehlo()
        server.starttls()
        try:
            server.login(user.email, form.password.data)
            flash("Log in successful!")
            # Set session variables after log in is successful 
            session["email"] = user.email
            session["username"] = user.username
            session["password"] = form.password.data
            return redirect(url_for('user', username=user.username))
        except smtplib.SMTPAuthenticationError as e:
            print(f"Error: {e}")
            flash("You have entered an invalid username or password, try again!")
            flash("Make sure this account is a valid and registered gmail account.")
            flash("Your account may not allow less secure apps or requires two-factor authentication: "
                      "https://myaccount.google.com/u/1/lesssecureapps?pli=1&pageId=none")
            return render_template("login.html", title="Sign In", form=form)
    else:
        return render_template("login.html", title='Sign In', form=form)

@app.route("/register", methods=["POST", "GET"])
def register():
#    if current_user.is_authenticated:
#        print(f"You are already authenticated: {current_user}")
#        return redirect(url_for(user))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, password=form.password.data)
        #user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("You are now registered as a new user.")
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route("/user/<username>/forward/<emailid>", methods=["POST", "GET"])
@login_required
def forward(username, emailid):
    message = SeecMail.query.filter_by(emailid=emailid).first()
    if request.method == "POST":
        #msg = EmailMessage()
        # Mixed message
        msg = MIMEMultipart("alternative")
        msg["From"] = session["email"]
        msg["To"]= request.form["email_to"]
        msg["Subject"]= request.form["email_subject"]
        #msg.set_content(request.form["email_body"])
        text = request.form["email_body"]

        body_plain = MIMEText(text, 'plain')
        body_html = MIMEText(text, 'html')
        msg.attach(body_plain)
        msg.attach(body_html)

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(session["email"], session["password"])
            smtp.sendmail(msg["From"], msg["To"], msg.as_string())

        flash("Message forwarded")
        return redirect(url_for("user", username=username))

    return render_template("forward.html", message=message, username=username)

@app.route("/user/<username>", methods=["POST", "GET"])
@login_required
def user(username):
    #print(f"User from func: {username}")
    user = User.query.filter_by(username=username).first_or_404()
    inbox = get_inbox_messages(user)

    if request.method == "POST":
        inbox = search(request.form['search_term'])
        if not inbox:
            flash("No matches found for " + request.form['search_term'], 'searched_for')
            return render_template("search.html", inbox = inbox, username = user)
        else:
            flash("Search results for " + request.form['search_term'], 'searched_for')
            return render_template("search.html", inbox = inbox, username = user)

    return render_template("user.html", inbox=inbox, username=user)

@app.route("/user/<username>/viewemail/<emailid>")
@login_required
def viewemail(username, emailid):
    #inbox = get_inbox()
    #message = get_email(inbox, emailid)
    message = SeecMail.query.filter_by(emailid=emailid).first()
    #print(f"Message: {message}")
    return render_template('read.html', message=message, username=username, emailid=emailid)


@app.route("/user/<username>/sent", methods=["POST", "GET"])
@login_required
def sent(username):
    user = User.query.filter_by(username=username).first_or_404()
    inbox = get_sent_messages(user)
    return render_template("user.html", inbox=inbox, user=user)

@app.route("/logout")
def logout():
    flash("You have been logged out")
    logout_user()
    return redirect(url_for('login'))
    if "email" in session:
        user = session["email"]
        flash(f"You have been logged out, {user}!", "info")
        session.pop("email", None)
        session.pop("password", None)
        return redirect(url_for("login"))
    else:
        flash(f"session: {session}")
        flash(f"You are not logged in yet")
        return redirect(url_for("login"))

def reset_db(db):
    users = User.query.all()
    emails = SeecMail.query.all()
    for u in users:
        db.session.delete(u)
    for e in emails:
        db.session.delete(e)
    db.session.commit()

if __name__ == "__main__":
    db.create_all()
    #reset_db(db)
    app.run(debug=True)



