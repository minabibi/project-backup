import os
import requests 
from functools import wraps
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_session import Session
from models import *
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

# sqlite:///happy_database.db
# export DATABASE_URL="postgresql://localhost/users"

# psql postgres
# \c users
# SELECT * FROM users;
# \dt
# background: #f1e9e3;

# Database configuration
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
db.init_app(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

@app.route("/add_accomplishment", methods=["POST"])
@login_required
def add_accomplishment():
    user_id = session["user_id"]
    text = request.form.get("accomplishment")

    if text:
        accomplishment = Accomplishment(text=text, user_id=user_id)
        db.session.add(accomplishment)
        db.session.commit()
        flash("Your accomplishment has been shared!")

    return redirect("/")

@app.route("/", methods=['GET', 'POST'])
@login_required
def index():
    user_id = session["user_id"]
    user = User.query.get(user_id)

    if request.method == 'POST':
        if 'goal' in request.form:
            goal_text = request.form.get('goal')
            if goal_text:
                goal = Goal(text=goal_text, user_id=user_id)
                db.session.add(goal)
                db.session.commit()
                return redirect("/") 

        elif 'affirmation' in request.form:
            affirmation_text = request.form.get('affirmation')
            if affirmation_text:
                affirmation = Affirmation(text=affirmation_text, user_id=user_id)
                db.session.add(affirmation)
                db.session.commit()
                return redirect("/")
            
    goals = Goal.query.filter_by(user_id=user_id).all()
    affirmations = Affirmation.query.filter_by(user_id=user_id).all()
    accomplishments = Accomplishment.query.all()
    
    return render_template("index.html", user=user.username, user_id=user_id, goals=goals, affirmations=affirmations, accomplishments=accomplishments)

@app.route("/toggle_goal/<int:goal_id>/<string:is_attained_str>")
@login_required
def toggle_goal(goal_id, is_attained_str):
    user_id = session["user_id"]
    goal = Goal.query.get(goal_id)
    if goal and goal.user_id == user_id:
        goal.is_attained = is_attained_str == "true"

        if goal.is_attained:
            flash("Congratulations! You just accomplished a new goal.")
            
        if is_attained_str == "false":
            goal.shared_goal = None

        db.session.commit()
        return redirect("/")
    else:
        return "Goal not found or you do not have permission to change it", 404
    
@app.route("/delete_goal/<int:goal_id>")
@login_required
def delete_goal(goal_id):
    user_id = session["user_id"]
    goal = Goal.query.get(goal_id)
    if goal and goal.user_id == user_id:
        db.session.delete(goal)
        db.session.commit()
    else:
        flash("Goal not found or you do not have permission to delete it.")
    return redirect("/")
    
@app.route("/delete_affirmation/<int:affirmation_id>")
@login_required
def delete_affirmation(affirmation_id):
    affirmation = Affirmation.query.get(affirmation_id)
    if affirmation and affirmation.user_id == session["user_id"]:
        db.session.delete(affirmation)
        db.session.commit()
    else:
        flash("Affirmation not found or you do not have permission to delete it.")
    return redirect("/")

@app.route("/delete_accomplishment/<int:accomplishment_id>")
@login_required
def delete_accomplishment(accomplishment_id):
    user_id = session["user_id"]
    accomplishment = Accomplishment.query.get(accomplishment_id)

    if accomplishment and accomplishment.user_id == user_id:
        db.session.delete(accomplishment)
        db.session.commit()
    else:
        flash("Accomplishment not found or you do not have permission to delete it.")

    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message= "must provide username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message= "must provide password")
        
        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            return render_template("error.html", message= "must provide a confirmation for your password")
        
        # Ensure confirmation and password matches
        elif request.form.get("confirmation") != request.form.get("password"):
            return render_template("error.html", message= "confirmation must be the same as password")

        # Query database for username
        existing_user  =  User.query.filter_by(username = request.form.get("username")).first()
        print(existing_user)
        
        if existing_user:
            return render_template("error.html", message="Username already exists")

        new_user = User(username=request.form.get("username"))
        new_user.set_password(request.form.get("password"))

        # Add new user to the database
        db.session.add(new_user)
        db.session.commit()

        session["user_id"] = new_user.id
        
        flash(f"Succesfully registerd {new_user.username}")
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return render_template("error.html", message="Enter username")

        # Ensure password was submitted
        elif not request.form.get("password"):
            return render_template("error.html", message="Enter password")

        # Query database for username
        user = User.query.filter_by(username=request.form.get("username")).first()
        
        # Ensure username exists and password is correct
        if not user or not user.check_password(request.form.get("password")):
            return render_template("error.html", message="Invalid username and/or password")

        # Remember which user has logged in
        session["user_id"] = user.id
        
        flash(f"Welcome back, {user.username}!")
        
        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")
    
@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


if __name__ == '__main__':
    app.run()


