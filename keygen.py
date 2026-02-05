import sys
import json
import os
import argparse
from datetime import datetime
from license_utils import sign_license, generate_key_pair, PRIVATE_KEY_PATH

DB_FILE = "license_db.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}

def save_db(db):
    with open(DB_FILE, "w", encoding='utf-8') as f:
        json.dump(db, f, indent=4, ensure_ascii=False)

def setup():
    print(f"Generating new key pair... (Warning: This invalidates old licenses!)")
    if os.path.exists(PRIVATE_KEY_PATH):
        confirm = input(f"Private key already exists. Overwrite? (y/N): ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

    priv, pub = generate_key_pair()
    print(f"Keys generated: private.pem, public.pem")
    print("Please keep private.pem SAFE and distribute public.pem with the server.")

def generate(machine_code, days=None, note=""):
    if not os.path.exists(PRIVATE_KEY_PATH):
        print("Error: private.pem not found. Run 'python keygen.py --setup' first.")
        return

    db = load_db()
    
    # Check for duplicate (reuse existing valid key if same logic? Or allow new key?)
    # Let's allow generating a new key even if one exists (e.g., extension)
    # But checking if machine code exists helps warn.
    if machine_code in db:
        record = db[machine_code]
        print(f"\n[!] Warning: Machine Code has history.")
        print(f"Last Key Created: {record.get('created_at', 'Unknown')}")
        # We proceed to generate a new one anyway
    
    # Generate new
    try:
        key = sign_license(machine_code, days)
    except Exception as e:
        print(f"Error signing license: {e}")
        return

    # Calculate expiration date for DB record
    expire_str = "LIFETIME"
    if days:
        from datetime import timedelta
        expire_dt = datetime.now() + timedelta(days=days)
        expire_str = expire_dt.strftime("%Y-%m-%d")

    # Save
    record = {
        "key": key,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "expire": expire_str,
        "note": note,
        "days": str(days) if days else "Lifetime"
    }
    
    # Store in DB - we might want to store list of keys per machine, but simple key-value is easier for now.
    # Let's just overwrite for now or maybe append?
    # Requirement: "generated key query display function"
    # Overwriting means we lose history. Let's make DB structure slightly better.
    # If db[code] is a list, append. If dict, convert to list?
    # To keep it simple for now, we'll just store the LATEST key as primary, 
    # but maybe we can rename the key to "history" if we want full history.
    # Let's stick to simple: Key by Code.
    db[machine_code] = record
    save_db(db)

    print("\n" + "="*30)
    print(f"Machine Code: {machine_code}")
    print(f"Duration    : {record['days']}")
    print(f"Expires     : {record['expire']}")
    print(f"License Key : {key}")
    print("="*30 + "\n")
    print(f"Record saved to {DB_FILE}")

def query_keys(filter_text=None):
    db = load_db()
    if not db:
        print("No licenses found.")
        return

    print(f"\n{'Machine Code':<26} | {'Created':<20} | {'Expires':<12} | {'Note'}")
    print("-" * 80)
    
    for code, record in db.items():
        if filter_text and filter_text not in code and filter_text not in str(record):
            continue
            
        expire = record.get('expire', 'Unknown')
        created = record.get('created_at', '')
        note = record.get('note', '')
        
        # Check if expired
        status = ""
        is_expired = False
        if expire != "LIFETIME":
            try:
                exp_dt = datetime.strptime(expire, "%Y-%m-%d")
                if datetime.now() > exp_dt.replace(hour=23, minute=59, second=59):
                    status = "[EXPIRED] "
                    is_expired = True
            except:
                pass
        
        # Color/Mark
        row = f"{status}{code:<26} | {created:<20} | {expire:<12} | {note}"
        print(row)
    print("-" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="License Key Generator")
    parser.add_argument("code", nargs="?", help="Machine Code from the client")
    parser.add_argument("--setup", action="store_true", help="Generate Admin Key Pair (Run once)")
    
    # Duration options
    parser.add_argument("--days", type=int, help="Number of days valid (e.g. 7, 30, 365)")
    parser.add_argument("--lifetime", action="store_true", help="Lifetime license (default if no days specified)")
    
    # Management
    parser.add_argument("--query", "-q", action="store_true", help="List all generated keys")
    parser.add_argument("--filter", "-f", help="Filter query results")
    parser.add_argument("--note", help="Add a note to the license (e.g. Client Name)")

    args = parser.parse_args()

    if args.setup:
        setup()
        return

    if args.query:
        query_keys(args.filter)
        return

    if args.code:
        generate(args.code, args.days, args.note)
    else:
        # Interactive mode
        print("=== License Key Generator ===")
        print("1. Generate License")
        print("2. Query/List Licenses")
        choice = input("Select (1/2): ").strip()
        
        if choice == '2':
            query_keys()
        else:
            code = input("Enter Machine Code: ").strip()
            if not code:
                return
                
            print("\nSelect Duration:")
            print("1. 7 Days")
            print("2. 1 Month (30 Days)")
            print("3. 1 Year (365 Days)")
            print("4. Lifetime (Default)")
            print("5. Custom Days")
            
            dur_choice = input("Choice (1-5): ").strip()
            days = None
            if dur_choice == '1': days = 7
            elif dur_choice == '2': days = 30
            elif dur_choice == '3': days = 365
            elif dur_choice == '5':
                try:
                    days = int(input("Enter days: ").strip())
                except:
                    print("Invalid number")
                    return
            
            note = input("Note (Optional): ").strip()
            generate(code, days, note)

if __name__ == "__main__":
    main()
