import os
import sys
import time
from python import run_flow, fill_profile_form, automate_checkout_link_selenium

def main():
    print("="*60)
    print("🚀 SPARKY GEN PRO - STANDALONE LOCAL RUNNER")
    print("="*60)
    
    # Prompt for credentials
    email = input("Enter Outlook Email: ").strip()
    password = input("Enter Outlook Password: ").strip()
    
    if not email or not password:
        print("[-] Error: Email and password cannot be empty!")
        return
        
    print("\n[*] Starting registration and session retrieval flow...")
    success, driver = run_flow(email, password)
    
    if success and driver:
        try:
            print("[*] Outlook authenticated successfully. Filling onboarding profile form...")
            session_response = fill_profile_form(driver)
            
            if session_response:
                print("[*] Onboarding complete. Generating secure INR Stripe checkout link...")
                stripe_url = automate_checkout_link_selenium(driver, session_response)
                
                if stripe_url:
                    print("\n" + "="*60)
                    print("🎉 SUCCESS! STRIPE CHECKOUT LINK GENERATED:")
                    print("="*60)
                    print(stripe_url)
                    print("="*60 + "\n")
                else:
                    print("[-] Error: Failed to generate Stripe checkout link via the web portal.")
            else:
                print("[-] Error: Failed to retrieve ChatGPT session details.")
        except Exception as e:
            print(f"[-] An unexpected error occurred: {e}")
        finally:
            print("[*] Cleaning up browser processes...")
            try:
                driver.quit()
            except:
                pass
    else:
        print("[-] Flow failed during Outlook/ChatGPT authentication.")
        if driver:
            try:
                driver.quit()
            except:
                pass

if __name__ == "__main__":
    main()
