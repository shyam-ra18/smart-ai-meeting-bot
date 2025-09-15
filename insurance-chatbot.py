import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Step 1: Set ChromeDriver path
chrome_driver_path = r"D:\chromedriver-win64\chromedriver.exe"

# Set the path to your damage photo here
Registration_Photo_path = r"C:\Users\Shyam\Downloads\car.webp"

# Verify photo exists
if not os.path.exists(Registration_Photo_path):
    print(f"WARNING: Photo not found at {Registration_Photo_path}")
    print("Please update Registration_Photo_path with the correct path to your damage photo")
else:
    print(f"Photo found: {Registration_Photo_path}")

options = Options()
options.add_argument("--start-maximized")

service = Service(chrome_driver_path)
driver = webdriver.Chrome(service=service, options=options)

wait = WebDriverWait(driver, 30)

# Step 2: Launch Vehicle damage assessment page
driver.get("https://www.accident.autos/")
print("Title:", driver.title)

time.sleep(1)

# click the chatbot button
chat_button = wait.until(
    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[class*='hnGZLo']"))
)
chat_button.click()

# Step 5: Message loop
messages_seen = []  # list to store chatbot messages

def get_messages():
    """Fetch all chatbot messages currently visible."""
    return driver.find_elements(By.CSS_SELECTOR, "div[class*='crGyWU']")

def send_response(text):
    """Send a message to the chatbot."""
    input_box = driver.find_element(By.CSS_SELECTOR, "input[placeholder*='message']")
    input_box.send_keys(text)
    send_button = driver.find_element(By.CSS_SELECTOR, "button[class*='cAgAUL']")
    send_button.click()

def handle_file_dialog():
    """Handle Windows file dialog using multiple methods."""
    try:
        print("Handling file dialog...")
        time.sleep(2)  # Wait for dialog to fully open

        # Method 1: Use pyautogui (most reliable)
        try:
            import pyautogui
            print("Using pyautogui method...")

            # Type the full file path
            pyautogui.write(Registration_Photo_path)
            time.sleep(1)

            # Press Enter to select the file
            pyautogui.press('enter')
            time.sleep(2)

            print("File selected successfully using pyautogui!")
            return True
        except ImportError:
            print("pyautogui not installed. Install with: pip install pyautogui")
            return False
        except Exception as e:
            print(f"pyautogui method failed: {e}")

    except Exception as e:
        print(f"Error handling file dialog: {e}")
    return False

def upload_photo():
    """Upload photo to the chatbot with multiple methods."""
    try:
        print("Attempting to upload photo...")

        # Define file input selectors
        file_input_selectors = [
            "input[type='file']",
            "input[accept*='image']",
            "input[accept*='/*']"
        ]

        upload_button_selectors = [
            "div[class*='ENykR']",
            "button[class*='upload']",
            "div[class*='upload']",
            "[data-testid*='upload']",
            "input[type='file']"
        ]

        # First, try to find hidden file inputs
        for file_selector in file_input_selectors:
            try:
                file_inputs = driver.find_elements(By.CSS_SELECTOR, file_selector)
                for file_input in file_inputs:
                    try:
                        # Make the input visible if it's hidden
                        driver.execute_script("arguments[0].style.display = 'block';", file_input)
                        driver.execute_script("arguments[0].style.visibility = 'visible';", file_input)
                        driver.execute_script("arguments[0].style.opacity = '1';", file_input)

                        file_input.send_keys(Registration_Photo_path)
                        time.sleep(2)
                        print("Photo uploaded successfully via hidden file input!")
                        return True
                    except Exception as e:
                        print(f"Failed with file input {file_selector}: {e}")
                        continue
            except:
                continue

        # If no hidden file inputs work, try clicking upload buttons
        for selector in upload_button_selectors:
            try:
                upload_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for upload_button in upload_elements:
                    try:
                        if upload_button.is_displayed() or upload_button.tag_name == 'input':
                            print(f"Found upload element: {selector}")

                            if upload_button.tag_name == 'input' and upload_button.get_attribute('type') == 'file':
                                # Direct file input
                                upload_button.send_keys(Registration_Photo_path)
                                time.sleep(2)
                                print("Photo uploaded successfully via direct file input!")
                                return True
                            else:
                                # Click button to open file dialog
                                upload_button.click()
                                time.sleep(1)

                                # Check if file input appeared after clicking
                                for file_selector in file_input_selectors:
                                    try:
                                        file_input = driver.find_element(By.CSS_SELECTOR, file_selector)
                                        print(f"Found file input after click: {file_selector}")
                                        file_input.send_keys(Registration_Photo_path)
                                        time.sleep(2)
                                        print("Photo uploaded successfully!")
                                        return True
                                    except:
                                        continue

                                # If no file input found, assume file dialog opened
                                print("File dialog likely opened. Attempting to handle...")
                                if handle_file_dialog():
                                    print("Photo uploaded successfully via file dialog!")
                                    return True
                    except Exception as e:
                        print(f"Failed with upload button {selector}: {e}")
                        continue
            except:
                continue

    except Exception as e:
        print(f"Error uploading photo: {e}")
    return False

def handle_upload_request():
    """Handle photo upload request from chatbot."""
    print("Chatbot requested photo upload")

    # First, try to upload the photo
    if upload_photo():
        # Wait for upload to complete
        time.sleep(3)

        # Look for confirmation or send button after upload
        confirm_selectors = [
            "button[class*='cAgAUL']",
            "button[type='submit']",
            "button[class*='send']",
            "button[class*='confirm']"
        ]

        # Try CSS selectors
        for selector in confirm_selectors:
            try:
                confirm_button = driver.find_element(By.CSS_SELECTOR, selector)
                if confirm_button.is_displayed() and confirm_button.is_enabled():
                    confirm_button.click()
                    print("Upload confirmed")
                    time.sleep(2)
                    return True
            except:
                continue

        print("Upload completed but no confirmation button found")
        return True
    else:
        # If upload fails, send a text message instead
        print("Upload failed, sending text response")
        send_response("I have photos but having trouble uploading. Can I provide details instead?")
        return False

print("Chatbot automation started. Waiting for messages...")

while True:
    # Check for new messages every 2 seconds regardless of count
    time.sleep(2)

    all_messages = get_messages()

    # Check each message to see if it's new
    for i, msg in enumerate(all_messages):
        try:
            text = msg.text.strip()
            message_id = f"{text}_{i}"  # Unique identifier

            if message_id not in [m.text.strip() + f"_{j}" for j, m in enumerate(messages_seen)]:
                print("New message:", text)
                messages_seen.append(msg)

                # Your response logic here
                if "traffic incident" in text.lower():
                    send_response("Yes")
                    time.sleep(3)  # Wait for bot to process
                elif "full name" in text.lower():
                    send_response("Sneethi C T")
                    time.sleep(3)
                elif "claim reference number" in text.lower():
                    send_response("Yes")
                    time.sleep(3)
                elif "upload a clear photo of your official vehicle registration" in text.lower():
                    # This triggers the photo upload
                    handle_upload_request()
                    time.sleep(5)
                else:
                    print("No matching response pattern found for:", text)

        except Exception as e:
            print(f"Error processing message: {e}")
            continue