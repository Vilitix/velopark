import psycopg2
import time
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import threading


def create_selenium_review_system():
    """
    Create an interactive Selenium-based review system for velopark detections
    """
    
    # Setup Firefox options
    firefox_options = Options()
    # firefox_options.add_argument("--headless")  # Keep commented for interactive use
    
    # Setup WebDriver with automatic driver management
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    
    # Database connection
    conn = None
    cursor = None
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        
        print("🚀 Starting Selenium Review System")
        print("=" * 50)
        print("Controls:")
        print("  'y' key: Mark as VALID and delete from velopark")
        print("  'n' key: Mark as INVALID and delete from velopark") 
        print("  's' key: Skip this detection (no action)")
        print("  'q' key: Quit the program")
        print("=" * 50)
        
        processed_count = 0
        current_detection = None
        consent_handled = False  # Track if we've handled consent
        
        while True:
            # Get the next unprocessed detection
            cursor.execute("""
                SELECT v.id, v.latitude, v.longitude, v.panoid
                FROM velopark v
                LEFT JOIN processed_data pd ON v.id = pd.velopark_id
                WHERE pd.velopark_id IS NULL
                ORDER BY v.id
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            
            if not result:
                print("✅ All detections have been processed!")
                break
            
            velopark_id, latitude, longitude, panoid = result
            current_detection = {
                'id': velopark_id,
                'latitude': latitude,
                'longitude': longitude,
                'panoid': panoid
            }
            
            # Create Street View URL
            street_view_url = f"https://www.google.com/maps/@{latitude},{longitude},3a,75y,0h,90t/data=!3m4!1e1!3m2!1s{panoid}!2e0"
            
            print(f"\n📍 Detection #{velopark_id}")
            print(f"   Location: {latitude:.6f}, {longitude:.6f}")
            print(f"   Pano ID: {panoid}")
            print(f"   URL: {street_view_url}")
            
            # Navigate to Street View
            driver.get(street_view_url)
            
            # Wait for page to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Initial wait for page elements
            except:
                print("⚠️  Page load timeout, continuing...")
            
            # Handle Google consent page (only on first load)
            if not consent_handled:
                print("🔄 Handling Google consent page...")
                handle_google_consent(driver)
                consent_handled = True
                # Additional wait after consent handling
                time.sleep(3)
            else:
                # Regular wait for subsequent pages
                time.sleep(1)
            
            # Wait a bit more for Street View to fully load
            time.sleep(2)
            
            # Inject keyboard listener with more robust approach
            inject_robust_keyboard_listener(driver)
            
            # Update the detection info in the page
            update_detection_info(driver, current_detection, processed_count)
            
            print(f"🎯 Ready for review. Press 'y' (valid), 'n' (invalid), 's' (skip), or 'q' (quit)")
            
            # Wait for user decision
            decision = wait_for_user_decision(driver)
            
            if decision == 'quit':
                print("👋 Exiting review system...")
                break
            elif decision == 'skip':
                print("⏭️  Skipping this detection")
                continue
            elif decision in ['valid', 'invalid']:
                is_valid = (decision == 'valid')
                
                # Process the decision
                success = process_detection_decision_db(
                    cursor, conn, velopark_id, is_valid
                )
                
                if success:
                    processed_count += 1
                    status = "✅ VALID" if is_valid else "❌ INVALID"
                    print(f"{status} - Detection {velopark_id} processed successfully")
                else:
                    print(f"⚠️  Failed to process detection {velopark_id}")
            
            # Small delay before next detection
            time.sleep(1)
        
        print(f"\n🎉 Review session complete!")
        print(f"📊 Total detections processed: {processed_count}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Review interrupted by user")
        print(f"📊 Processed {processed_count} detections in this session")
    
    except Exception as e:
        print(f"❌ Error in review system: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
        try:
            driver.quit()
        except:
            pass

def inject_robust_keyboard_listener(driver):
    """
    Inject a more robust JavaScript keyboard listener that works with Google Maps
    """
    keyboard_script = """
    // Remove any existing listeners
    if (window.reviewKeyboardListener) {
        document.removeEventListener('keydown', window.reviewKeyboardListener);
    }
    
    // Reset decision state
    window.reviewDecision = null;
    window.reviewDecisionReady = false;
    
    // Create the keyboard listener function
    window.reviewKeyboardListener = function(event) {
        const key = event.key.toLowerCase();
        
        // Only handle our specific keys
        if (['y', 'n', 's', 'q'].includes(key)) {
            // Stop all propagation to prevent Google Maps from handling it
            event.preventDefault();
            event.stopPropagation();
            event.stopImmediatePropagation();
            
            console.log('Key pressed:', key);
            
            if (key === 'y') {
                window.reviewDecision = 'valid';
                console.log('✅ Marked as VALID');
            } else if (key === 'n') {
                window.reviewDecision = 'invalid';
                console.log('❌ Marked as INVALID');
            } else if (key === 's') {
                window.reviewDecision = 'skip';
                console.log('⏭️ Skipped');
            } else if (key === 'q') {
                window.reviewDecision = 'quit';
                console.log('👋 Quit requested');
            }
            
            window.reviewDecisionReady = true;
            
            // Visual feedback
            const feedback = document.getElementById('review-feedback');
            if (feedback) {
                const messages = {
                    'valid': '✅ VALID - Processing...',
                    'invalid': '❌ INVALID - Processing...',
                    'skip': '⏭️ SKIPPED',
                    'quit': '👋 QUITTING...'
                };
                feedback.innerHTML = messages[window.reviewDecision];
                feedback.style.backgroundColor = key === 'y' ? '#27ae60' : 
                                                  key === 'n' ? '#e74c3c' : 
                                                  key === 's' ? '#f39c12' : '#95a5a6';
            }
            
            return false; // Prevent any further handling
        }
    };
    
    // Add listener with capture=true to catch events before Google Maps
    document.addEventListener('keydown', window.reviewKeyboardListener, true);
    
    // Also add to window and body for redundancy
    window.addEventListener('keydown', window.reviewKeyboardListener, true);
    document.body.addEventListener('keydown', window.reviewKeyboardListener, true);
    
    console.log('🎹 Robust keyboard listener activated');
    console.log('Press: y=valid, n=invalid, s=skip, q=quit');
    
    // Test the listener immediately
    console.log('Testing keyboard listener...');
    """
    
    driver.execute_script(keyboard_script)
    
    # Give some time for the script to take effect
    time.sleep(0.5)

def wait_for_user_decision(driver, timeout=300):
    """
    Wait for user to make a decision via keyboard with better debugging
    """
    start_time = time.time()
    
    print("⌨️  Waiting for your decision... (press Y, N, S, or Q)")
    
    while time.time() - start_time < timeout:
        try:
            # Check if decision is ready
            decision_ready = driver.execute_script("return window.reviewDecisionReady;")
            
            if decision_ready:
                decision = driver.execute_script("return window.reviewDecision;")
                
                # Reset for next iteration
                driver.execute_script("""
                    window.reviewDecision = null;
                    window.reviewDecisionReady = false;
                """)
                
                return decision
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️  Error checking decision: {e}")
            # Re-inject the keyboard listener if there was an error
            try:
                inject_robust_keyboard_listener(driver)
            except:
                pass
            time.sleep(0.5)
    
    print("⏰ Timeout waiting for user decision, skipping...")
    return 'skip'

# Add the rest of your existing functions (handle_google_consent, update_detection_info, etc.)
# ... (keep all the other functions as they were)

def create_selenium_review_system():
    """
    Create an interactive Selenium-based review system for velopark detections
    """
    
    # Setup Firefox options
    firefox_options = Options()
    # firefox_options.add_argument("--headless")  # Keep commented for interactive use
    
    # Setup WebDriver with automatic driver management
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    
    # Database connection
    conn = None
    cursor = None
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        
        print("🚀 Starting Selenium Review System")
        print("=" * 50)
        print("Controls:")
        print("  'y' key: Mark as VALID and delete from velopark")
        print("  'n' key: Mark as INVALID and delete from velopark") 
        print("  's' key: Skip this detection (no action)")
        print("  'q' key: Quit the program")
        print("=" * 50)
        
        processed_count = 0
        current_detection = None
        consent_handled = False  # Track if we've handled consent
        
        while True:
            # Get the next unprocessed detection
            cursor.execute("""
                SELECT v.id, v.latitude, v.longitude, v.panoid
                FROM velopark v
                LEFT JOIN processed_data pd ON v.id = pd.velopark_id
                WHERE pd.velopark_id IS NULL
                ORDER BY v.id
                LIMIT 1
            """)
            
            result = cursor.fetchone()
            
            if not result:
                print("✅ All detections have been processed!")
                break
            
            velopark_id, latitude, longitude, panoid = result
            current_detection = {
                'id': velopark_id,
                'latitude': latitude,
                'longitude': longitude,
                'panoid': panoid
            }
            
            # Create Street View URL
            street_view_url = f"https://www.google.com/maps/@{latitude},{longitude},3a,75y,0h,90t/data=!3m4!1e1!3m2!1s{panoid}!2e0"
            
            print(f"\n📍 Detection #{velopark_id}")
            print(f"   Location: {latitude:.6f}, {longitude:.6f}")
            print(f"   Pano ID: {panoid}")
            print(f"   URL: {street_view_url}")
            
            # Navigate to Street View
            driver.get(street_view_url)
            
            # Wait for page to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(2)  # Initial wait for page elements
            except:
                print("⚠️  Page load timeout, continuing...")
            
            # Handle Google consent page (only on first load)
            if not consent_handled:
                print("🔄 Handling Google consent page...")
                handle_google_consent(driver)
                consent_handled = True
                # Additional wait after consent handling
                time.sleep(3)
            else:
                # Regular wait for subsequent pages
                time.sleep(1)
            
            # Inject keyboard listener
            inject_keyboard_listener(driver)
            
            # Update the detection info in the page
            update_detection_info(driver, current_detection, processed_count)
            
            print(f"🎯 Ready for review. Press 'y' (valid), 'n' (invalid), 's' (skip), or 'q' (quit)")
            
            # Wait for user decision
            decision = wait_for_user_decision(driver)
            
            if decision == 'quit':
                print("👋 Exiting review system...")
                break
            elif decision == 'skip':
                print("⏭️  Skipping this detection")
                continue
            elif decision in ['valid', 'invalid']:
                is_valid = (decision == 'valid')
                
                # Process the decision
                success = process_detection_decision_db(
                    cursor, conn, velopark_id, is_valid
                )
                
                if success:
                    processed_count += 1
                    status = "✅ VALID" if is_valid else "❌ INVALID"
                    print(f"{status} - Detection {velopark_id} processed successfully")
                else:
                    print(f"⚠️  Failed to process detection {velopark_id}")
            
            # Small delay before next detection
            time.sleep(1)
        
        print(f"\n🎉 Review session complete!")
        print(f"📊 Total detections processed: {processed_count}")
        
    except KeyboardInterrupt:
        print(f"\n⏹️  Review interrupted by user")
        print(f"📊 Processed {processed_count} detections in this session")
    
    except Exception as e:
        print(f"❌ Error in review system: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        
        try:
            driver.quit()
        except:
            pass

def handle_google_consent(driver):
    """
    Handle Google consent page using keyboard navigation
    Inspired by auto_walkthrough.py consent handling
    """
    try:
        print("🔄 Attempting to handle Google consent...")
        
        # Get the body element for keyboard interaction
        body = driver.find_element(By.TAG_NAME, "body")
        
        # Navigate through consent dialog using TAB and ENTER
        # This mimics the auto_walkthrough.py approach
        for i in range(5):
            body.send_keys(Keys.TAB)
            time.sleep(0.1)
        
        # Press ENTER to accept/confirm
        body.send_keys(Keys.ENTER)
        time.sleep(1.3)
        
        print("✅ Google consent handled successfully")
        
    except Exception as e:
        print(f"⚠️  Could not handle consent automatically: {e}")
        print("📝 You may need to manually accept consent if it appears")


def inject_keyboard_listener(driver):
    """
    Inject JavaScript keyboard listener into the page
    """
    keyboard_script = """
    window.reviewDecision = null;
    window.reviewDecisionReady = false;
    
    document.addEventListener('keydown', function(event) {
        const key = event.key.toLowerCase();
        
        if (['y', 'n', 's', 'q'].includes(key)) {
            event.preventDefault();
            
            if (key === 'y') {
                window.reviewDecision = 'valid';
                console.log('✅ Marked as VALID');
            } else if (key === 'n') {
                window.reviewDecision = 'invalid';
                console.log('❌ Marked as INVALID');
            } else if (key === 's') {
                window.reviewDecision = 'skip';
                console.log('⏭️ Skipped');
            } else if (key === 'q') {
                window.reviewDecision = 'quit';
                console.log('👋 Quit requested');
            }
            
            window.reviewDecisionReady = true;
            
            // Visual feedback
            const feedback = document.getElementById('review-feedback');
            if (feedback) {
                const messages = {
                    'valid': '✅ VALID - Processing...',
                    'invalid': '❌ INVALID - Processing...',
                    'skip': '⏭️ SKIPPED',
                    'quit': '👋 QUITTING...'
                };
                feedback.innerHTML = messages[window.reviewDecision];
                feedback.style.backgroundColor = key === 'y' ? '#27ae60' : 
                                                  key === 'n' ? '#e74c3c' : 
                                                  key === 's' ? '#f39c12' : '#95a5a6';
            }
        }
    });
    
    console.log('🎹 Keyboard listener activated');
    console.log('Press: y=valid, n=invalid, s=skip, q=quit');
    """
    
    driver.execute_script(keyboard_script)

def update_detection_info(driver, detection, processed_count):
    """
    Update the page with current detection information
    """
    info_script = f"""
    // Remove existing info panel
    const existingPanel = document.getElementById('review-panel');
    if (existingPanel) existingPanel.remove();
    
    // Create info panel
    const panel = document.createElement('div');
    panel.id = 'review-panel';
    panel.style.cssText = `
        position: fixed;
        top: 20px;
        left: 20px;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 15px;
        border-radius: 8px;
        font-family: Arial, sans-serif;
        font-size: 14px;
        z-index: 10000;
        max-width: 300px;
    `;
    
    panel.innerHTML = `
        <h3 style="margin: 0 0 10px 0; color: #3498db;">🚴 Detection #{detection['id']}</h3>
        <p style="margin: 5px 0;"><strong>📍 Location:</strong> {detection['latitude']:.6f}, {detection['longitude']:.6f}</p>
        <p style="margin: 5px 0;"><strong>🆔 Pano ID:</strong> {detection['panoid']}</p>
        <p style="margin: 5px 0;"><strong>📊 Processed:</strong> {processed_count}</p>
        <hr style="margin: 10px 0; border: 1px solid #555;">
        <p style="margin: 5px 0; font-weight: bold;">🎹 Controls:</p>
        <p style="margin: 3px 0; font-size: 12px;">Y = Valid | N = Invalid | S = Skip | Q = Quit</p>
        <div id="review-feedback" style="margin-top: 10px; padding: 8px; border-radius: 4px; text-align: center; font-weight: bold; background: #34495e;">
            Ready for review...
        </div>
    `;
    
    document.body.appendChild(panel);
    
    // Reset decision state
    window.reviewDecision = null;
    window.reviewDecisionReady = false;
    """
    
    driver.execute_script(info_script)

def wait_for_user_decision(driver, timeout=300):
    """
    Wait for user to make a decision via keyboard
    
    Args:
        driver: Selenium WebDriver instance
        timeout: Maximum wait time in seconds
    
    Returns:
        str: User decision ('valid', 'invalid', 'skip', 'quit')
    """
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            # Check if decision is ready
            decision_ready = driver.execute_script("return window.reviewDecisionReady;")
            
            if decision_ready:
                decision = driver.execute_script("return window.reviewDecision;")
                
                # Reset for next iteration
                driver.execute_script("""
                    window.reviewDecision = null;
                    window.reviewDecisionReady = false;
                """)
                
                return decision
            
            time.sleep(0.1)
            
        except Exception as e:
            print(f"⚠️  Error checking decision: {e}")
            time.sleep(0.5)
    
    print("⏰ Timeout waiting for user decision, skipping...")
    return 'skip'

def process_detection_decision_db(cursor, conn, velopark_id, is_valid, notes=None):
    """
    Process a decision and update the database
    
    Args:
        cursor: Database cursor
        conn: Database connection
        velopark_id (int): ID of the velopark record
        is_valid (bool): Whether the detection is valid
        notes (str): Optional notes
    
    Returns:
        bool: Success status
    """
    try:
        # Insert into processed_data table
        cursor.execute("""
            INSERT INTO processed_data (velopark_id, is_valid, notes)
            VALUES (%s, %s, %s)
            ON CONFLICT (velopark_id) DO UPDATE SET
                is_valid = EXCLUDED.is_valid,
                reviewed_at = CURRENT_TIMESTAMP,
                notes = EXCLUDED.notes
        """, (velopark_id, is_valid, notes))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return False



def get_review_progress():
    """
    Get current review progress
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM velopark")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data")
        processed = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data WHERE is_valid = true")
        valid = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data WHERE is_valid = false")
        invalid = cursor.fetchone()[0]
        
        remaining = total - processed
        
        print(f"📊 REVIEW PROGRESS:")
        print(f"   Total detections: {total}")
        print(f"   Processed: {processed}")
        print(f"   Remaining: {remaining}")
        print(f"   Valid: {valid}")
        print(f"   Invalid: {invalid}")
        
        if processed > 0:
            accuracy = (valid / processed) * 100
            print(f"   AI Accuracy: {accuracy:.1f}%")
        
    except Exception as e:
        print(f"❌ Error getting progress: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def reset_review_progress():
    """
    Reset all review progress (clear processed_data table)
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM processed_data")
        conn.commit()
        
        print("✅ Review progress reset - all decisions cleared")
        
    except Exception as e:
        print(f"❌ Error resetting progress: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--progress":
            get_review_progress()
        elif sys.argv[1] == "--reset":
            reset_review_progress()
        else:
            print("Usage:")
            print("  python processresultv2.py           - Start review system")
            print("  python processresultv2.py --progress - Show progress")
            print("  python processresultv2.py --reset   - Reset progress")
    else:
        create_selenium_review_system()