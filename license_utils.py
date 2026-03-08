import os
import sys
import base64
import json
import math
import hmac
import uuid
import platform
import hashlib
from datetime import datetime, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

# File paths
LICENSE_FILE = "license.key"
TRIAL_PERIOD_DAYS = 7
TRIAL_STORE_DIRNAME = "BidSystemPortable"
TRIAL_STATE_FILENAME = "trial.json"
TRIAL_REG_PATH = r"Software\BidSystemPortable"
TRIAL_REG_VALUE = "TrialState"
TRIAL_RECORD_VERSION = 1
TRIAL_SECRET = "bid-system-trial-v1-local-pepper"

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


def _now(now=None):
    return (now or datetime.now()).replace(microsecond=0)


def _serialize_dt(value):
    return value.replace(microsecond=0).isoformat()


def _parse_dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _get_trial_file_path():
    program_data = os.environ.get("PROGRAMDATA")
    if os.name == "nt":
        base_dir = program_data or os.environ.get("ALLUSERSPROFILE") or r"C:\ProgramData"
        return os.path.join(base_dir, TRIAL_STORE_DIRNAME, TRIAL_STATE_FILENAME)

    fallback_dir = os.path.join(os.path.expanduser("~"), ".bid_system")
    return os.path.join(fallback_dir, TRIAL_STATE_FILENAME)


def _trial_payload(record):
    return {
        "version": record.get("version", TRIAL_RECORD_VERSION),
        "machine_code": record.get("machine_code"),
        "first_run_at": record.get("first_run_at"),
        "expire_at": record.get("expire_at"),
    }


def _sign_trial_payload(machine_code, payload):
    secret = f"{TRIAL_SECRET}:{machine_code}".encode("utf-8")
    body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hmac.new(secret, body, hashlib.sha256).hexdigest()


def _build_trial_record(machine_code, now=None):
    started_at = _now(now)
    payload = {
        "version": TRIAL_RECORD_VERSION,
        "machine_code": machine_code,
        "first_run_at": _serialize_dt(started_at),
        "expire_at": _serialize_dt(started_at + timedelta(days=TRIAL_PERIOD_DAYS)),
    }
    payload["signature"] = _sign_trial_payload(machine_code, payload)
    return payload


def _trial_record_matches_machine(record, machine_code):
    return isinstance(record, dict) and record.get("machine_code") == machine_code


def _is_trial_record_valid(record, machine_code):
    if not _trial_record_matches_machine(record, machine_code):
        return False

    payload = _trial_payload(record)
    if payload.get("version") != TRIAL_RECORD_VERSION:
        return False

    first_run_at = _parse_dt(payload.get("first_run_at"))
    expire_at = _parse_dt(payload.get("expire_at"))
    if not first_run_at or not expire_at or expire_at <= first_run_at:
        return False

    signature = record.get("signature")
    if not signature:
        return False

    expected_signature = _sign_trial_payload(machine_code, payload)
    return hmac.compare_digest(signature, expected_signature)


def _load_trial_from_file(path=None):
    trial_path = path or _get_trial_file_path()
    if not os.path.exists(trial_path):
        return None

    try:
        with open(trial_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _save_trial_to_file(record, path=None):
    trial_path = path or _get_trial_file_path()
    try:
        os.makedirs(os.path.dirname(trial_path), exist_ok=True)
        with open(trial_path, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return True
    except OSError:
        return False


def _load_trial_from_registry():
    if os.name != "nt":
        return None

    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, TRIAL_REG_PATH) as key:
            value, _ = winreg.QueryValueEx(key, TRIAL_REG_VALUE)
        return json.loads(value)
    except (ImportError, FileNotFoundError, OSError, json.JSONDecodeError):
        return None


def _save_trial_to_registry(record):
    if os.name != "nt":
        return False

    try:
        import winreg

        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, TRIAL_REG_PATH) as key:
            winreg.SetValueEx(key, TRIAL_REG_VALUE, 0, winreg.REG_SZ, payload)
        return True
    except (ImportError, OSError):
        return False


def _same_trial_record(left, right):
    if left is None or right is None:
        return left is right
    return _trial_payload(left) == _trial_payload(right) and left.get("signature") == right.get("signature")


def _calculate_days_left(expire_at, now=None):
    remaining_seconds = (expire_at - _now(now)).total_seconds()
    if remaining_seconds <= 0:
        return 0
    return max(1, math.ceil(remaining_seconds / 86400))


def get_trial_status(machine_code=None, now=None):
    current_machine_code = machine_code or get_machine_code()
    current_time = _now(now)

    file_record = _load_trial_from_file()
    registry_record = _load_trial_from_registry()

    valid_records = []
    tampered = False
    saw_current_machine_record = False

    for record in (file_record, registry_record):
        if record is None:
            continue
        if _trial_record_matches_machine(record, current_machine_code):
            saw_current_machine_record = True
            if _is_trial_record_valid(record, current_machine_code):
                valid_records.append(record)
            else:
                tampered = True

    if valid_records:
        canonical_record = min(valid_records, key=lambda item: item["first_run_at"])
    elif tampered and saw_current_machine_record:
        return {
            "trial_active": False,
            "trial_started_at": None,
            "trial_expire_at": None,
            "trial_days_left": 0,
            "trial_tampered": True,
        }
    else:
        canonical_record = _build_trial_record(current_machine_code, current_time)

    if not _same_trial_record(file_record, canonical_record):
        _save_trial_to_file(canonical_record)
    if not _same_trial_record(registry_record, canonical_record):
        _save_trial_to_registry(canonical_record)

    expire_at = _parse_dt(canonical_record["expire_at"])
    trial_active = bool(expire_at and current_time < expire_at)

    return {
        "trial_active": trial_active,
        "trial_started_at": canonical_record["first_run_at"],
        "trial_expire_at": canonical_record["expire_at"],
        "trial_days_left": _calculate_days_left(expire_at, current_time) if expire_at else 0,
        "trial_tampered": False,
    }

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


def _has_valid_license(machine_code):
    if not os.path.exists(LICENSE_FILE):
        return False

    try:
        with open(LICENSE_FILE, "r") as f:
            key = f.read().strip()

        license_info = get_license_info(key)
        if license_info and license_info.get("code") != machine_code:
            return False

        return verify_license(machine_code, key)
    except Exception:
        return False


def get_access_status(now=None):
    code = get_machine_code()
    if _has_valid_license(code):
        info = get_license_info() or {}
        return {
            "machine_code": code,
            "licensed": True,
            "license_expire": info.get("expire", "Unknown"),
            "trial_active": False,
            "trial_started_at": None,
            "trial_expire_at": None,
            "trial_days_left": 0,
            "trial_tampered": False,
            "locked": False,
            "mode": "licensed",
        }

    trial_status = get_trial_status(machine_code=code, now=now)
    locked = not trial_status["trial_active"]

    return {
        "machine_code": code,
        "licensed": False,
        "license_expire": None,
        **trial_status,
        "locked": locked,
        "mode": "locked" if locked else "trial",
    }

def check_license_status():
    """
    Checks if a valid license exists.
    Returns (is_valid, machine_code)
    """
    status = get_access_status()
    return not status["locked"], status["machine_code"]
