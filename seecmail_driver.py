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
from datetime import timedelta, datetime
import imghdr # for images 
import mimetypes
import os 
from os.path import basename
import smtplib
import imaplib
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "testing"
# Stop from allowing huge uploads
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024

# Default folder is the inbox
def get_inbox(folder="INBOX"): 
    host = 'imap.gmail.com'
    mail = imaplib.IMAP4_SSL(host)
    mail.login(session["email"], session["password"])
    mail.select(folder)
    _, search_data = mail.search(None, "ALL")
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
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                email_data['body'] = part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                email_data['html_body'] = part.get_payload(decode=True).decode()
        my_message.append(email_data)
    my_message.sort(key=lambda d: d['date'], reverse=True) # Reverse order, newest first
    mail.logout()
    return my_message

def search(searchTerm):
    server = "imap.gmail.com"  # For example, “imap.gmail.com“
    user = session["email"]  # For example, “example.imap.python.user“
    password = session["password"]  # For example, “example.imap.python.password”
    mailbox = "Inbox"  # For example, “Inbox” or “[Gmail]/All Mail“
    mail = imaplib.IMAP4_SSL(server)
    mail.login(user, password)
    mail.select(mailbox, True)
    my_message = []
    try:
        _, search_data = mail.search(None, "TEXT " + searchTerm)
        #print(search_data)
    except:
        print("SEARCH ERROR")

    for num in search_data[0].split():
        email_data = {}
        # These codes are documented here:
        # https://tools.ietf.org/html/rfc3501
        _, data = mail.fetch(num, '(RFC822)')
        _, b = data[0]
        #print(b)

        email_message = email.message_from_bytes(b)
        # Grabbing and formatting the data that we want to display
        for header in ['subject', 'to', 'from']:  # , 'date']:
            email_data[header] = email_message[header]
        # Convert to datetime format for descending order
        time_fmt = " ".join(email_message['date'].split()[:5])
        dt = datetime.strptime(time_fmt, '%a, %d %b %Y %H:%M:%S')
        email_data['date'] = dt
        for part in email_message.walk():
            if part.get_content_type() == "text/plain":
                email_data['body'] = part.get_payload(decode=True).decode()
            elif part.get_content_type() == "text/html":
                email_data['html_body'] = part.get_payload(decode=True).decode()
        my_message.append(email_data)
    my_message.sort(key=lambda d: d['date'], reverse=True)  # Reverse order, newest first
    mail.logout()
    return my_message


@app.route("/", methods=["POST", "GET"])
#@app.route("/home", methods=["POST", "GET"])
def home():
    #if request.method == "POST":
        #render_template("login.html")
       #return redirect(url_for("login"))
   # else:
      #  return render_template("index.html")
    return redirect(url_for("user"))


@app.route("/compose", methods=["POST", "GET"])
def compose():
    # If they are hitting the send button
    if not "email" in session:
        flash("You are not logged in.")
        return redirect(url_for("login"))
    # For debugging
    #print(session["email"])

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
        return redirect(url_for("user"))

    else:
        return render_template("compose.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # if they press the login button
        if 'login_button' in request.form:
            session.permanent = False
            # Grab the data from the boxes after you hit login
            email = request.form["user_email"] # This variable from login.html
            if email == '':
                return redirect(url_for("login"))
            session["email"] = email
            password = request.form["user_password"]  # This variable from login.html
            if password == '':
                return redirect(url_for("login"))
            session["password"] = password

            # This will be where we do authentication 
            server = smtplib.SMTP(host='smtp.gmail.com', port=587)
            server.ehlo()
            server.starttls()
            try:
                server.login(email, password)
                flash("Login successful!")
                return redirect(url_for("user"))
            except smtplib.SMTPAuthenticationError as e:
                print(f"Error: {e}")
                flash("You have entered an invalid username or password, try again!")
                flash("Your account may not allow less secure apps or requires two-factor authentication: "
                      "https://myaccount.google.com/u/1/lesssecureapps?pli=1&pageId=none")
                # Clear these values for security purposes
                session["email"] = None
                session["password"] = None
                return render_template("login.html")
    else:
        return render_template("login.html")


@app.route("/user", methods=["POST", "GET"])
def user():
    email = None
    if request.method == "POST":
        user = session["email"]
        password = session["password"]
        inbox = search(request.form['searchTerm'])
        return render_template("user.html", inbox=inbox, user = user)
    if "email" in session:
        user = session["email"]
        password = session["password"]
        inbox = get_inbox()
        return render_template("user.html", inbox=inbox, user=user)
    else:
        flash("You are not logged in")
        return redirect(url_for("login"))

@app.route("/sent", methods=["POST", "GET"])
def sent():
    if "email" in session:
        user = session["email"] 
        password = session["password"]
        inbox = get_inbox(folder='"[Gmail]/Sent Mail"')
        return render_template("user.html", inbox=inbox, user=user)
    else:
        flash("You are not logged in!")
        return redirect(url_for("login"))

@app.route("/logout")
def logout():
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



if __name__ == "__main__":
    app.run(debug=True)



