import sys
from license_utils import generate_license_key

def main():
    print("=== License Key Generator ===")
    print("Run this tool to generate a license key for a specific machine.")
    
    if len(sys.argv) > 1:
        machine_code = sys.argv[1]
    else:
        # Check if running in a pipe or non-interactive mode?
        # For simplicity, just use input()
        try:
            machine_code = input("Enter Machine Code: ").strip()
        except EOFError:
             print("Error: No input provided.")
             return
    
    if not machine_code:
        print("Error: Machine Code is required.")
        return
        
    key = generate_license_key(machine_code)
    print("\n" + "="*30)
    print(f"Machine Code: {machine_code}")
    print(f"License Key : {key}")
    print("="*30 + "\n")

if __name__ == "__main__":
    main()
