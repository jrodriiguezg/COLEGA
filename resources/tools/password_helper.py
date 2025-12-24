#!/usr/bin/env python3
import os
import sys
import json
import argparse
from werkzeug.security import generate_password_hash

# Add parent directory to path to find modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../config/config.json'))

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Config file not found at {CONFIG_PATH}, creating new one.")
        return {}
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print("Error decoding config.json, starting fresh.")
        return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"Configuration saved to {CONFIG_PATH}")

def set_password(username, password):
    config = load_config()
    hashed_pw = generate_password_hash(password)
    config['admin_user'] = username
    config['admin_pass'] = hashed_pw
    save_config(config)
    print(f"Password for user '{username}' has been hashed and set.")

def main():
    parser = argparse.ArgumentParser(description="Neo Core Password Helper")
    parser.add_argument('--user', default='admin', help="Username to set")
    parser.add_argument('--password', help="Password to set (will prompt if not provided)")
    
    args = parser.parse_args()
    
    password = args.password
    if not password:
        import getpass
        password = getpass.getpass(f"Enter password for user '{args.user}': ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match!")
            sys.exit(1)
            
    set_password(args.user, password)

if __name__ == "__main__":
    main()
