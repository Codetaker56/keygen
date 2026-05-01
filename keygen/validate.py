"""
Client-side key validation script.

No secrets are stored here. All validation is performed server-side.
Set the API URL via the API_BASE_URL environment variable (optional).
"""

import os
import sys
import requests

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:5000")
VALIDATE_URL = f"{API_BASE_URL}/validate"


def validate_key(key: str) -> bool:
    """
    Send the key to the Flask API for validation.
    Returns True if the key is valid, False otherwise.
    """
    try:
        response = requests.post(
            VALIDATE_URL,
            json={"key": key},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("valid", False)
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the validation API.")
        print(f"       Make sure the API is running at: {API_BASE_URL}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("ERROR: Request to validation API timed out.")
        sys.exit(1)
    except requests.exceptions.HTTPError as e:
        print(f"ERROR: API returned an error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error during validation: {e}")
        sys.exit(1)


def main():
    print("=== Access Key Validation ===")
    key = input("Enter your access key: ").strip()

    if not key:
        print("No key entered. Access denied.")
        sys.exit(1)

    print("Validating key...")
    is_valid = validate_key(key)

    if is_valid:
        print("✅ Key is valid. Access granted.")
        # --- Your protected application logic starts here ---
        run_application()
    else:
        print("❌ Invalid key. Access denied.")
        sys.exit(1)


def run_application():
    """Placeholder for your protected application logic."""
    print("\n--- Application Started ---")
    print("Welcome! You now have access to the application.")
    # Replace this with your actual application code


if __name__ == "__main__":
    main()
