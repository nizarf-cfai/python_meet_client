#!/usr/bin/env python3
"""
Google Meet Visitor with Audio Bridge
Joins Google Meet and works with the audio bridge for Gemini AI integration

This script:
1. Joins Google Meet using saved Chrome profile
2. Configures audio to work with the audio bridge
3. Allows Gemini AI to participate in the meeting

Usage:
1. First run: python audio_bridge.py
2. Then run: python visit_meet_with_audio.py
"""

import time
from pathlib import Path
from DrissionPage import ChromiumPage, ChromiumOptions
import pyautogui

# Google Meet link
MEET_LINK = "https://meet.google.com/xdt-graq-fcm"
 
# Use the same profile directory as the profile manager
PROFILE_DIR = Path(__file__).parent / "chrome_profile"

def create_chrome_options():
    """Create Chrome options using the saved profile - EXACT copy from chrome_profile_manager.py"""
    co = ChromiumOptions()
    
    # Set the profile directory
    co.set_user_data_path(str(PROFILE_DIR))
    co.set_argument('--profile-directory=Default')
    

    
    return co

def open_new_tab_and_visit(page, url):

    try:
        print(f"Opening new tab and visiting: {url}")
        
        # Use JavaScript to open a new tab with the URL
        # page.run_js(f"window.open('{url}', '_blank');")
        page.new_tab(url=url)
        print(f"✓ New tab opened and navigated to: {url}")
        
        # Wait a moment for the page to load
        time.sleep(2)
        # tabs = page.get_tabs()
        # print(tabs[0].tab_id)
        # page.tab_id = tabs[0].tab_id
        # page.activate_tab(tabs[0])
        
        return True
        
    except Exception as e:
        print(f"❌ Error opening new tab and visiting {url}: {e}")
        return False

def handle_chrome_dialog():
    """
    Handle Chrome screen sharing dialog using screen automation
    """
    print("🎯 Automating Chrome screen sharing dialog...")
    
    # Wait for dialog to appear
    time.sleep(2)
    
    try:
        # Look for "Chrome Tab" option and click it
        print("Looking for 'Chrome Tab' option...")
        chrome_tab_location = pyautogui.locateOnScreen('chrome_tab.png', confidence=0.8)
        if chrome_tab_location:
            pyautogui.click(chrome_tab_location)
            print("✓ Clicked 'Chrome Tab' option")
        else:
            print("○ Could not find 'Chrome Tab' option, trying text search...")
            # Alternative: search for text
            pyautogui.click(400, 300)  # Approximate location of Chrome Tab option
            print("✓ Clicked approximate Chrome Tab location")
        
        time.sleep(1)
        
        # Look for the localhost tab in the list
        print("Looking for localhost tab...")
        # Try to find the tab with "Canvas Board" or "localhost" text
        # This might need adjustment based on your screen resolution
        tab_location = pyautogui.locateOnScreen('localhost_tab.png', confidence=0.7)
        if tab_location:
            pyautogui.click(tab_location)
            print("✓ Clicked localhost tab")
        else:
            print("○ Could not find localhost tab, trying coordinate click...")
            # Fallback: click in the area where tabs are listed
            pyautogui.click(400, 400)  # Adjust coordinates as needed
            print("✓ Clicked approximate tab location")
        
        time.sleep(1)
        
        # Look for "Also share tab audio" checkbox and enable it
        print("Enabling 'Also share tab audio'...")
        audio_checkbox = pyautogui.locateOnScreen('audio_checkbox.png', confidence=0.8)
        if audio_checkbox:
            pyautogui.click(audio_checkbox)
            print("✓ Enabled tab audio sharing")
        else:
            print("○ Could not find audio checkbox, trying coordinate click...")
            pyautogui.click(400, 500)  # Adjust coordinates as needed
            print("✓ Clicked approximate audio checkbox location")
        
        time.sleep(1)
        
        # Click the "Share" button
        print("Clicking 'Share' button...")
        share_button = pyautogui.locateOnScreen('share_button.png', confidence=0.8)
        if share_button:
            pyautogui.click(share_button)
            print("✓ Clicked Share button")
        else:
            print("○ Could not find Share button, trying coordinate click...")
            pyautogui.click(500, 600)  # Adjust coordinates as needed
            print("✓ Clicked approximate Share button location")
        
        print("✓ Chrome dialog automation completed!")
        return True
        
    except Exception as e:
        print(f"❌ Error automating Chrome dialog: {e}")
        print("📋 Manual steps required:")
        print("1. Select 'Chrome Tab' in the dialog")
        print("2. Choose the localhost:3001 tab")
        print("3. Enable 'Also share tab audio'")
        print("4. Click 'Share'")
        return False

def meet_ops(page):
    tabs = page.get_tabs()
    print(f"Tab ID: {tabs[1].tab_id}")
    first_tab = tabs[1]
    
    # Get the title of the first tab
    try:
        title = first_tab.title
        print(f"Tab Title: {title}")
    except Exception as e:
        print(f"Could not get tab title: {e}")
    
    # Also try to get the URL
    try:
        url = first_tab.url
        print(f"Tab URL: {url}")
    except Exception as e:
        print(f"Could not get tab URL: {e}")
    
    # Look for button with data-promo-anchor-id="hNGZQc"
    print("Looking for button with data-promo-anchor-id='hNGZQc'...")
    try:
        button_element = first_tab.ele('@data-promo-anchor-id=hNGZQc', timeout=5)
        if button_element:
            print("✓ Found button with data-promo-anchor-id='hNGZQc'")
            print(f"Button text: {button_element.text}")
            print(f"Button tag: {button_element.tag}")
            button_element.click()
            print("✓ Clicked button")
            
            # Use screen automation to handle the Chrome dialog
            success = handle_chrome_dialog()
            
            if success:
                print("✓ Screen sharing automation completed!")
            else:
                print("⚠️ Screen automation failed, manual intervention may be required")
                
        else:
            print("○ Button with data-promo-anchor-id='hNGZQc' not found")
    except Exception as e:
        print(f"○ Could not find button: {e}")
    


def main():
    """Visit Google Meet with audio bridge integration"""
    print("=" * 60)
    print("Google Meet Visitor with Audio Bridge")
    print("=" * 60)
    print(f"Meet Link: {MEET_LINK}")
    print(f"Using profile: {PROFILE_DIR}")
    
    # Check if profile exists
    default_profile = PROFILE_DIR / "Default"
    if not default_profile.exists():
        print("❌ No saved profile found!")
        print("Please run 'python chrome_profile_manager.py' first to set up your profile.")
        return False
    
    # Show profile status
    profile_files = list(default_profile.iterdir())
    print(f"✓ Found saved profile with {len(profile_files)} files")
    print("You should be automatically logged in!")
    
    # Check for key login files
    login_files = ["Login Data", "Preferences"]
    for file_name in login_files:
        file_path = default_profile / file_name
        if file_path.exists():
            print(f"✓ {file_name} found")
        else:
            print(f"○ {file_name} missing")
    

    try:
        # Create Chrome options
        options = create_chrome_options()
        
        # Launch Chrome
        print("\nLaunching Chrome...")
        page = ChromiumPage(options)
        
        print("✓ Chrome launched successfully!")
        print(f"Navigating to: {MEET_LINK}")
        
        # Visit the Google Meet link
        page.get(MEET_LINK)
        
        print("✓ Navigated to Google Meet")
        print("You should now be logged in automatically!")
        
        # Wait 2 seconds after page load
        print("Waiting 2 seconds after page load...")
        time.sleep(2)
        
        # Click on permission tag
        print("Looking for permission tag...")
        try:
            # Try to find and click the permission element
            permission_element = page.ele('tag:permission', timeout=5)
            if permission_element:
                print("✓ Found permission tag, clicking...")
                permission_element.click()
                print("✓ Clicked permission tag")
                
                # Wait 2 seconds after clicking
                print("Waiting 2 seconds after clicking permission...")
                time.sleep(2)
            else:
                print("○ Permission tag not found")
        except Exception as e:
            print(f"○ Could not find or click permission tag: {e}")
        
        # Click on button with specific attribute
        print("Looking for button with data-promo-anchor-id='w5gBed'...")
        try:
            # Try to find and click the button with the specific attribute
            button_element = page.ele('@data-promo-anchor-id=w5gBed', timeout=5)
            if button_element:
                print("✓ Found button with data-promo-anchor-id='w5gBed', clicking...")
                button_element.click()
                print("✓ Clicked button")
                
                # Wait 2 seconds after clicking
                print("Waiting 2 seconds after clicking button...")
                time.sleep(2)
            else:
                print("○ Button with data-promo-anchor-id='w5gBed' not found")
        except Exception as e:
            print(f"○ Could not find or click button: {e}")
        #data-promo-anchor-id="hNGZQc"


        open_new_tab_and_visit(page, "http://localhost:3001")
        time.sleep(3)
        meet_ops(page)

        
        # Keep the browser open
        print("\n🔄 Meeting is now active with audio bridge integration!")
        print("Press Ctrl+C to close the meeting and stop the audio bridge...")
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Closing meeting...")
        
        print("✓ Actions completed successfully!")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure Chrome is installed and accessible.")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Google Meet with Audio Bridge completed successfully!")
    else:
        print("\n❌ Google Meet with Audio Bridge failed. Please check the error messages above.")
