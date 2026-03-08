# backend/seed_data.py
import datetime
import secrets
import string
from sqlalchemy.orm import Session
from sqlalchemy import text # Import text for raw SQL commands
from passlib.context import CryptContext

import models
from database import SessionLocal, engine

# Create tables if they don't exist yet
models.Base.metadata.create_all(bind=engine)

# Setup password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_secure_password(length=16):
    """Generates a cryptographically secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in pwd) and any(c.isupper() for c in pwd) 
            and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*" for c in pwd)):
            return pwd

def seed_database():
    db: Session = SessionLocal()
    
    try:
        print("Wiping existing data (Truncating tables)...")
        # 1. Disable Foreign Key checks so MySQL doesn't block the wipe
        db.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
        
        # 2. Dynamically grab every table and truncate it
        for table in reversed(models.Base.metadata.sorted_tables):
            db.execute(text(f"TRUNCATE TABLE {table.name};"))
            
        # 3. Turn Foreign Key checks back on!
        db.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
        db.commit()
        print("All tables truncated successfully!")

        print("Seeding database with TRULY RANDOM dummy data...")

        # --- 1. User Roles ---
        role_admin = models.UserRole(RoleName="Administrator")
        role_mod = models.UserRole(RoleName="Moderator")
        role_user = models.UserRole(RoleName="User")
        db.add_all([role_admin, role_mod, role_user])
        db.commit()

        # --- Generate the random passwords ---
        passwords = {
            "admin@linkslens.com": generate_secure_password(),
            "mod1@linkslens.com": generate_secure_password(),
            "mod2@linkslens.com": generate_secure_password(),
            "user1@gmail.com": generate_secure_password(),
            "user2@gmail.com": generate_secure_password()
        }

        # --- 2. User Accounts ---
        users = [
            models.UserAccount(EmailAddress="admin@linkslens.com", PasswordHash=pwd_context.hash(passwords["admin@linkslens.com"]), RoleID=role_admin.RoleID, IsActive=True),
            models.UserAccount(EmailAddress="mod1@linkslens.com", PasswordHash=pwd_context.hash(passwords["mod1@linkslens.com"]), RoleID=role_mod.RoleID, IsActive=True),
            models.UserAccount(EmailAddress="mod2@linkslens.com", PasswordHash=pwd_context.hash(passwords["mod2@linkslens.com"]), RoleID=role_mod.RoleID, IsActive=True),
            models.UserAccount(EmailAddress="user1@gmail.com", PasswordHash=pwd_context.hash(passwords["user1@gmail.com"]), RoleID=role_user.RoleID, IsActive=True),
            models.UserAccount(EmailAddress="user2@gmail.com", PasswordHash=pwd_context.hash(passwords["user2@gmail.com"]), RoleID=role_user.RoleID, IsActive=True)
        ]
        db.add_all(users)
        db.commit()

        admin_id, mod1_id, mod2_id, user1_id, user2_id = [u.UserID for u in users]

        # --- 3. User Details ---
        details = [
            models.UserDetails(UserID=admin_id, FullName="System Admin", Gender="Other"),
            models.UserDetails(UserID=mod1_id, FullName="Alice Mod", Gender="Female"),
            models.UserDetails(UserID=user1_id, FullName="Bob User", Gender="Male")
        ]
        db.add_all(details)

        # --- 4. User Preferences ---
        default_prefs = {"Theme": "Dark", "VibrationEnabled": True, "ReportLanguage": "en"}
        prefs = [
            models.UserPreferences(UserID=admin_id, Preferences=default_prefs),
            models.UserPreferences(UserID=user1_id, Preferences={"Theme": "Light", "VibrationEnabled": False, "ReportLanguage": "en"})
        ]
        db.add_all(prefs)
        db.commit()

        # --- 5. URL Rules (Master List) ---
        # Using raw uppercase strings to satisfy MySQL's strict Enum constraints
        rules = [
            models.URLRules(URLDomain="google.com", ListType="WHITELIST", AddedBy=admin_id),
            models.URLRules(URLDomain="secure-bank-login-update.com", ListType="BLACKLIST", AddedBy=mod1_id),
            models.URLRules(URLDomain="free-iphones-now.net", ListType="BLACKLIST", AddedBy=mod2_id)
        ]
        db.add_all(rules)
        db.commit()

        # --- 6. Scan History ---
        scans = [
            models.ScanHistory(UserID=user1_id, InitialURL="https://google.com", StatusIndicator="SAFE", DomainAgeDays=8500, ServerLocation="USA"),
            models.ScanHistory(UserID=user1_id, InitialURL="https://secure-bank-login-update.com", StatusIndicator="MALICIOUS", DomainAgeDays=2, ServerLocation="Russia"),
            models.ScanHistory(UserID=user2_id, InitialURL="https://unknown-shop-online.com", StatusIndicator="SUSPICIOUS", DomainAgeDays=14, ServerLocation="Unknown")
        ]
        db.add_all(scans)
        db.commit()

        # --- 7. Scan Feedback ---
        scan_feedback = models.ScanFeedback(ScanID=scans[2].ScanID, UserID=user2_id, SuggestedStatus="MALICIOUS", Comments="They asked for my credit card without HTTPS!", IsResolved=False)
        db.add(scan_feedback)

        # --- 8. Blacklist Requests ---
        requests = [
            models.BlacklistRequest(UserID=user1_id, URLDomain="scam-crypto-wallet.io", Status="PENDING"),
            models.BlacklistRequest(UserID=user2_id, URLDomain="fake-shopee-deals.sg", Status="APPROVED", ReviewedBy=mod1_id, ReviewedAt=datetime.datetime.now(datetime.timezone.utc))
        ]
        db.add_all(requests)
        db.commit()

        # --- 9. App Feedback ---
        app_feedback = models.AppFeedback(UserID=user1_id, Feedback="Love the UI, but I wish the scans were 1 second faster!")
        db.add(app_feedback)

        # --- 10. Action History (Audit Log) ---
        actions = [
            models.ActionHistory(UserID=admin_id, ActionType="ADDED_WHITELIST", Action="Added google.com to master whitelist."),
            models.ActionHistory(UserID=mod1_id, ActionType="APPROVED_BLACKLIST", Action="Approved User2 request to blacklist fake-shopee-deals.sg.")
        ]
        db.add_all(actions)
        db.commit()

        print("\n" + "="*60)
        print("DB WIPED & SEEDED! SAVE THESE CREDENTIALS NOW:")
        print("="*60)
        for email, pwd in passwords.items():
            print(f"Email: {email:<20} | Password: {pwd}")
        print("="*60 + "\n")

    except Exception as e:
        print(f"Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()