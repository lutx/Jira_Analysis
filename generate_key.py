import os
import binascii

def generate_key():
    """Generate a secure 32-byte encryption key."""
    key = binascii.hexlify(os.urandom(32)).decode()
    print("\nGenerated encryption key:")
    print(key)
    print("\nPlease save this key securely. You will need it to decrypt any encrypted data.")
    print("\nTo use this key, set it as an environment variable:")
    print("PowerShell:")
    print(f'$env:ENCRYPTION_KEY = "{key}"')
    print("\nCmd:")
    print(f'set ENCRYPTION_KEY={key}')
    print("\nBash:")
    print(f'export ENCRYPTION_KEY="{key}"')

if __name__ == '__main__':
    generate_key() 