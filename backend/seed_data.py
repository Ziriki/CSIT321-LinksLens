# backend/seed_massive.py
import random
import string
import secrets
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from passlib.context import CryptContext
from faker import Faker

import models
from database import SessionLocal, engine

# Initialize Faker
fake = Faker()

# Rebuild all tables
models.Base.metadata.create_all(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_secure_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) 
            and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*" for c in pwd)):
            return pwd

def seed_massive_database():
    db: Session = SessionLocal()
    
    try:
        print("Wiping existing data (Truncating tables)...")
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        for table in reversed(models.Base.metadata.sorted_tables):
            db.execute(text(f"TRUNCATE TABLE {table.name};"))
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        print("Tables wiped. Generating massive dataset. This may take 10-20 seconds...\n")

        # --- 1. User Roles ---
        roles = [
            models.UserRole(RoleName="Administrator"),
            models.UserRole(RoleName="Moderator"),
            models.UserRole(RoleName="User")
        ]
        db.add_all(roles)
        db.commit()
        
        admin_role_id, mod_role_id, user_role_id = [r.RoleID for r in roles]

        # --- 2. User Accounts (100 total) ---
        print("⏳ Generating and hashing 100 unique passwords. This will take ~20 seconds...")
        users = []
        dummy_credentials_list = []
        
        # 5 Master Accounts
        master_accounts = [
            models.UserAccount(EmailAddress="admin@linkslens.com", PasswordHash=pwd_context.hash("o4LU6t$pGKGhEXZP"), RoleID=admin_role_id),
            models.UserAccount(EmailAddress="mod1@linkslens.com", PasswordHash=pwd_context.hash("X4tFpfErsT*ETWdI"), RoleID=mod_role_id),
            models.UserAccount(EmailAddress="mod2@linkslens.com", PasswordHash=pwd_context.hash("msqb2&RsN5%18pn1"), RoleID=mod_role_id),
            models.UserAccount(EmailAddress="user1@gmail.com", PasswordHash=pwd_context.hash("##3NQwuNGFL3EepW"), RoleID=user_role_id),
            models.UserAccount(EmailAddress="user2@gmail.com", PasswordHash=pwd_context.hash("bL86S70^5WW&yJNj"), RoleID=user_role_id),
        ]
        users.extend(master_accounts)

        # 95 Random Dummy Users
        for _ in range(95):
            fake_email = fake.unique.email()
            fake_password = generate_secure_password()
            
            dummy_credentials_list.append({"email": fake_email, "password": fake_password})
            
            users.append(models.UserAccount(
                EmailAddress=fake_email,
                PasswordHash=pwd_context.hash(fake_password),
                RoleID=user_role_id,
                CreatedAt=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=timezone.utc)
            ))
            
        db.add_all(users)
        db.commit()
        
        # --- THE MISSING LINES ARE BACK! ---
        all_user_ids = [u.UserID for u in users]
        admin_ids = [u.UserID for u in users if u.RoleID == admin_role_id]
        mod_ids = [u.UserID for u in users if u.RoleID == mod_role_id]
        standard_user_ids = [u.UserID for u in users if u.RoleID == user_role_id]

        # --- 3. User Details & Preferences ---
        details, prefs = [], []
        for user in users:
            details.append(models.UserDetails(
                UserID=user.UserID,
                FullName=fake.name(),
                PhoneNumber=fake.numerify(text='###-###-####'),
                Address=fake.city(),
                Gender=random.choice(["Male", "Female", "Other"]),
                DateOfBirth=fake.date_of_birth(minimum_age=18, maximum_age=80)
            ))
            prefs.append(models.UserPreferences(
                UserID=user.UserID,
                Preferences={"Theme": random.choice(["Dark", "Light"]), "Notifications": random.choice([True, False])}
            ))
        db.add_all(details)
        db.add_all(prefs)
        db.commit()

        # --- 4. URL Rules (Master List) ---
        rules = []
        for _ in range(100):
            rules.append(models.URLRules(
                URLDomain=fake.unique.domain_name(),
                ListType=random.choice(["WHITELIST", "BLACKLIST"]),
                AddedBy=random.choice(admin_ids + mod_ids),
                CreatedAt=fake.date_time_between(start_date='-6m', end_date='now', tzinfo=timezone.utc)
            ))
        db.add_all(rules)
        db.commit()

        # --- 5. Scan History ---
        scans = []
        for _ in range(300):
            status = random.choice(["SAFE", "SUSPICIOUS", "MALICIOUS", "PENDING"])
            scans.append(models.ScanHistory(
                UserID=random.choice(standard_user_ids),
                InitialURL=fake.url(),
                StatusIndicator=status,
                DomainAgeDays=random.randint(1, 3000) if status != "PENDING" else None,
                ServerLocation=fake.country() if status != "PENDING" else None,
                ScannedAt=fake.date_time_between(start_date='-3m', end_date='now', tzinfo=timezone.utc)
            ))
        db.add_all(scans)
        db.commit()
        
        scan_ids = [s.ScanID for s in scans]

        # --- 6. Scan Feedback ---
        scan_feedbacks = []
        for _ in range(100):
            scan_feedbacks.append(models.ScanFeedback(
                ScanID=random.choice(scan_ids),
                UserID=random.choice(standard_user_ids),
                SuggestedStatus=random.choice(["SAFE", "SUSPICIOUS", "MALICIOUS"]),
                Comments=fake.sentence(),
                IsResolved=random.choice([True, False])
            ))
        db.add_all(scan_feedbacks)

        # --- 7. Blacklist Requests ---
        requests = []
        for _ in range(100):
            status = random.choice(["PENDING", "APPROVED", "REJECTED"])
            req = models.BlacklistRequest(
                UserID=random.choice(standard_user_ids),
                URLDomain=fake.domain_name(),
                Status=status,
                CreatedAt=fake.date_time_between(start_date='-2m', end_date='now', tzinfo=timezone.utc)
            )
            if status != "PENDING":
                req.ReviewedBy = random.choice(mod_ids)
                req.ReviewedAt = req.CreatedAt + timedelta(days=random.randint(1, 5))
            requests.append(req)
        db.add_all(requests)

        # --- 8. App Feedback ---
        app_feedbacks = []
        for _ in range(100):
            app_feedbacks.append(models.AppFeedback(
                UserID=random.choice(standard_user_ids),
                Feedback=fake.paragraph(),
                CreatedAt=fake.date_time_between(start_date='-6m', end_date='now', tzinfo=timezone.utc)
            ))
        db.add_all(app_feedbacks)

        # --- 9. Action History ---
        actions = []
        for _ in range(500):
            action_types = ["LOGIN", "SCAN_EXECUTED", "BLACKLIST_UPDATED", "WHITELIST_UPDATED", "FEEDBACK_RESOLVED"]
            actions.append(models.ActionHistory(
                UserID=random.choice(all_user_ids),
                ActionType=random.choice(action_types),
                Action=fake.sentence(),
                Timestamp=fake.date_time_between(start_date='-1y', end_date='now', tzinfo=timezone.utc)
            ))
        db.add_all(actions)
        db.commit()

        # --- Export Credentials to File ---
        file_path = "dummy_credentials.txt"
        with open(file_path, "w") as f:
            f.write("============================================================\n")
            f.write("LINKS LENS - MASS SEED CREDENTIALS\n")
            f.write("============================================================\n\n")
            
            f.write("MASTER ACCOUNTS:\n")
            f.write(f"Email: {'admin@linkslens.com':<25} | Password: o4LU6t$pGKGhEXZP\n")
            f.write(f"Email: {'mod1@linkslens.com':<25} | Password: X4tFpfErsT*ETWdI\n")
            f.write(f"Email: {'mod2@linkslens.com':<25} | Password: msqb2&RsN5%18pn1\n")
            f.write(f"Email: {'user1@gmail.com':<25} | Password: ##3NQwuNGFL3EepW\n")
            f.write(f"Email: {'user2@gmail.com':<25} | Password: bL86S70^5WW&yJNj\n\n")
            
            f.write("RANDOMLY GENERATED DUMMY ACCOUNTS:\n")
            f.write("------------------------------------------------------------\n")
            for cred in dummy_credentials_list: 
                f.write(f"Email: {cred['email']:<25} | Password: {cred['password']}\n")

        print("="*60)
        print("MASSIVE DB SEEDED SUCCESSFULLY! OVER 1,400 ROWS CREATED.")
        print(f"Credentials saved to: backend/{file_path}")
        print("="*60)

    except Exception as e:
        print(f"Error during mass seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_massive_database()