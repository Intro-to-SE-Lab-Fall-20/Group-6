#!/usr/bin/env python

from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
import getpass

app = Flask(__name__)
app.secret_key = "testing"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(days=5)
#app.register_blueprint(second, url_prefix="")

db = SQLAlchemy(app)

class Users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True) # this is to keep things unique
    email = db.Column(db.String(100))
    password = db.Column(db.String(100))

    def __init__(self, email, password):
        self.email = email
        self.password = password

@app.route("/")
@app.route("/home")
def home():
    return render_template("index.html")

@app.route("/view")
def view():
    return render_template("view.html", values=Users.query.all())

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
            # Look for user in the database
            # This will be where we do authentication 
            found_user = Users.query.filter_by(email=email).first()

            if found_user: 
                session["email"] = found_user.email
                if password != found_user.password: 
                    flash("You have entered the wrong password!")
                    return render_template("login.html")
                else:
                    # This is for debugging - this can't be good practice
                    session["password"] = password
            else:
                flash("Username not found in database")
                return render_template("login.html")

            flash("Login successful!")
            return redirect(url_for("user"))
        # They have pressed the Register button
        elif 'register_button' in request.form:
            email = request.form["user_email"]
            password = request.form["user_password"]
            new_user = Users(email, password)
            found_user = Users.query.filter_by(email=email).first()
            if found_user:
                flash("This user is already registered.  Please login or register a new user.")
                return render_template("login.html")
            db.session.add(new_user)
            db.session.commit()
            flash("You have been registered.  You may now login with credentials")
            return render_template("login.html")
    else:
        return render_template("login.html")


@app.route("/user", methods=["POST", "GET"])
def user():
    email = None
    if "email" in session:
        user = session["email"]
        return render_template("user.html", user=user)
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

def reset_database(db):
    db.drop_all()

def setup_database(db):
    admin = Users(email="admin@email.com", password="secret")
    found_user = Users.query.filter_by(email=admin.email).first()
    if not found_user:
        db.session.add(admin)
    user = Users(email="user@email.com", password="supersecret")
    found_user = Users.query.filter_by(email=user.email).first()
    if not found_user:
        db.session.add(user)
    db.session.commit()

if __name__ == "__main__":
    db.create_all()
    setup_database(db)
    app.run(debug=True)
    reset_database(db)



