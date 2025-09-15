from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Step 1: Set ChromeDriver path
chrome_driver_path = r"D:\chromedriver-win64\chromedriver.exe"

options = Options()
options.add_argument("--start-maximized")

service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

wait = WebDriverWait(driver, 30)

# Step 2: Launch Emirates Help page
driver.get("https://www.emirates.com/us/english/help/")
print("Title:", driver.title)

time.sleep(1)

# Step 3: Accept cookies
cookies_button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id*='onetrust-accept-btn-handler']"))
)
cookies_button.click()

# Step 4: Scroll down and click chat button
driver.execute_script("window.scrollBy(0,800);")

chat_button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class*='help-centre-contact-us__live-chat-button']"))
)
chat_button.click()

# Step 5: Message loop
messages_seen = []  # list to store chatbot messages

def get_messages():
    """Fetch all chatbot messages currently visible."""
    return driver.find_elements(By.CSS_SELECTOR, "div[class*='markdown webchat--css-']")

def send_response(text):
    """Send a message to the chatbot."""
    input_box = driver.find_element(By.CSS_SELECTOR, "textarea[placeholder*='Type your message here']")
    input_box.send_keys(text)
    send_button = driver.find_element(By.NAME, "ayra-send")
    send_button.click()

print("🤖 Chatbot automation started. Waiting for messages...")

while True:
    # Wait until new messages arrive
    wait.until(lambda d: len(get_messages()) > len(messages_seen))

    # Get all current messages
    all_messages = get_messages()
    # Get only the new ones
    new_messages = all_messages[len(messages_seen):]

    for msg in new_messages:
        text = msg.text.strip()
        print("New message:", text)
        messages_seen.append(msg)  # add to seen list

        # Respond based on chatbot content
        if "first and last name" in text.lower():
            send_response("Sneethi C T")
        elif "email address" in text.lower():
            send_response("sneethict1998@gmail.com")
        elif "phone number" in text.lower():
            send_response("+1 555 123 4567")
        else:
            # Default: just acknowledge the bot
            print("⚡ No rule for this message. Waiting for next one...")

    # Small delay so loop doesn’t hammer CPU
    time.sleep(1)
