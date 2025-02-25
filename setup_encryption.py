import os
import binascii
from pathlib import Path

def setup_encryption():
    """Generate and save encryption key."""
    # Generate a secure 32-byte key
    key = binascii.hexlify(os.urandom(32)).decode()
    
    # Save the key to a file
    with open('encryption_key.txt', 'w') as f:
        f.write(key)
    
    print("\nGenerated encryption key:")
    print(key)
    print("\nThe key has been saved to 'encryption_key.txt'")
    print("\nTo use this key, set it as an environment variable:")
    print("PowerShell:")
    print(f'$env:ENCRYPTION_KEY = "{key}"')
    print("\nCmd:")
    print(f'set ENCRYPTION_KEY={key}')
    print("\nBash:")
    print(f'export ENCRYPTION_KEY="{key}"')
    
    # Create a .env file
    env_content = f'ENCRYPTION_KEY="{key}"'
    with open('.env', 'a') as f:
        f.write(f'\n{env_content}\n')
    print("\nThe key has also been added to .env file")

if __name__ == '__main__':
    setup_encryption() 