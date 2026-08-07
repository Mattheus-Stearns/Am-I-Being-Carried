# Importing key Libraries

import os
import uuid
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv
import json
import requests

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

@app.route('/results')
def results():
    # Get data from session or database
    data = session.get('api_data', [])
    return render_template('results.html', data=data)

@app.route('/api/query', methods=['POST'])
def query_api():
    try:
        # Get request data
        req_data = request.get_json()
        
        # Your API query logic here
        endpoint = req_data.get('endpoint', '/api/data')
        api_key = req_data.get('api_key', '')
        params = json.loads(req_data.get('params', '{}'))
        
        # Make API call
        headers = {}
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        response = requests.get(
            f'https://api.example.com{endpoint}',
            params=params,
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Store data in session
            session['api_data'] = data
            session['data_fetched'] = True
            return jsonify({'success': True, 'data': data})
        else:
            return jsonify({'success': False, 'message': f'API Error: {response.status_code}'})
            
    except requests.exceptions.Timeout:
        return jsonify({'success': False, 'message': 'API request timed out'})
    except requests.exceptions.ConnectionError:
        return jsonify({'success': False, 'message': 'Could not connect to API'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})
