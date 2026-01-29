import uuid
import hashlib
import platform
import os

SECRET_SALT = "sk-antigravity-secret-salt-2026"

def get_machine_code():
    """
    Generates a unique machine code based on the MAC address.
    """
    node = uuid.getnode()
    return hashlib.md5(f"{node}{platform.node()}".encode()).hexdigest().upper()[:24]

def generate_license_key(machine_code):
    """
    Generates a license key from the machine code using a secret salt.
    """
    raw = f"{machine_code}-{SECRET_SALT}"
    hash_obj = hashlib.sha256(raw.encode())
    digest = hash_obj.hexdigest().upper()
    # Format as XXXX-XXXX-XXXX-XXXX
    return f"{digest[:4]}-{digest[4:8]}-{digest[8:12]}-{digest[12:16]}"

def verify_license(machine_code, key):
    """
    Verifies if the provided key is valid for the given machine code.
    """
    expected = generate_license_key(machine_code)
    return key.strip().upper() == expected

def save_license(key):
    """Saves the license key to a file."""
    with open("license.key", "w") as f:
        f.write(key.strip())

def load_license():
    """Loads the license key from file."""
    if not os.path.exists("license.key"):
        return None
    with open("license.key", "r") as f:
        return f.read().strip()

def check_license_status():
    """
    Checks if a valid license exists.
    Returns (is_valid, machine_code)
    """
    code = get_machine_code()
    key = load_license()
    if not key:
        return False, code
    return verify_license(code, key), code
