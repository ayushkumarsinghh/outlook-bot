import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import random
import string
import json
import os
import re
import asyncio

# --- CONFIG ---
URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9199bf20-a13f-4107-85dc-02114787ef48&scope=https%3A%2F%2Foutlook.office.com%2F.default%20openid%20profile%20offline_access&redirect_uri=https%3A%2F%2Foutlook.live.com%2Fmail%2F&client-request-id=85af84fb-4838-c204-f618-76e540231109&response_mode=fragment&client_info=1&prompt=select_account&nonce=019e35f5-4ebc-7f28-8e36-611bb37f46ef&state=eyJpZCI6IjAxOWUzNWY1LTRlYmItNzdmZS04MzkwLTVlMmMzZTFhN2FiMiIsIm1ldGEiOnsiaW50ZXJhY3Rpb25UeXBlIjoicmVkaXJlY3QifX0%3D%7CaHR0cHM6Ly9vdXRsb29rLmxpdmUuY29tL21haWwvP2N1bHR1cmU9ZW4tdXMmY291bnRyeT11Uw&claims=%7B%22access_token%22%3A%7B%22xms_cc%22%3A%7B%22values%22%3A%5B%22CP1%22%5D%7D%7D%7D&x-client-SKU=msal.js.browser&x-client-VER=4.28.2&response_type=code&code_challenge=Y-gIvtWec47bQ-tJO49QiNIoRYFseu5HdBprFFN3Af0&code_challenge_method=S256&cobrandid=ab0455a0-8d03-46b9-b18b-df2f57b9e44c&fl=dob,flname,wld&sso_reload=true"

CHATGPT_SESSION_URL = "https://chatgpt.com/api/auth/session"
SESSION_FILE_PATH = "chatgpt_session.txt"

driver = None


def clear_session_file():
    try:
        if os.path.exists(SESSION_FILE_PATH):
            os.remove(SESSION_FILE_PATH)
            print("Cleared previous session file")
    except Exception:
        pass


def get_chrome_options():
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    is_cloud = os.getenv("DOCKER_ENV") == "true" or os.name != 'nt'
    if is_cloud:
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--disable-default-apps")
        options.add_argument("--no-first-run")
        options.add_argument("--no-service-autorun")
        options.add_argument("--password-store=basic")
        options.add_argument("--use-gl=swiftshader")
        options.add_argument("--blink-settings=imagesEnabled=false")
        options.add_argument("--js-flags=--max-old-space-size=256")
    return options

def create_driver(options=None):
    # Try auto-detect first
    try:
        print("Initializing Chrome driver (auto-detect)...")
        fresh_options = get_chrome_options()
        return uc.Chrome(options=fresh_options)
    except Exception as e:
        err_msg = str(e)
        print(f"Auto-detect failed: {err_msg}")
        
        # Self-healing: Parse the version from the error message if possible
        match = re.search(r"Current browser version is (\d+)", err_msg)
        if match:
            detected_ver = int(match.group(1))
            print(f"Self-Healing: Detected Chrome version {detected_ver} from error. Retrying...")
            try:
                retry_options = get_chrome_options()
                return uc.Chrome(options=retry_options, version_main=detected_ver)
            except Exception as retry_err:
                print(f"Self-Healing retry failed for version {detected_ver}: {retry_err}")

        # On Windows, try registry lookup
        if os.name == 'nt':
            major_version = None
            try:
                import winreg
                reg_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Google\Chrome\BLBeacon")
                version, _ = winreg.QueryValueEx(reg_key, "version")
                winreg.CloseKey(reg_key)
                major_version = int(version.split(".")[0])
                print(f"Detected Chrome major version: {major_version} (HKCU)")
            except Exception:
                try:
                    import winreg
                    reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Google\Chrome\BLBeacon")
                    version, _ = winreg.QueryValueEx(reg_key, "version")
                    winreg.CloseKey(reg_key)
                    major_version = int(version.split(".")[0])
                    print(f"Detected Chrome major version: {major_version} (HKLM)")
                except Exception:
                    pass

            if major_version:
                try:
                    print(f"Initializing Chrome driver with version_main={major_version}...")
                    reg_options = get_chrome_options()
                    return uc.Chrome(options=reg_options, version_main=major_version)
                except Exception as reg_err:
                    print(f"Failed with version_main={major_version}: {reg_err}")

        # Fallback to common versions
        for ver in [148, 147, 149]:
            try:
                print(f"Initializing Chrome driver with fallback version_main={ver}...")
                fallback_options = get_chrome_options()
                return uc.Chrome(options=fallback_options, version_main=ver)
            except Exception:
                pass

        # If all else fails, try one last time to let the error propagate
        print("All Chrome driver initialization attempts failed. Trying final fallback...")
        final_options = get_chrome_options()
        return uc.Chrome(options=final_options)

def run_flow(email, password):
    global driver
    
    max_retries = 2
    retry_count = 0
    
    while retry_count < max_retries:
        clear_session_file()
        
        driver = create_driver()
            
        wait = WebDriverWait(driver, 30)

        try:
            driver.get(URL)
            print("Navigated to Outlook URL successfully.")
            
            original_window = driver.current_window_handle
            
            driver.switch_to.new_window('tab')
            chatgpt_window = driver.current_window_handle
            driver.get('https://chatgpt.com/')
            print("Opened ChatGPT in a second tab.")
            
            time.sleep(3)
            current_url = driver.current_url.lower()
            print(f"Current ChatGPT URL: {current_url}")
            
            if "/auth/login" in current_url or "auth/login" in current_url:
                print("Detected /auth/login page - restarting flow...")
                retry_count += 1
                driver.quit()
                driver = None
                print(f"Restart attempt {retry_count}/{max_retries}...")
                time.sleep(2)
                continue
            
            print("Waiting for ChatGPT login button...")
            chatgpt_login_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='login-button']")))
            chatgpt_login_btn.click()
            print("Clicked ChatGPT Log in button.")
            
            print("Waiting for ChatGPT email input...")
            chatgpt_email_input = wait.until(EC.element_to_be_clickable((By.ID, "email")))
            chatgpt_email_input.clear()
            for char in email:
                chatgpt_email_input.send_keys(char)
                time.sleep(0.05)
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", chatgpt_email_input)
            print("Entered email into ChatGPT successfully.")
            
            print("Waiting for ChatGPT Continue button...")
            chatgpt_continue_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
            chatgpt_continue_btn.click()
            print("Clicked ChatGPT Continue button.")
            
            driver.switch_to.window(original_window)
            
            print(f"Typing email: {email}")
            email_input = wait.until(EC.element_to_be_clickable((By.ID, "i0116")))
            email_input.clear()
            for char in email:
                email_input.send_keys(char)
                time.sleep(0.05)
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", email_input)
            print("Email entered successfully.")
            
            time.sleep(1)
            next_btn = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
            next_btn.click()
            print("Clicked 'Next' button.")

            print("Waiting for password field...")
            password_input = wait.until(EC.element_to_be_clickable((By.ID, "passwordEntry")))
            password_input.clear()
            for char in password:
                password_input.send_keys(char)
                time.sleep(0.05)
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", password_input)
            print("Password entered successfully.")
            
            time.sleep(1)
            submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='primaryButton']")))
            submit_btn.click()
            print("Clicked 'Next' (Submit) button.")
            
            print("Checking for 'Skip for now' / security setup prompts...")
            time.sleep(2)
            for i in range(7):
                try:
                    cancel_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Cancel')] | //input[@id='idCancel'] | //*[@id='idCancel'] | //input[@value='Cancel'] | //*[contains(text(), 'Cancel')]")
                    passkey_header = driver.find_elements(By.XPATH, "//*[contains(text(), 'Setting up your passkey') or contains(text(), 'passkey')]")
                    
                    if cancel_btns and (cancel_btns[0].is_displayed() or (passkey_header and len(passkey_header) > 0)):
                        cancel_btns[0].click()
                        print(f"Clicked Microsoft Passkey setup 'Cancel' button (Attempt {i+1})!")
                        time.sleep(4)
                        continue
                    
                    skip_btns = driver.find_elements(By.ID, "iShowSkip")
                    if skip_btns and skip_btns[0].is_displayed():
                        skip_btns[0].click()
                        print(f"Clicked 'Skip for now' (Attempt {i+1}).")
                        time.sleep(3)
                    else:
                        skip_btns_xpath = driver.find_elements(By.XPATH, "//*[contains(@id, 'iShowSkip') or contains(text(), 'Skip for now')]")
                        if skip_btns_xpath and skip_btns_xpath[0].is_displayed():
                            skip_btns_xpath[0].click()
                            print(f"Clicked 'Skip for now' via XPath (Attempt {i+1}).")
                            time.sleep(3)
                        else:
                            break
                except Exception as e_skip:
                    print(f"Skip/Cancel loop iteration {i+1} handled exception: {e_skip}")
                    break
            
            print("Waiting for 'Stay signed in' prompt...")
            try:
                no_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='secondaryButton']")))
                no_btn.click()
                print("Clicked 'No' button on 'Stay signed in' prompt.")
            except Exception:
                try:
                    no_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'No') or contains(text(), 'no')]")))
                    no_btn.click()
                    print("Clicked 'No' button on 'Stay signed in' prompt via text match.")
                except Exception as stay_signed_err:
                    print("Stay signed in prompt did not appear or failed:", stay_signed_err)
            
            print("Inbox loaded. Searching for ChatGPT verification emails...")
            time.sleep(3)
            chatgpt_email_found = False
            extracted_code = None
            
            try:
                # Search for "chatgpt code"
                search_input = wait.until(EC.element_to_be_clickable((By.ID, "topSearchInput")))
                search_input.click()
                time.sleep(1)
                search_input.clear()
                
                search_term = "chatgpt code"
                print(f"Typing search query: {search_term}")
                for char in search_term:
                    search_input.send_keys(char)
                    time.sleep(0.1)
                    
                time.sleep(2)
                search_input.send_keys("\n")
                print("Search submitted successfully.")
                
                print("Waiting for search results to display...")
                time.sleep(5)
                
                # CHECK FOR EMPTY STATE
                empty_state = driver.find_elements(By.XPATH, "//span[contains(text(), 'No more results to show')]")
                if empty_state:
                    print("No search results found! Opening TOPMOST email...")
                    time.sleep(2)
                    top_email = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-focusable-row='true'][role='option']")))
                    top_email.click()
                    print("Clicked TOPMOST email!")
                    chatgpt_email_found = True
                else:
                    # Scan for ChatGPT verification code email
                    items = driver.find_elements(By.CSS_SELECTOR, "div[data-focusable-row='true'][role='option']")
                    print(f"Found {len(items)} email list items to scan.")
                    
                    for item in items:
                        text = (item.text or "")
                        aria_label = (item.get_attribute("aria-label") or "")
                        combined_text = (text + " " + aria_label).lower()
                        
                        if "chatgpt" in combined_text and "verification code" in combined_text or "temporary chatgpt login code" in combined_text:
                            code_match = re.search(r'verification code\D*(\d{6})', combined_text, re.IGNORECASE)
                            if code_match:
                                extracted_code = code_match.group(1)
                                print(f"Extracted verification code from preview: {extracted_code}")
                            
                            item.click()
                            print("Clicked ChatGPT verification email!")
                            chatgpt_email_found = True
                            break
            except Exception as scan_err:
                print("Error during search and scan:", scan_err)
                
            if not chatgpt_email_found:
                print("OpenAI verification email not found. Attempting Resend Email procedure...")
                try:
                    driver.switch_to.window(chatgpt_window)
                    print("Switched to ChatGPT window to trigger resend...")
                    
                    time.sleep(2)
                    resend_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='intent'][value='resend']")))
                    resend_btn.click()
                    print("Clicked 'Resend email' button in ChatGPT!")
                    
                    driver.switch_to.window(original_window)
                    print("Switched back to Outlook window...")
                    time.sleep(10)
                    
                    # Refresh search
                    search_input = wait.until(EC.element_to_be_clickable((By.ID, "topSearchInput")))
                    search_input.click()
                    search_input.clear()
                    for char in "chatgpt code":
                        search_input.send_keys(char)
                        time.sleep(0.05)
                    search_input.send_keys("\n")
                    print("Search refreshed.")
                    time.sleep(8)
                    
                    # CHECK EMPTY STATE
                    empty_state = driver.find_elements(By.XPATH, "//span[contains(text(), 'No more results to show')]")
                    if empty_state:
                        print("No search results! Opening TOPMOST email...")
                        time.sleep(2)
                        top_email = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div[data-focusable-row='true'][role='option']")))
                        top_email.click()
                        print("Clicked TOPMOST email!")
                        chatgpt_email_found = True
                    else:
                        items = driver.find_elements(By.CSS_SELECTOR, "div[data-focusable-row='true'][role='option']")
                        for item in items:
                            text = (item.text or "")
                            aria_label = (item.get_attribute("aria-label") or "")
                            combined_text = (text + " " + aria_label).lower()
                            
                            if "chatgpt" in combined_text and "verification code" in combined_text or "temporary chatgpt login code" in combined_text:
                                code_match = re.search(r'verification code\D*(\d{6})', combined_text, re.IGNORECASE)
                                if code_match:
                                    extracted_code = code_match.group(1)
                                    print(f"Extracted verification code: {extracted_code}")
                                item.click()
                                print("Clicked ChatGPT verification email!")
                                chatgpt_email_found = True
                                break
                except Exception as resend_err:
                    print("Failed to auto-resend:", resend_err)
                    
            if not chatgpt_email_found:
                print("Please manually open verification email and press Enter...")
                input()
                
            time.sleep(5)

            print("Monitoring for OpenAI verification codes...")
            
            start_time = time.time()
            while time.time() - start_time < 300:
                try:
                    code_to_enter = None
                    
                    # Try to find code in styled elements
                    try:
                        elements = driver.find_elements(By.XPATH, "//*[contains(@style, 'Menlo') or contains(@style, 'Monaco') or contains(@style, 'F3F3F3')]")
                        for elem in elements:
                            text = elem.text.strip()
                            if len(text) == 6 and text.isdigit():
                                code_to_enter = text
                                print(f"Copied code from styled element: {code_to_enter}")
                                break
                    except Exception:
                        pass
                    
                    if not code_to_enter and extracted_code:
                        code_to_enter = extracted_code
                        print(f"Using pre-extracted code: {code_to_enter}")
                    
                    if not code_to_enter:
                        try:
                            page_text = driver.find_element(By.TAG_NAME, "body").text
                            match = re.search(r'(?:continue|code):\s*(\d{6})', page_text, re.IGNORECASE)
                            if match:
                                code_to_enter = match.group(1)
                            else:
                                matches = re.findall(r'\b\d{6}\b', page_text)
                                if matches:
                                    code_to_enter = matches[0]
                        except Exception:
                            pass
                                
                    if code_to_enter:
                        print(f"FOUND VERIFICATION CODE: {code_to_enter}")
                        
                        driver.switch_to.window(chatgpt_window)
                        print("Entering code in ChatGPT...")
                        
                        code_input = wait.until(EC.element_to_be_clickable((By.NAME, "code")))
                        code_input.clear()
                        for char in code_to_enter:
                            code_input.send_keys(char)
                            time.sleep(0.05)
                        driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", code_input)
                        
                        try:
                            time.sleep(0.5)
                            verify_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[name='intent'][value='validate']")))
                            verify_btn.click()
                            print("Clicked Continue to verify.")
                        except Exception:
                            pass
                        
                        return True
                except Exception as e:
                    print("Error during code checking cycle:", e)
                
                time.sleep(2)
            
            print("Search timed out.")
            return True
            
        except Exception as e:
            print("Flow failed:", e)
            return False


def save_session_to_file(pre_text):
    try:
        with open(SESSION_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(pre_text)
        print(f"Saved to: {os.path.abspath(SESSION_FILE_PATH)}")
    except Exception as e:
        print(f"Failed to save: {e}")

def fill_profile_form():
    global driver
    wait = WebDriverWait(driver, 30)
    
    print("Waiting for profile registration form to load...")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "_r_h_-name")))
        print("Profile form detected successfully.")
    except Exception as wait_err:
        print("Timed out waiting for profile form, proceeding anyway:", wait_err)
        
    time.sleep(2)
    
    # === Only letters for name ===
    random_first = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
    random_last = ''.join(random.choices(string.ascii_lowercase, k=5)).capitalize()
    random_full = f"{random_first} {random_last}"
    print(f"Generated name: {random_full}")
    
    # Generate random age between 18-25
    random_age = str(random.randint(18, 25))
    
    def type_slowly(element, text):
        try:
            element.click()
            time.sleep(0.1)
            element.clear()
            time.sleep(0.1)
            for char in text:
                element.send_keys(char)
                time.sleep(0.04)
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", element)
            driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", element)
            driver.execute_script("arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));", element)
            return True
        except Exception as type_err:
            print(f"Error typing: {type_err}")
            return False

    # === Fill name field ===
    name_filled = False
    
    try:
        name_input = driver.find_element(By.ID, "_r_h_-name")
        if type_slowly(name_input, random_full):
            print(f"Filled name field: {random_full}")
            name_filled = True
    except Exception:
        pass
    
    if not name_filled:
        try:
            name_input = driver.find_element(By.NAME, "name")
            if type_slowly(name_input, random_full):
                print(f"Filled name field: {random_full}")
                name_filled = True
        except Exception:
            pass

    # Wait after entering name
    print("Waiting 2 seconds after entering name...")
    time.sleep(2)

    # === FIX: Find age input using label relationship ===
    age_filled = False
    
    print("Looking for age input field...")
    
    # Method 1: Find input that has label with "Age" text
    try:
        label = driver.find_element(By.XPATH, "//label[contains(text(), 'Age')]")
        label_for = label.get_attribute("for")
        print(f"Found label 'for' attribute: {label_for}")
        
        if label_for:
            age_input = driver.find_element(By.ID, label_for)
            if type_slowly(age_input, random_age):
                print(f"Filled age via label 'for' + type_slowly: {random_age}")
                age_filled = True
    except Exception as e:
        print(f"Method 1 failed: {e}")

    # Method 2: Find input by name="age" or ID containing "age"
    if not age_filled:
        try:
            age_input = driver.find_element(By.NAME, "age")
            if type_slowly(age_input, random_age):
                print(f"Filled age via By.NAME + type_slowly: {random_age}")
                age_filled = True
        except Exception as e:
            print(f"Method 2 failed: {e}")

    # Method 3: Find input by type="number" or placeholder "Age" that's NOT the name field
    if not age_filled:
        try:
            all_inputs = driver.find_elements(By.CSS_SELECTOR, "input")
            for inp in all_inputs:
                try:
                    inp_name = inp.get_attribute("name") or ""
                    inp_placeholder = inp.get_attribute("placeholder") or ""
                    inp_id = inp.get_attribute("id") or ""
                    inp_type = inp.get_attribute("type") or ""
                    
                    if "age" in inp_name.lower() or "age" in inp_placeholder.lower() or "age" in inp_id.lower() or (inp_type == "number" and "name" not in inp_name.lower()):
                        if type_slowly(inp, random_age):
                            print(f"Filled age via generic input scan + type_slowly: {random_age}")
                            age_filled = True
                            break
                except:
                    continue
        except Exception as e:
            print(f"Method 3 failed: {e}")

    # Method 4: Fallback to React-safe JS value setter
    if not age_filled:
        try:
            driver.execute_script(f"""
                var inputs = document.querySelectorAll('input');
                var randomAge = '{random_age}';
                for (var input of inputs) {{
                    var name = (input.getAttribute('name') || '').toLowerCase();
                    var placeholder = (input.getAttribute('placeholder') || '').toLowerCase();
                    var id = (input.getAttribute('id') || '').toLowerCase();
                    
                    if (name.includes('age') || placeholder.includes('age') || id.includes('age')) {{
                        var nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value").set;
                        nativeSetter.call(input, randomAge);
                        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                        console.log("React-safe set val: " + randomAge);
                    }}
                }}
            """)
            print(f"Filled age via React-safe JS fallback: {random_age}")
            age_filled = True
        except Exception as e:
            print(f"Method 4 failed: {e}")

    if not age_filled:
        print("WARNING: Age field was NOT filled!")
    else:
        print(f"✓ Age successfully filled: {random_age}")

    # Click submit button
    print("Looking for submit button...")
    try:
        finish_btn = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Finish') or contains(text(), 'Agree') or contains(text(), 'Continue') or contains(text(), 'Finish creating account')]"))
        )
        finish_btn.click()
        print("Clicked finish button.")
    except Exception as e:
        print(f"Could not click submit: {e}")

    delay = random.randint(10, 15)
    print(f"Waiting {delay} seconds...")
    time.sleep(delay)
    
    print("Opening ChatGPT session API...")
    driver.switch_to.new_window('tab')
    driver.get(CHATGPT_SESSION_URL)
    time.sleep(3)
    
    try:
        pre_element = wait.until(EC.presence_of_element_located((By.TAG_NAME, "pre")))
        pre_text = pre_element.text
        print("="*50)
        print("Session API Response:")
        print("="*50)
        print(pre_text)
        print("="*50)
        
        # Check subscription status from the session JSON
        try:
            session_data = json.loads(pre_text)
            plan_type = session_data.get("account", {}).get("planType", "free").lower()
            print("\n" + "="*50)
            if plan_type == "plus" or "plus" in plan_type:
                print("🎉 SUCCESS: ChatGPT Plus is ACTIVE! (Plan: Plus) 🎉")
            else:
                print(f"❌ INFO: ChatGPT Plus is NOT active (Plan: {plan_type.upper()}) ❌")
            print("="*50 + "\n")
        except Exception as parse_err:
            print(f"Failed to parse subscription status from JSON: {parse_err}")
            
        save_session_to_file(pre_text)
        return pre_text
    except Exception as e:
        print(f"Error: {e}")
        return None

import http.server
import socketserver
import threading
import sys
import urllib.request
import ssl

registration_lock = threading.Lock()

class RailwayHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health" or self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "healthy"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/register":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                email = data.get("email")
                password = data.get("password")
                if not email or not password:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Missing email or password"}).encode("utf-8"))
                    return
                
                print(f"[Railway] Received registration request for {email}")
                
                # Single-threaded lock to prevent browser resource collision
                with registration_lock:
                    result = run_flow(email, password)
                    if result:
                        print("Registration flow succeeded! Completing profile setup...")
                        session_json = fill_profile_form()
                        if session_json:
                            self.send_response(200)
                            self.send_header("Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": True, "session": json.loads(session_json)}).encode("utf-8"))
                        else:
                            self.send_response(500)
                            self.end_headers()
                            self.wfile.write(json.dumps({"success": False, "error": "Profile filled but session retrieval failed"}).encode("utf-8"))
                    else:
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(json.dumps({"success": False, "error": "Registration flow failed"}).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

def run_http_server(port):
    handler = RailwayHandler
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"🚀 Railway Server is running on port {port}...")
        httpd.serve_forever()

def keep_awake():
    # Wait for the server to fully boot up first
    time.sleep(30)
    app_url = os.getenv("RAILWAY_STATIC_URL") or os.getenv("APP_URL")
    if not app_url:
        print("[Self-Pinger] RAILWAY_STATIC_URL or APP_URL not set. Skipping self-pinging.")
        return
        
    if not app_url.startswith("http"):
        app_url = f"https://{app_url}"
        
    print(f"[Self-Pinger] Started! Pinging {app_url} every 10 minutes to stay awake.")
    
    # Ignore self-signed SSL or temporary handshake issues
    ssl_context = ssl._create_unverified_context()
    
    while True:
        try:
            req = urllib.request.Request(
                app_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as r:
                r.read()
            print("[Self-Pinger] Ping successful! Keeping app awake.")
        except Exception as e:
            print(f"[Self-Pinger] Ping failed: {e}")
        time.sleep(600) # Ping every 10 minutes

if __name__ == "__main__":
    port_env = os.getenv("PORT")
    if port_env:
        # Railway / Docker Cloud Mode
        port = int(port_env)
        # Start background self-pinger thread to prevent free-tier container sleep
        threading.Thread(target=keep_awake, daemon=True).start()
        run_http_server(port)
    else:
        # Local Interactive Mode
        user_input = input("Paste credentials (format: email:password or mail:pass): ").strip()
        
        if ":" not in user_input:
            print("Invalid format! Please paste credentials with a colon separating them (e.g., myemail@outlook.com:mypassword).")
            sys.exit(1)
            
        email_to_use, password_to_use = user_input.split(":", 1)
        email_to_use = email_to_use.strip()
        password_to_use = password_to_use.strip()
        
        print(f"Parsed Email: {email_to_use}")
        print("Starting registration flow...")
        result = run_flow(email_to_use, password_to_use)
        
        if result:
            print("Registration flow succeeded! Completing profile setup...")
            fill_profile_form()
            print("Done!")
        else:
            print("Registration flow failed!")
            
        input("Press Enter to close browser and exit...")