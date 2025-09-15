from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import re

class EmiratesChatbotTester:
    def __init__(self, chrome_driver_path):
        self.chrome_driver_path = chrome_driver_path
        self.driver = None
        self.wait = None
        self.messages_seen = []
        self.conversation_context = {}

        # Dummy data pools
        self.dummy_data = {
            'names': [
                'John Smith', 'Sarah Johnson', 'Michael Brown', 'Emily Davis',
                'David Wilson', 'Jessica Miller', 'Robert Taylor', 'Ashley Garcia',
                'Christopher Martinez', 'Amanda Rodriguez', 'Matthew Lopez', 'Jennifer Hernandez'
            ],
            'emails': [
                'john.smith@email.com', 'sarah.j@gmail.com', 'mike.brown@yahoo.com',
                'emily.davis@outlook.com', 'david.w@hotmail.com', 'jessica.m@gmail.com',
                'robert.taylor@email.com', 'ashley.g@yahoo.com', 'chris.m@outlook.com',
                'amanda.r@gmail.com', 'matt.lopez@email.com', 'jennifer.h@yahoo.com'
            ],
            'phone_numbers': [
                '+1 555 123 4567', '+1 555 987 6543', '+1 555 246 8135',
                '+1 555 369 2580', '+1 555 147 2589', '+1 555 753 9514',
                '+44 20 7946 0958', '+971 4 316 6000', '+91 11 4567 8900'
            ],
            'destinations': [
                'Dubai', 'London', 'New York', 'Paris', 'Tokyo', 'Sydney',
                'Mumbai', 'Bangkok', 'Singapore', 'Madrid', 'Rome', 'Cairo',
                'Johannesburg', 'Lagos', 'Frankfurt', 'Amsterdam', 'Istanbul'
            ],
            'dates': [
                '25th December 2025', '15th January 2026', '20th February 2026',
                '10th March 2026', '5th April 2026', '18th May 2026',
                '22nd June 2026', '30th July 2026', '12th August 2026'
            ],
            'passenger_counts': [
                '1 adult', '2 adults', '1 adult, 1 child', '2 adults, 1 child',
                '3 adults', '2 adults, 2 children', '4 adults', '1 adult, 2 children'
            ],
            'booking_references': [
                'AB12345', 'CD67890', 'EF13579', 'GH24680', 'IJ97531',
                'KL86420', 'MN75319', 'OP64208', 'QR53107', 'ST42096'
            ],
            'skyward_numbers': [
                'SK123456789', 'SK987654321', 'SK456789123', 'SK321654987',
                'SK789123456', 'SK654987321', 'SK147258369', 'SK963852741'
            ],
            'complaint_types': [
                'Flight delay', 'Baggage issue', 'Seat problem', 'Food complaint',
                'Staff behavior', 'Booking error', 'Refund request', 'Upgrade issue'
            ],
            'special_assistance': [
                'Wheelchair assistance', 'Special meal', 'Infant travel',
                'Pet travel', 'Medical equipment', 'Unaccompanied minor'
            ]
        }

    def setup_driver(self):
        """Initialize Chrome WebDriver with options."""
        options = Options()
        options.add_argument("--start-maximized")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        service = Service(self.chrome_driver_path)
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 30)

        # Execute script to remove webdriver property
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def launch_emirates_chat(self):
        """Navigate to Emirates help page and start chat."""
        try:
            self.driver.get("https://www.emirates.com/us/english/help/")
            print(f"✅ Launched Emirates Help Page: {self.driver.title}")

            time.sleep(2)

            # Accept cookies
            try:
                cookies_button = self.wait.until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[id*='onetrust-accept-btn-handler']"))
                )
                cookies_button.click()
                print("✅ Accepted cookies")
            except TimeoutException:
                print("⚠️ No cookie banner found")

            # Scroll and find chat button
            self.driver.execute_script("window.scrollBy(0,800);")
            time.sleep(1)

            chat_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[class*='help-centre-contact-us__live-chat-button']"))
            )
            chat_button.click()
            print("✅ Chat started successfully")

        except Exception as e:
            print(f"❌ Error launching chat: {e}")
            return False

        return True

    def get_messages(self):
        """Fetch all chatbot messages currently visible."""
        try:
            return self.driver.find_elements(By.CSS_SELECTOR, "div[class*='markdown webchat--css-']")
        except:
            return []

    def send_response(self, text):
        """Send a message to the chatbot."""
        try:
            input_box = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "textarea[placeholder*='Type your message here']"))
            )
            input_box.clear()
            input_box.send_keys(text)

            send_button = self.driver.find_element(By.NAME, "ayra-send")
            send_button.click()
            print(f"📤 Sent: {text}")
            time.sleep(1)

        except Exception as e:
            print(f"❌ Error sending message: {e}")

    def handle_quick_replies(self, specific_choice=None):
        """Click a quick reply button randomly or by specific choice."""
        try:
            # Wait a bit for buttons to load
            time.sleep(2)

            # Look for different types of buttons
            button_selectors = [
                "button.ac-pushButton",
                "button[class*='quick-reply']",
                "div[class*='quick-reply'] button",
                "button[class*='suggestion']"
            ]

            buttons = []
            for selector in button_selectors:
                found_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                buttons.extend(found_buttons)

            if not buttons:
                print("⚠️ No quick reply buttons found")
                return False

            # Filter visible buttons
            visible_buttons = [btn for btn in buttons if btn.is_displayed() and btn.is_enabled()]

            if not visible_buttons:
                print("⚠️ No visible quick reply buttons found")
                return False

            print(f"🔍 Found {len(visible_buttons)} quick reply options:")
            for i, btn in enumerate(visible_buttons):
                print(f"   {i+1}. {btn.text.strip()}")

            # Choose button
            if specific_choice:
                for btn in visible_buttons:
                    if specific_choice.lower() in btn.text.lower():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                        time.sleep(0.5)
                        btn.click()
                        print(f"✅ Clicked specific choice: '{btn.text.strip()}'")
                        return True
                print(f"⚠️ Specific choice '{specific_choice}' not found")

            # Random selection
            selected_button = random.choice(visible_buttons)
            self.driver.execute_script("arguments[0].scrollIntoView(true);", selected_button)
            time.sleep(0.5)
            selected_button.click()
            print(f"✅ Randomly selected: '{selected_button.text.strip()}'")

            # Store context
            self.conversation_context['last_selection'] = selected_button.text.strip()
            return True

        except Exception as e:
            print(f"❌ Error handling quick replies: {e}")
            return False

    def get_random_data(self, data_type):
        """Get random data from dummy data pools."""
        if data_type in self.dummy_data:
            return random.choice(self.dummy_data[data_type])
        return "Data not available"

    def analyze_message_and_respond(self, message_text):
        """Analyze chatbot message and provide appropriate response."""
        message_lower = message_text.lower()

        # Personal information requests
        if any(phrase in message_lower for phrase in ['name', 'full name', 'first and last name']):
            name = self.get_random_data('names')
            self.conversation_context['name'] = name
            self.send_response(name)

        elif any(phrase in message_lower for phrase in ['email', 'email address']):
            email = self.get_random_data('emails')
            self.conversation_context['email'] = email
            self.send_response(email)

        elif any(phrase in message_lower for phrase in ['phone', 'phone number', 'contact number']):
            phone = self.get_random_data('phone_numbers')
            self.conversation_context['phone'] = phone
            self.send_response(phone)

        # Initial service selection
        elif any(phrase in message_lower for phrase in ['how can i help', 'what can i do', 'help you today']):
            time.sleep(1)
            self.handle_quick_replies()

        # Booking related
        elif any(phrase in message_lower for phrase in ['where would you like to fly', 'destination', 'where to']):
            destination = self.get_random_data('destinations')
            self.conversation_context['destination'] = destination
            self.send_response(destination)

        elif any(phrase in message_lower for phrase in ['when would you like to travel', 'travel date', 'departure date']):
            date = self.get_random_data('dates')
            self.conversation_context['travel_date'] = date
            self.send_response(date)

        elif any(phrase in message_lower for phrase in ['how many passengers', 'number of passengers']):
            passengers = self.get_random_data('passenger_counts')
            self.conversation_context['passengers'] = passengers
            self.send_response(passengers)

        elif any(phrase in message_lower for phrase in ['booking reference', 'confirmation number', 'pnr']):
            booking_ref = self.get_random_data('booking_references')
            self.conversation_context['booking_ref'] = booking_ref
            self.send_response(booking_ref)

        elif any(phrase in message_lower for phrase in ['skywards', 'frequent flyer', 'membership number']):
            skyward_num = self.get_random_data('skyward_numbers')
            self.conversation_context['skyward_num'] = skyward_num
            self.send_response(skyward_num)

        # Complaint/Issue types
        elif any(phrase in message_lower for phrase in ['what is your complaint', 'type of issue', 'problem']):
            complaint = self.get_random_data('complaint_types')
            self.conversation_context['complaint'] = complaint
            self.send_response(complaint)

        # Special assistance
        elif any(phrase in message_lower for phrase in ['special assistance', 'special needs', 'additional help']):
            assistance = self.get_random_data('special_assistance')
            self.conversation_context['assistance'] = assistance
            self.send_response(assistance)

        # Yes/No questions - random response
        elif any(phrase in message_lower for phrase in ['yes or no', 'confirm', 'would you like']):
            response = random.choice(['Yes', 'No'])
            self.send_response(response)

        # Multiple choice or button scenarios
        elif any(phrase in message_lower for phrase in ['select', 'choose', 'option', 'which one']):
            time.sleep(1)
            self.handle_quick_replies()

        # Catch-all for button scenarios
        elif len(message_text.strip()) < 100:  # Short messages likely have buttons
            time.sleep(2)
            if not self.handle_quick_replies():
                # If no buttons found, send a generic response
                generic_responses = [
                    "I would like to proceed with this request",
                    "Please continue",
                    "Yes, that's correct",
                    "I need help with this",
                    "Thank you"
                ]
                self.send_response(random.choice(generic_responses))

    def run_automation_test(self, max_interactions=20):
        """Run the main automation test loop."""
        print("🚀 Starting Emirates Chatbot Automation Test")
        print("=" * 50)

        if not self.launch_emirates_chat():
            return

        interaction_count = 0

        print("🤖 Waiting for chatbot messages...")

        while interaction_count < max_interactions:
            try:
                # Wait for new messages
                self.wait.until(lambda d: len(self.get_messages()) > len(self.messages_seen))

                all_messages = self.get_messages()
                new_messages = all_messages[len(self.messages_seen):]

                for msg in new_messages:
                    text = msg.text.strip()
                    if text:  # Only process non-empty messages
                        print(f"\n📨 Bot: {text}")
                        self.messages_seen.append(msg)

                        # Analyze and respond
                        self.analyze_message_and_respond(text)

                        interaction_count += 1

                        # Add some human-like delay
                        time.sleep(random.uniform(2, 4))

                        if interaction_count >= max_interactions:
                            break

                # Small delay between message checks
                time.sleep(1)

            except TimeoutException:
                print("⏰ No new messages received, continuing...")
                time.sleep(2)
            except Exception as e:
                print(f"❌ Error in automation loop: {e}")
                break

        print(f"\n✅ Automation test completed after {interaction_count} interactions")
        print("📊 Conversation Context Summary:")
        for key, value in self.conversation_context.items():
            print(f"   {key}: {value}")

    def cleanup(self):
        """Clean up resources."""
        if self.driver:
            print("\n🧹 Cleaning up...")
            time.sleep(2)  # Wait a bit before closing
            self.driver.quit()
            print("✅ Browser closed successfully")

# Usage Example
if __name__ == "__main__":
    # Configuration
    CHROME_DRIVER_PATH = r"D:\chromedriver-win64\chromedriver.exe"
    MAX_INTERACTIONS = 25  # Adjust as needed

    # Initialize tester
    tester = EmiratesChatbotTester(CHROME_DRIVER_PATH)

    try:
        # Setup WebDriver
        tester.setup_driver()

        # Run automation test
        tester.run_automation_test(max_interactions=MAX_INTERACTIONS)

    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        # Cleanup
        tester.cleanup()

# Alternative: Quick test function for specific scenarios
def run_quick_test(scenario='booking'):
    """Run a quick test for specific scenarios."""
    tester = EmiratesChatbotTester(r"D:\chromedriver-win64\chromedriver.exe")

    try:
        tester.setup_driver()

        if scenario == 'booking':
            # Force booking scenario by pre-setting context
            tester.conversation_context['scenario'] = 'new_booking'
        elif scenario == 'existing':
            tester.conversation_context['scenario'] = 'existing_booking'
        elif scenario == 'skywards':
            tester.conversation_context['scenario'] = 'skywards'

        tester.run_automation_test(max_interactions=15)

    except Exception as e:
        print(f"❌ Quick test failed: {e}")
    finally:
        tester.cleanup()

# Uncomment to run specific scenario tests:
# run_quick_test('booking')
run_quick_test('existing')
# run_quick_test('skywards')