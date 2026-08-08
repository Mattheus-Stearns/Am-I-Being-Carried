#!/usr/bin/env python
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import app, db
from sqlalchemy import text

def vacuum_database():
    with app.app_context():
        print("Running VACUUM ANALYZE...")
        db.session.execute(text("VACUUM ANALYZE"))
        db.session.commit()
        print("VACUUM complete!")

if __name__ == "__main__":
    vacuum_database()