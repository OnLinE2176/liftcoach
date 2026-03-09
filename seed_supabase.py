import os
import random
import time
from dotenv import load_dotenv  # type: ignore

import database as db  # type: ignore

# Load .env explicitly to ensure DATABASE_URL is read
load_dotenv()

def generate_fake_data():
    if not db.DATABASE_URL:
        print("❌ DATABASE_URL is missing from your .env file!")
        print("Please configure it first as shown in the steps before running this script.")
        return

    print("🚀 Connecting to Supabase and initializing tables...")
    # This automatically invokes the dialect-agnostic creation logic (PostgreSQL!)
    db.init_db()
    
    conn = db.get_connection()

    print("👥 Seeding 10 dummy users...")
    users = [
        ("john_doe", "john@email.com", "John Doe"),
        ("sarah_smith", "sarah@email.com", "Sarah Smith"),
        ("mike_johnson", "mike@email.com", "Mike Johnson"),
        ("deadlift_king", "dk@email.com", "David King"),
        ("squat_queen", "sq@email.com", "Samantha Quail"),
        ("bench_bro", "bro@email.com", "Bradley Bro"),
        ("iron_addict", "iron@email.com", "Ian Addict"),
        ("powerlifter99", "pl99@email.com", "Paul Lifter"),
        ("fitness_freak", "freak@email.com", "Fiona Freak"),
        ("gym_rat", "rat@email.com", "Gary Rat"),
    ]

    user_ids = []
    
    # Try inserting user, or get the existing ID if it fails (because user already exists)
    for u, e, n in users:
        res = db.register_user(u, e, "password123", n)
        if res["success"]:
            # Hacky way to grab the newly inserted user ID
            db_user = conn.execute("SELECT id FROM users WHERE username = %s" if conn.is_postgres else "SELECT id FROM users WHERE username = ?", (u,)).fetchone()
            if db_user:
                user_ids.append(db_user[0])
        else:
            db_user = conn.execute("SELECT id FROM users WHERE username = %s" if conn.is_postgres else "SELECT id FROM users WHERE username = ?", (u,)).fetchone()
            if db_user:
                user_ids.append(db_user[0])
                
    print("🏋️‍♂️ Generating 20 realistic analysis sessions for the screenshot...")
    lifts = ["Squat", "Bench Press", "Deadlift"]
    verdicts = ["Good Lift", "Bad Lift"]
    
    for i in range(20):
        # Pick random user, lift, and verdict
        uid = random.choice(user_ids)
        lift = random.choice(lifts)
        verdict = random.choice(verdicts)
        
        # Make realistic faults (empty if good, 1-2 if bad)
        faults_found = []
        if verdict == "Bad Lift":
            all_faults = ["Knees caving in", "Hips rising too fast", "Back rounding", "Not enough depth", "Uneven bar path"]
            faults_found = random.sample(all_faults, random.randint(1, 2))
            
        # Create a fake analysis result dictionary
        analysis_result = {
            "verdict": verdict,
            "faults_found": faults_found,
            "kinematic_data": {"bar_speed": float(f"{random.uniform(0.3, 0.9):.2f}"), "depth": float(f"{random.uniform(80, 110):.2f}")},
            "phases": {"setup": "good", "eccentric": "fast", "concentric": "slow", "lockout": "good"}
        }
        
        # Save session to DB
        fake_filename = f"user_{uid}_{lift.lower().replace(' ', '_')}_{int(time.time()) - random.randint(1000, 100000)}.mp4"
        session_id = db.save_session(uid, lift, analysis_result, fake_filename)
        
        # Save some to gallery
        if random.random() > 0.5:
            db.save_to_gallery(session_id, uid, f"My {lift} PR attempt", f"Felt heavy today. Result: {verdict}")

    print("✅ Dummy data successfully loaded into Supabase!")
    print("👉 Go to your Supabase Table Editor now and take your screenshot!")

if __name__ == "__main__":
    generate_fake_data()
