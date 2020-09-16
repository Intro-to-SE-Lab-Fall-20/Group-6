#!/usr/bin/env python

from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta
from flask_sqlalchemy import SQLAlchemy
#from second import second

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

# This is a good example of a way to debug things in Flask - dump it to a temporary page
#@app.route("/view")
#def view():
#    return render_template("view.html", values=Users.query.all())

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "POST":
        session.permanent = True
        # Grab the data from the boxes after you hit login
        email = request.form["user_email"] # This variable from login.html
        session["email"] = email  
        password = request.form["user_password"]  # This variable from login.html
        session["password"] = password
        # Look for user in the database
        # This will be where we do authentication 
#        found_user = Users.query.filter_by(email=email).first()
#        print(f"Found user: {found_user}")
#        if found_user: 
#            session["email"] = found_user.email
#        else:
#            usr = Users(email) #, "random_pass")
#            db.session.add(usr)
#            db.session.commit()

        flash("Login successful!")
        return redirect(url_for("user"))
    else:
        return render_template("login.html")

@app.route("/user", methods=["POST", "GET"])
def user():
    email = None
    if "email" in session:
        user = session["email"]
#        return f"<h1>{user}'s email messages (that don't exist)"
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


if __name__ == "__main__":
    db.create_all()
    app.run(debug=True)



