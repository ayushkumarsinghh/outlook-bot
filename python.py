import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import discord
from discord.ext import commands
import asyncio
import threading

# --- CONFIG ---
URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9199bf20-a13f-4107-85dc-02114787ef48&scope=https%3A%2F%2Foutlook.office.com%2F.default%20openid%20profile%20offline_access&redirect_uri=https%3A%2F%2Foutlook.live.com%2Fmail%2F&client-request-id=85af84fb-4838-c204-f618-76e540231109&response_mode=fragment&client_info=1&prompt=select_account&nonce=019e35f5-4ebc-7f28-8e36-611bb37f46ef&state=eyJpZCI6IjAxOWUzNWY1LTRlYmItNzdmZS04MzkwLTVlMmMzZTFhN2FiMiIsIm1ldGEiOnsiaW50ZXJhY3Rpb25UeXBlIjoicmVkaXJlY3QifX0%3D%7CaHR0cHM6Ly9vdXRsb29rLmxpdmUuY29tL21haWwvP2N1bHR1cmU9ZW4tdXMmY291bnRyeT11cw&claims=%7B%22access_token%22%3A%7B%22xms_cc%22%3A%7B%22values%22%3A%5B%22CP1%22%5D%7D%7D%7D&x-client-SKU=msal.js.browser&x-client-VER=4.28.2&response_type=code&code_challenge=Y-gIvtWec47bQ-tJO49QiNIoRYFseu5HdBprFFN3Af0&code_challenge_method=S256&cobrandid=ab0455a0-8d03-46b9-b18b-df2f57b9e44c&fl=dob,flname,wld&sso_reload=true"

# Lock to prevent concurrent executions
execution_lock = threading.Lock()

def run_flow(email, password):
    driver = None
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            print(f"\n{'='*60}")
            print(f"Starting attempt {attempt + 1}/3 for: {email}")
            print(f"{'='*60}")
            
            options = uc.ChromeOptions()
            options.add_argument("--start-maximized")
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-images")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-software-rasterizer")
            options.add_argument("--disable-features=TranslateUI")
            options.add_argument("--disable-ipc_fuzzing")
            options.add_argument("--single-process")  # Use single process for stability
            
            # Use unique user data dir per account to avoid conflicts
            user_data_dir = f"/tmp/chrome-profile-{email.split('@')[0].replace('.', '_')}"
            options.add_argument(f"--user-data-dir={user_data_dir}")
            
            driver = uc.Chrome(options=options, version_main=147)
            driver.set_page_load_timeout(30)
            driver.set_script_timeout(30)
            
            wait = WebDriverWait(driver, 30)
            
            print(f"Navigating to Outlook URL...")
            driver.get(URL)
            print(f"✓ Page loaded successfully")
            
            print(f"Typing email: {email}")
            email_input = wait.until(EC.element_to_be_clickable((By.ID, "i0116")))
            email_input.clear()
            for char in email:
                email_input.send_keys(char)
                time.sleep(0.05)
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", email_input)
            print(f"✓ Email entered")
            
            time.sleep(1)
            next_btn = wait.until(EC.element_to_be_clickable((By.ID, "idSIButton9")))
            next_btn.click()
            print(f"✓ Clicked 'Next' button")
            
            print(f"Waiting for password field...")
            password_input = wait.until(EC.element_to_be_clickable((By.ID, "passwordEntry")))
            password_input.clear()
            for char in password:
                password_input.send_keys(char)
                time.sleep(0.05)
                
            driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", password_input)
            print(f"✓ Password entered")
            
            time.sleep(1)
            submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='primaryButton']")))
            submit_btn.click()
            print(f"✓ Clicked 'Submit' button")
            
            # Handle passkey prompts
            print(f"Checking for passkey setup prompts...")
            time.sleep(2)
            for i in range(7):
                try:
                    cancel_btns = driver.find_elements(By.XPATH, "//button[contains(text(), 'Cancel')] | //input[@id='idCancel'] | //*[@id='idCancel'] | //input[@value='Cancel'] | //*[contains(text(), 'Cancel')]")
                    passkey_header = driver.find_elements(By.XPATH, "//*[contains(text(), 'Setting up your passkey') or contains(text(), 'passkey')]")
                    
                    if cancel_btns and (cancel_btns[0].is_displayed() or (passkey_header and len(passkey_header) > 0)):
                        cancel_btns[0].click()
                        print(f"✓ Clicked passkey 'Cancel' button")
                        time.sleep(4)
                    else:
                        break
                except Exception as e_skip:
                    break
            
            # Scan inbox initially
            print(f"Scanning inbox initially...")
            time.sleep(3)
            found_subscription = False
            
            try:
                items = driver.find_elements(By.CSS_SELECTOR, "div[data-focusable-row='true'], div[role='option'], div[data-item-index]")
                print(f"Found {len(items)} email items")
                
                for item in items:
                    text = (item.text or "")
                    aria_label = (item.get_attribute("aria-label") or "")
                    combined_text = (text + " " + aria_label).lower()
                    
                    # Check for subscription phrases
                    if any(phrase in combined_text for phrase in ["successfully subscribed", "your new plan", "subscribed to chatgpt", "chatgpt plus", "chatgpt - your new plan", "chatgpt subscription", "subscription confirmed"]):
                        print(f"✓ Found subscription email!")
                        found_subscription = True
                        break
            except Exception as scan_err:
                print(f"Error scanning: {scan_err}")
            
            # If not found, perform search
            if not found_subscription:
                print(f"Performing 'openai' search...")
                try:
                    search_input = wait.until(EC.element_to_be_clickable((By.ID, "topSearchInput")))
                    search_input.click()
                    search_input.clear()
                    
                    search_term = "openai"
                    for char in search_term:
                        search_input.send_keys(char)
                        time.sleep(0.05)
                        
                    time.sleep(1)
                    search_input.send_keys("\n")
                    
                    print(f"Waiting for search results...")
                    time.sleep(10)
                    
                    items = driver.find_elements(By.CSS_SELECTOR, "div[data-focusable-row='true'], div[role='option'], div[data-item-index]")
                    print(f"Found {len(items)} search results")
                    
                    for item in items:
                        text = (item.text or "")
                        aria_label = (item.get_attribute("aria-label") or "")
                        combined_text = (text + " " + aria_label).lower()
                        
                        if any(phrase in combined_text for phrase in ["successfully subscribed", "your new plan", "subscribed to chatgpt", "chatgpt plus", "chatgpt - your new plan", "chatgpt subscription", "subscription confirmed"]):
                            print(f"✓ Found subscription email in search!")
                            found_subscription = True
                            break
                except Exception as search_err:
                    print(f"Search error: {search_err}")
            
            if found_subscription:
                status = "subscribed"
                print(f"\n🎉 SUCCESS: ChatGPT Plus is subscribed!\n")
            else:
                status = "notsubscribed"
                print(f"\n❌ No subscription email found\n")
            
            # Success - close properly
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            return status
            
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # Wait before retry
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"Waiting {wait_time}s before retry...")
                time.sleep(wait_time)
    
    return "failed"

# --- DISCORD BOT CONFIG ---
if os.path.exists(".env"):
    try:
        with open(".env", "r") as env_file:
            for line in env_file:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("#") and "=" in clean_line:
                    key, val = clean_line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    except Exception as env_err:
        print(f"Warning: Could not parse .env file: {env_err}")

BOT_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"🤖 Discord Bot is online as {bot.user}!")
    print("Prefix is '!' - Use '!check <accounts>' to start.")
    print("=" * 50)
    print(f"Execution lock: {'ACTIVE' if execution_lock.locked() else 'READY'}")

@bot.command(name="check")
async def check_accounts(ctx, *, accounts_text: str = None):
    """
    Checks accounts for ChatGPT Plus subscription.
    Usage: !check email1@outlook.com:pass1
    """
    if not accounts_text:
        await ctx.send("❌ Please provide accounts in `email:password` format.")
        return
    
    # Check if already running
    if not execution_lock.acquire(blocking=False):
        await ctx.send("⏳ A scan is already in progress. Please wait for it to finish.")
        return
    
    try:
        accounts_list = [line.strip() for line in accounts_text.split("\n") if line.strip() and ":" in line]
        
        if not accounts_list:
            await ctx.send("❌ No valid accounts found (use email:password format).")
            return
        
        await ctx.send(f"🚀 Starting scan for **{len(accounts_list)}** accounts...")
        
        results = {}
        
        for idx, account in enumerate(accounts_list, 1):
            email, password = account.split(":", 1)
            email = email.strip()
            password = password.strip()
            
            print(f"\n{'#'*60}")
            print(f"Account {idx}/{len(accounts_list)}: {email}")
            print(f"{'#'*60}")
            
            status_msg = await ctx.send(f"🔄 Scanning `{email}` ({idx}/{len(accounts_list)})...")
            
            status = await asyncio.to_thread(run_flow, email, password)
            results[email] = status
            
            emoji = "✅" if status == "subscribed" else "❌"
            await status_msg.edit(content=f"{emoji} Scanned `{email}`: **{status}**")
            
            # Delay between accounts to avoid overwhelming
            if idx < len(accounts_list):
                await asyncio.sleep(3)
        
        # Summary
        subscribed = sum(1 for s in results.values() if s == "subscribed")
        not_subscribed = sum(1 for s in results.values() if s == "notsubscribed")
        failed = sum(1 for s in results.values() if s == "failed")
        
        summary = "\n".join([f"{'✅' if s == 'subscribed' else '❌'} {email}: {s}" for email, s in results.items()])
        
        embed = discord.Embed(
            title="📝 ChatGPT Plus Scan Results",
            color=discord.Color.green() if subscribed > 0 else discord.Color.red()
        )
        embed.add_field(name="Summary", value=f"✅ Subscribed: {subscribed}\n❌ Not Subscribed: {not_subscribed}\n⚠️ Failed: {failed}", inline=False)
        embed.add_field(name="Details", value=f"```\n{summary}\n```", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        print(f"Error in check_accounts: {e}")
        await ctx.send(f"❌ Error: {e}")
    finally:
        execution_lock.release()

@bot.command(name="stop")
async def stop_scan(ctx):
    """Stops any running scan (placeholder for future implementation)"""
    await ctx.send("⏹️ Scan stop feature coming soon.")

if __name__ == "__main__":
    if not BOT_TOKEN or BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("\n⚠️ WARNING: Please set DISCORD_TOKEN in .env file or environment.\n")
    else:
        bot.run(BOT_TOKEN)