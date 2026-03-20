"""
Seed 10 user accounts into the LiftCoach database.
Run once: python seed_users.py
"""
import database as db

# Initialize DB tables first (in case they don't exist yet)
db.init_db()

users = [
    {
        "full_name": "Marcvain Gonzales Guce",
        "username": "marcvain.guce",
        "email": "marcvain.guce@gmail.com",
        "password": "liftcoach2026",
        "age": 22,
        "weight_kg": 77.0,
        "height_cm": 173.0,
        "gender": "Male",
        "experience_level": "Intermediate",
        "preferred_lift": "Clean & Jerk",
        "bio": "Competitive weightlifter focused on clean technique and explosive power.",
    },
    {
        "full_name": "Aliana Lao",
        "username": "aliana.lao",
        "email": "aliana.lao@gmail.com",
        "password": "liftcoach2026",
        "age": 21,
        "weight_kg": 55.0,
        "height_cm": 160.0,
        "gender": "Female",
        "experience_level": "Beginner",
        "preferred_lift": "Snatch",
        "bio": "Aspiring Olympic weightlifter training for university competitions.",
    },
    {
        "full_name": "Chine Evila",
        "username": "chine.evila",
        "email": "chine.evila@gmail.com",
        "password": "liftcoach2026",
        "age": 23,
        "weight_kg": 68.0,
        "height_cm": 165.0,
        "gender": "Female",
        "experience_level": "Intermediate",
        "preferred_lift": "Clean & Jerk",
        "bio": "Strength and conditioning enthusiast with a passion for Olympic lifts.",
    },
    {
        "full_name": "Hazel Javier",
        "username": "hazel.javier",
        "email": "hazel.javier@gmail.com",
        "password": "liftcoach2026",
        "age": 20,
        "weight_kg": 52.0,
        "height_cm": 157.0,
        "gender": "Female",
        "experience_level": "Beginner",
        "preferred_lift": "Snatch",
        "bio": "New to weightlifting, eager to learn proper form and technique.",
    },
    {
        "full_name": "Eko Ralar",
        "username": "eko.ralar",
        "email": "eko.ralar@gmail.com",
        "password": "liftcoach2026",
        "age": 24,
        "weight_kg": 85.0,
        "height_cm": 178.0,
        "gender": "Male",
        "experience_level": "Advanced",
        "preferred_lift": "Clean & Jerk",
        "bio": "Varsity athlete and certified weightlifting coach with 5 years of experience.",
    },
    {
        "full_name": "Zai Ampiloquio",
        "username": "zai.ampiloquio",
        "email": "zai.ampiloquio@gmail.com",
        "password": "liftcoach2026",
        "age": 22,
        "weight_kg": 73.0,
        "height_cm": 170.0,
        "gender": "Male",
        "experience_level": "Intermediate",
        "preferred_lift": "Snatch",
        "bio": "CrossFit athlete transitioning into competitive Olympic weightlifting.",
    },
    {
        "full_name": "Dane Cristobal-Yap",
        "username": "dane.cristobalyap",
        "email": "dane.cristobalyap@gmail.com",
        "password": "liftcoach2026",
        "age": 25,
        "weight_kg": 90.0,
        "height_cm": 180.0,
        "gender": "Male",
        "experience_level": "Advanced",
        "preferred_lift": "Clean & Jerk",
        "bio": "National-level competitor specializing in the clean and jerk.",
    },
    {
        "full_name": "Ortiz Tindaan Jr",
        "username": "ortiz.tindaan",
        "email": "ortiz.tindaan@gmail.com",
        "password": "liftcoach2026",
        "age": 23,
        "weight_kg": 81.0,
        "height_cm": 175.0,
        "gender": "Male",
        "experience_level": "Intermediate",
        "preferred_lift": "Snatch",
        "bio": "Sports science student researching biomechanics in Olympic weightlifting.",
    },
    {
        "full_name": "Aryan Cruz Magat",
        "username": "aryan.magat",
        "email": "aryan.magat@gmail.com",
        "password": "liftcoach2026",
        "age": 21,
        "weight_kg": 69.0,
        "height_cm": 168.0,
        "gender": "Male",
        "experience_level": "Beginner",
        "preferred_lift": "Snatch",
        "bio": "Fitness enthusiast looking to improve snatch mechanics through video analysis.",
    },
    {
        "full_name": "John Emmanuel Miso Avanzado",
        "username": "john.avanzado",
        "email": "john.avanzado@gmail.com",
        "password": "liftcoach2026",
        "age": 24,
        "weight_kg": 96.0,
        "height_cm": 182.0,
        "gender": "Male",
        "experience_level": "Advanced",
        "preferred_lift": "Clean & Jerk",
        "bio": "Team captain and powerhouse lifter training for regional qualifiers.",
    },
]

print("=" * 60)
print("  LiftCoach AI -- Seeding 10 User Accounts")
print("=" * 60)

for i, u in enumerate(users, 1):
    # Step 1: Register (creates account with hashed password)
    result = db.register_user(u["username"], u["email"], u["password"], u["full_name"])
    if result["success"]:
        # Step 2: Fetch the user to get their ID
        conn = db.get_connection()
        row = conn.execute("SELECT id FROM users WHERE username = ?", (u["username"],)).fetchone()
        conn.close()
        if row:
            uid = row["id"] if isinstance(row, dict) else row[0]
            # Step 3: Update their profile with athlete details
            db.update_profile(
                uid,
                age=u["age"],
                weight_kg=u["weight_kg"],
                height_cm=u["height_cm"],
                gender=u["gender"],
                experience_level=u["experience_level"],
                preferred_lift=u["preferred_lift"],
                bio=u["bio"],
            )
            print(f"  [{i:02d}/10] OK   {u['full_name']:40s} -> @{u['username']}")
        else:
            print(f"  [{i:02d}/10] WARN {u['full_name']:40s} -> registered but could not fetch ID")
    else:
        print(f"  [{i:02d}/10] SKIP {u['full_name']:40s} -> {result['message']}")

print("=" * 60)
print("  Done! All accounts use password: liftcoach2026")
print("=" * 60)
