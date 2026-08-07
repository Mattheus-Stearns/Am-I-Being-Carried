# Importing key Libraries

import os
import uuid
from flask import Flask, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

load_dotenv()

# Configure application
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.secret_key = os.getenv("SECRET_KEY")

# Initialize and connect your server-side session database
session_db = SQLAlchemy()
app.config["SESSION_TYPE"] = "sqlalchemy"
app.config["SESSION_SQLALCHEMY"] = session_db
app.config["SESSION_SQLALCHEMY_TABLE"] = "sessions"  # Automatically creates this table in Postgres

session_db.init_app(app)
Session(app)

# Build the session table automatically on startup
with app.app_context():
    session_db.create_all()

# This is the Homepage
@app.route("/")
def index():
    if "guest_id" not in session:
        session["guest_id"] = str(uuid.uuid4())
        
    return render_template("index.html")
