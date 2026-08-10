# utils/helpers.py
from flask import request
import hashlib

def get_client_ip():
    """Get client IP address from request"""
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
        return ip
    elif request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    else:
        return request.remote_addr

def hash_string(string):
    """Hash a string for consistent keys"""
    return hashlib.sha256(string.encode()).hexdigest()[:16]