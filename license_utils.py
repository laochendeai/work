import os
import sys
import base64
import json
import uuid
import platform
import hashlib
from datetime import datetime
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# File paths
LICENSE_FILE = "license.key"

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# Keys might be embedded or external. logic:
# 1. Try external (cwd) first (allow override).
# 2. Try embedded (_MEIPASS).
def get_key_path(filename):
    # Check current directory first
    if os.path.exists(filename):
        return filename

    # In frozen mode (PyInstaller), check next to executable
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(os.path.abspath(sys.executable))
        exe_path = os.path.join(exe_dir, filename)
        if os.path.exists(exe_path):
            return exe_path

        # Also check _MEIPASS (for one-file mode or extracted data)
        if hasattr(sys, '_MEIPASS'):
            embedded = os.path.join(sys._MEIPASS, filename)
            if os.path.exists(embedded):
                return embedded

    return filename

PRIVATE_KEY_PATH = "private.pem" # Usually external for generator
PUBLIC_KEY_PATH = get_key_path("public.pem") # Embedded for server

def get_machine_code():
    """
    Generates a unique machine code based on the MAC address and Hostname.
    """
    node = uuid.getnode()
    raw = f"{node}{platform.node()}"
    return hashlib.md5(raw.encode()).hexdigest().upper()[:24]

def generate_key_pair():
    """
    Generates Ed25519 private/public key pair and saves to disk.
    WARN: Overwrites existing keys!
    """
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()

    # Save Private Key
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    # Save Public Key
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))

    return private_key, public_key

def load_private_key():
    if not os.path.exists(PRIVATE_KEY_PATH):
        raise FileNotFoundError(f"Private Key not found at {PRIVATE_KEY_PATH}. Run keygen setup first.")
    
    with open(PRIVATE_KEY_PATH, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def load_public_key():
    if not os.path.exists(PUBLIC_KEY_PATH):
        return None
        
    with open(PUBLIC_KEY_PATH, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def sign_license(machine_code, days=None):
    """
    Signs the machine code + expiration using the private key.
    
    Args:
        machine_code (str): The machine ID.
        days (int, optional): Validity in days. None = Lifetime.
        
    Returns: 
        str: "KEY-<PayloadB64>.<SignatureB64>"
    """
    private_key = load_private_key()
    
    # Construct Payload
    payload = {
        "code": machine_code,
        "ts": int(datetime.now().timestamp()), # Creation time
    }
    
    if days:
        try:
            # Calculate expiry date
            from datetime import timedelta
            expire_dt = datetime.now() + timedelta(days=days)
            payload["expire"] = expire_dt.strftime("%Y-%m-%d")
        except:
            pass
    else:
        payload["expire"] = "LIFETIME"
        
    # Serialize Payload
    payload_str = json.dumps(payload, separators=(',', ':')) # Compact JSON
    payload_b64 = base64.urlsafe_b64encode(payload_str.encode()).decode().rstrip("=")
    
    # Sign the payload (base64 string)
    signature = private_key.sign(payload_b64.encode())
    sig_b64 = base64.urlsafe_b64encode(signature).decode().rstrip("=")
    
    return f"KEY-{payload_b64}.{sig_b64}"

def verify_license(machine_code, license_key):
    """
    Verifies:
    1. Signature matches Payload
    2. Machine Code matches
    3. Not Expired
    """
    public_key = load_public_key()
    if not public_key:
        print("[License] Verification failed: Public key missing.")
        return False

    try:
        if not license_key.startswith("KEY-"):
            return False
            
        parts = license_key[4:].split('.')
        if len(parts) != 2:
            return False
            
        payload_b64, sig_b64 = parts
        
        # 1. Verify Signature
        # Restore padding for decoding
        sig_missing = len(sig_b64) % 4
        if sig_missing: sig_b64 += "=" * (4 - sig_missing)
        
        signature = base64.urlsafe_b64decode(sig_b64)
        
        # Verify that the signature signs the payload_b64 string
        public_key.verify(signature, payload_b64.encode())
        
        # 2. Decode Payload
        pay_missing = len(payload_b64) % 4
        if pay_missing: payload_b64 += "=" * (4 - pay_missing)
        
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        data = json.loads(payload_json)
        
        # 3. Check Machine Code
        if data.get("code") != machine_code:
            print(f"[License] Code mismatch: {data.get('code')} != {machine_code}")
            return False
            
        # 4. Check Expiration
        expire = data.get("expire")
        if expire and expire != "LIFETIME":
            expire_date = datetime.strptime(expire, "%Y-%m-%d")
            # Compare with today (start of day)
            if datetime.now() > expire_date.replace(hour=23, minute=59, second=59):
                 print(f"[License] Expired on {expire}")
                 return False
                 
        return True
    except Exception as e:
        print(f"[License] Check Failed: {e}")
        return False

def get_license_info(license_key=None):
    """
    Decodes license info without verification (UI checks verification separately).
    Returns dict or None.
    """
    if not license_key:
        if not os.path.exists(LICENSE_FILE):
            return None
        try:
            with open(LICENSE_FILE, "r") as f:
                license_key = f.read().strip()
        except:
            return None

    try:
        if not license_key.startswith("KEY-"): return None
        parts = license_key[4:].split('.')
        if len(parts) != 2: return None
        
        payload_b64 = parts[0]
        pay_missing = len(payload_b64) % 4
        if pay_missing: payload_b64 += "=" * (4 - pay_missing)
        
        payload_json = base64.urlsafe_b64decode(payload_b64).decode()
        return json.loads(payload_json)
    except:
        return None

def save_license(key):
    with open(LICENSE_FILE, "w") as f:
        f.write(key.strip())

def check_license_status():
    """
    Checks if a valid license exists.
    Returns (is_valid, machine_code)
    """
    code = get_machine_code()
    if not os.path.exists(LICENSE_FILE):
        return False, code
        
    try:
        with open(LICENSE_FILE, "r") as f:
            key = f.read().strip()
            
        if verify_license(code, key):
            return True, code
    except Exception:
        pass
        
    return False, code
