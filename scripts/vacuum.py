#!/usr/bin/env python
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from extensions import db
from app import app
from sqlalchemy import text

def vacuum_database():
    with app.app_context():
        print("Running VACUUM ANALYZE...")
        
        # Use the engine directly with autocommit
        with db.engine.connect() as conn:
            # Enable autocommit mode for VACUUM
            conn.execution_options(isolation_level="AUTOCOMMIT")
            conn.execute(text("VACUUM ANALYZE"))
            
        print("VACUUM complete!")

if __name__ == "__main__":
    vacuum_database()