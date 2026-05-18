import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os
import discord
from discord.ext import commands
import asyncio

# --- CONFIG ---
URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=9199bf20-a13f-4107-85dc-02114787ef48&scope=https%3A%2F%2Foutlook.office.com%2F.default%20openid%20profile%20offline_access&redirect_uri=https%3A%2F%2Foutlook.live.com%2Fmail%2F&client-request-id=85af84fb-4838-c204-f618-76e540231109&response_mode=fragment&client_info=1&prompt=select_account&nonce=019e35f5-4ebc-7f28-8e36-611bb37f46ef&state=eyJpZCI6IjAxOWUzNWY1LTRlYmItNzdmZS04MzkwLTVlMmMzZTFhN2FiMiIsIm1ldGEiOnsiaW50ZXJhY3Rpb25UeXBlIjoicmVkaXJlY3QifX0%3D%7CaHR0cHM6Ly9vdXRsb29rLmxpdmUuY29tL21haWwvP2N1bHR1cmU9ZW4tdXMmY291bnRyeT11cw&claims=%7B%22access_token%22%3A%7B%22xms_cc%22%3A%7B%22values%22%3A%5B%22CP1%22%5D%7D%7D%7D&x-client-SKU=msal.js.browser&x-client-VER=4.28.2&response_type=code&code_challenge=Y-gIvtWec47bQ-tJO49QiNIoRYFseu5HdBprFFN3Af0&code_challenge_method=S256&cobrandid=ab0455a0-8d03-46b9-b18b-df2f57b9e44c&fl=dob,flname,wld&sso_reload=true"

def run_flow(email, password):
    driver = None
    try:
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        
        # Auto-detect if running on a Linux cloud server or inside Docker container
        is_cloud = os.getenv("DOCKER_ENV") == "true" or os.name != 'nt'
        
        if is_cloud:
            print("☁️ Cloud server detected. Initializing Headless Chrome options...")
            options.add_argument("--headless=new")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            # Let undetected_chromedriver automatically match driver version on Linux cloud
            driver = uc.Chrome(options=options)
        else:
            print("💻 Local Windows machine detected. Starting Chrome in standard GUI mode...")
            driver = uc.Chrome(options=options, version_main=147)
            
        wait = WebDriverWait(driver, 30)

        driver.get(URL)
        print("Navigated to Outlook URL successfully.")
        
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
        
        # Click the "No" button on the Stay Signed In prompt
        print("Waiting for 'Stay signed in' prompt...")
        no_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[data-testid='secondaryButton']")))
        no_btn.click()
        print("Clicked 'No' button on 'Stay signed in' prompt.")
        
        # Locate search bar and input search term
        print("Waiting for Outlook inbox to load and search bar to be clickable...")
        search_input = wait.until(EC.element_to_be_clickable((By.ID, "topSearchInput")))
        search_input.click()
        search_input.clear()
        
        search_term = "chatgpt plus"
        print(f"Typing search query: {search_term}")
        for char in search_term:
            search_input.send_keys(char)
            time.sleep(0.05)
            
        time.sleep(1)
        search_input.send_keys("\n")
        print("Search submitted successfully.")
        
        # Wait for search results to load
        print("Waiting for search results to display...")
        time.sleep(10)
        
        # Scan search list items for ChatGPT Plus subscription email
        found_subscription = False
        try:
            items = driver.find_elements(By.CSS_SELECTOR, "div[data-focusable-row='true'], div[role='option'], div[data-item-index]")
            print(f"Found {len(items)} email list items to scan.")
            
            for item in items:
                text = (item.text or "").lower()
                aria_label = (item.get_attribute("aria-label") or "").lower()
                combined_text = text + " " + aria_label
                
                # Check strictly for subscription receipt phrases (never generic words)
                if "successfully subscribed" in combined_text or "your new plan" in combined_text or "subscribed to chatgpt" in combined_text:
                    found_subscription = True
                    break
        except Exception as scan_err:
            print("Error scanning items in list:", scan_err)
        
        if found_subscription:
            print("\n🎉 yes chatgpt plus is subscribed\n")
            status = "subscribed"
        else:
            print("\n❌ no chatgpt plus subscription email found\n")
            status = "notsubscribed"
            
    except Exception as e:
        print("Flow failed:", e)
        status = "failed (login/error)"
    finally:
        if driver:
            try:
                driver.quit()
                print("Closed browser successfully.")
            except:
                pass
                
    return status

# --- DISCORD BOT CONFIG ---
# Load local .env variables if present
if os.path.exists(".env"):
    try:
        with open(".env", "r") as env_file:
            for line in env_file:
                clean_line = line.strip()
                if clean_line and not clean_line.startswith("#") and "=" in clean_line:
                    key, val = clean_line.split("=", 1)
                    os.environ[key.strip()] = val.strip()
    except Exception as env_err:
        print("Warning: Could not parse local .env file:", env_err)

BOT_TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"🤖 Discord Bot is online as {bot.user}!")
    print("Prefix is '!' - Use '!check <pasted accounts>' to start.")
    print("=" * 50)

@bot.command(name="check")
async def check_accounts(ctx, *, accounts_text: str = None):
    """
    Checks a list of pasted email:password accounts for ChatGPT Plus subscription.
    Example:
    !check
    email1@outlook.com:pass1
    email2@outlook.com:pass2
    """
    if not accounts_text:
        await ctx.send("❌ Please provide accounts in `email:password` format (one per line) after the command.")
        return

    # Parse accounts
    accounts_list = [line.strip() for line in accounts_text.split("\n") if line.strip()]
    if not accounts_list:
        await ctx.send("❌ No accounts detected in the input.")
        return
        
    await ctx.send(f"🚀 Starting batch scan for **{len(accounts_list)}** accounts. Please wait...")
    
    results = {}
    for account in accounts_list:
        if ":" in account:
            email, password = account.split(":", 1)
            email = email.strip()
            password = password.strip()
            
            status_msg = await ctx.send(f"🔄 Scanning account `{email}`...")
            
            # Execute browser automation safely in a background worker thread
            status = await asyncio.to_thread(run_flow, email, password)
            
            # Update status dynamically
            await status_msg.edit(content=f"✅ Finished scanning `{email}`: **{status}**")
            results[email] = status
        else:
            await ctx.send(f"⚠️ Invalid format for `{account}` (skipped). Use `email:password` format.")
            
    # Compile and output final summary checklist
    summary = "\n".join([f"{email}:{status}" for email, status in results.items()])
    
    embed = discord.Embed(
        title="📝 ChatGPT Plus Checklist Summary",
        color=discord.Color.green()
    )
    embed.description = f"```text\n{summary}\n```"
    await ctx.send(embed=embed)

if __name__ == "__main__":
    if BOT_TOKEN == "YOUR_DISCORD_BOT_TOKEN_HERE":
        print("\n⚠️ WARNING: Please configure your DISCORD_TOKEN in the environment variables or edit python.py to add your token.\n")
    bot.run(BOT_TOKEN)