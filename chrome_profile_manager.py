#!/usr/bin/env python3
"""
Simple Chrome Profile Manager using DrissionPage
Creates and manages a persistent Chrome profile for Google login
"""
import time
from pathlib import Path
from DrissionPage import ChromiumPage, ChromiumOptions
import subprocess

# Profile directory - this will store your Chrome profile
PROFILE_DIR = Path(__file__).parent / "chrome_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)

def kill_chrome():
    """Kill any existing Chrome processes to avoid profile conflicts"""
    try:
        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe", "/T"],
                       capture_output=True, text=True)
        time.sleep(2)  # Wait for processes to close
    except Exception:
        pass

def create_chrome_options():
    """Create Chrome options with persistent profile settings"""
    co = ChromiumOptions()
    
    # Set the profile directory
    co.set_user_data_path(str(PROFILE_DIR))
    co.set_argument('--profile-directory=Default')
    
    # Basic Chrome settings
    # co.set_argument('--start-maximized')
    # co.set_argument('--disable-gpu')
    # co.set_argument('--no-sandbox')
    # co.set_argument('--disable-dev-shm-usage')
    
    # # Allow profile to save data
    # co.set_argument('--disable-web-security')
    # co.set_argument('--allow-running-insecure-content')
    
    # # Auto port to avoid conflicts
    # co.auto_port()
    
    return co

def main():
    """Main function to manage Chrome profile"""
    print("=" * 60)
    print("Chrome Profile Manager")
    print("=" * 60)
    print(f"Profile directory: {PROFILE_DIR}")
    print(f"Profile exists: {PROFILE_DIR.exists()}")
    
    # Check if profile already has data
    default_profile = PROFILE_DIR / "Default"
    has_existing_profile = default_profile.exists() and any(default_profile.iterdir())
    
    print(f"Default profile path: {default_profile}")
    print(f"Default profile exists: {default_profile.exists()}")
    
    if default_profile.exists():
        profile_files = list(default_profile.iterdir())
        print(f"Profile files found: {len(profile_files)}")
        print(f"Profile files: {[f.name for f in profile_files[:10]]}")  # Show first 10 files
    
    if has_existing_profile:
        print("✓ Found existing profile with data")
        print("This should load your saved login automatically")
    else:
        print("○ No existing profile found - this will be a fresh setup")
    
    print("\n" + "=" * 60)
    print("Starting Chrome with persistent profile...")
    print("=" * 60)
    
    # Kill any existing Chrome processes
    kill_chrome()
    
    try:
        # Create Chrome options
        options = create_chrome_options()
        
        # Launch Chrome
        print("Launching Chrome...")
        page = ChromiumPage(options)
        
        print("✓ Chrome launched successfully!")
        print("\nInstructions:")
        print("1. Chrome should now be open with a blank page")
        print("2. Navigate to any Google service (gmail.com, meet.google.com, etc.)")
        print("3. Log in with your Google account")
        print("4. Your login will be automatically saved to the profile")
        print("5. Close Chrome when done (or press Enter here)")
        
        # Wait for user to finish
        input("\nPress Enter when you're done logging in and want to close Chrome...")
        
        # Close Chrome
        page.quit()
        print("✓ Chrome closed. Profile saved.")
        
        # Show profile status
        print("\n" + "=" * 60)
        print("Profile Status:")
        print("=" * 60)
        
        if default_profile.exists():
            profile_files = list(default_profile.iterdir())
            print(f"Profile files created: {len(profile_files)}")
            print(f"All profile files: {[f.name for f in profile_files]}")
            
            # Check for important files
            important_files = ["Login Data", "Cookies", "Preferences", "Local State"]
            for file_name in important_files:
                file_path = default_profile / file_name
                if file_path.exists():
                    print(f"✓ {file_name}")
                else:
                    print(f"○ {file_name} (not found yet)")
        else:
            print("❌ Default profile directory not found!")
        
        print("\nNext time you run this script, your login should be automatically loaded!")
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Chrome is installed and accessible.")
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\nProfile management completed successfully!")
    else:
        print("\nProfile management failed. Please check the error messages above.")
