#!/usr/bin/env python

from email.message import EmailMessage
import email
from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, datetime
#import imghdr # for images later
import smtplib
import imaplib

app = Flask(__name__)
app.secret_key = "testing"


def get_inbox(): 
    host = 'imap.gmail.com'
    mail = imaplib.IMAP4_SSL(host)
    mail.login(session["email"], session["password"])
    mail.select("inbox")
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
    return my_message

@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/compose", methods=["POST", "GET"])
def compose():
    # If they are hitting the send button
    if not "email" in session:
        flash("You are not logged in.")
        return redirect(url_for("login"))
    # For debugging
    print(session["email"])

    if request.method == "POST":
        msg = EmailMessage()
        msg["From"] = session["email"]
        msg["To"]= request.form["email_to"]
        msg["Subject"]= request.form["email_subject"]
        msg.set_content(request.form["email_body"])

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(session["email"], session["password"])
            msg.set_type('text/html')
            smtp.send_message(msg)


        flash("Message sent")
        return redirect(url_for("user"))

    else:
        return render_template("compose.html")

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        # if they press the login button
        if 'login_button' in request.form:
            session.permanent = True
            # Grab the data from the boxes after you hit login
            email = request.form["user_email"] # This variable from login.html
            session["email"] = email  
            password = request.form["user_password"]  # This variable from login.html
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
    if "email" in session:
        user = session["email"]
        password = session["password"]
        inbox = get_inbox()
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



