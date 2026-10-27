#!/usr/bin/env python3
"""
ActionPilot Database Seeding Utility
Populates sample scenarios for demo accounts including:
- satyamchaubey471@gmail.com
- satayamchaubey471@gmail.com
- judge@hackathon.com
"""
import sys, os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

if "--sqlite" in sys.argv:
    os.environ["DATABASE_URL"] = ""
    os.environ["POSTGRES_URL"] = ""

from app import db
from app.seed import seed_all_demo_users

def main():
    print(f"Connecting to database (is_postgres={db.is_postgres()})...")
    db.init_db()
    with db.connect() as c:
        seed_all_demo_users(c)
    print("✅ Successfully seeded sample scenarios for satyamchaubey471@gmail.com, satayamchaubey471@gmail.com, and judge@hackathon.com!")

if __name__ == "__main__":
    main()
