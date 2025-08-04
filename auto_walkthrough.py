#INSERT INTO panoids (latitude, longitude, pano_id) VALUES (48.6738246, 6.1744465, 'mITixiRaLqJT8pRKf6kvLQ');

import psycopg2
from psycopg2 import sql
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.action_chains import ActionChains
import time
import re
from urllib.parse import urlparse, parse_qs
import folium
import numpy as np
import csv
import os
import sys
import subprocess

def visualize_panoids_on_map():
    """
    Fetch all panoids from the database and visualize them on an interactive map
    """
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
        
        # Fetch all records from panoids table
        cursor.execute("SELECT latitude, longitude, pano_id FROM panoids")
        records = cursor.fetchall()
        
        if not records:
            print("No records found in panoids table")
            return
        
        print(f"Found {len(records)} records")
        
        # Calculate center point (average of all coordinates)
        avg_lat = sum(record[0] for record in records) / len(records)
        avg_lon = sum(record[1] for record in records) / len(records)
        
        # Create map centered on average coordinates
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        for i, (lat, lon, pano_id) in enumerate(records):
            # Create popup with information
            popup_text = f"""
            <div style="width: 200px;">
                <b>Point {i+1}</b><br>
                Latitude: {lat}<br>
                Longitude: {lon}<br>
                Pano ID: {pano_id}<br>
                <a href="https://www.google.com/maps/@{lat},{lon},3a,75y,0h,90t/data=!3m4!1e1!3m2!1s{pano_id}!2e0" target="_blank">View in Street View</a>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=popup_text,
                icon=folium.DivIcon(
                    html=f'<div style="background-color: black; width: 12px; height: 12px; border-radius: 50%; border: 1px solid black;"></div>',
                    icon_size=(12, 12),
                    icon_anchor=(6, 6)
                )
            ).add_to(map_viz)
        
        # Add Nancy center and boundary circle
        nancy_center = [latcenter_nancy, longcenter_nancy]
        nancy_radius = (R_nancy) * 111000  # Convert to meters approximately
        
        folium.Marker(
            location=nancy_center,
            popup="Nancy Center",
            icon=folium.Icon(color='blue', icon='star')
        ).add_to(map_viz)
        
        folium.Circle(
            location=nancy_center,
            radius=nancy_radius,
            color='blue',
            fill=True,
            fillOpacity=0.1,
        ).add_to(map_viz)
        
        # Save map to HTML file
        map_filename = "panoids_map.html"
        map_viz.save(map_filename)
        print(f"Map saved as {map_filename}")
        print(f"Open the file in your web browser to view the interactive map")
        
        return map_viz
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def insert_db(latitude, longitude, pano_id):
    """
    Insert a record into the panoids table with the given parameters.
    Also delete the nearest point from to_insert table within 30 meters.
    
    Args:
        latitude (float): The latitude coordinate
        longitude (float): The longitude coordinate  
        pano_id (str): The panorama ID
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
        # Find and delete the nearest point from to_insert within 30 meters
        find_nearest_query = """
        SELECT latitude, longitude, ST_Distance(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography) as distance_m
        FROM to_insert 
        WHERE ST_DWithin(geom::geography, ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography, 30)
        ORDER BY geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326)
        LIMIT 1;
        """
        
        cursor.execute(find_nearest_query, (longitude, latitude, longitude, latitude, longitude, latitude))
        nearest_point = cursor.fetchone()
        
        if nearest_point:
            nearest_lat, nearest_lon, distance = nearest_point
            
            # Delete the nearest point from to_insert
            delete_query = """
            DELETE FROM to_insert 
            WHERE latitude = %s AND longitude = %s;
            """
            
            cursor.execute(delete_query, (nearest_lat, nearest_lon))
            deleted_count = cursor.rowcount
            
            if deleted_count > 0:
                print(f"✅ Deleted nearest point from to_insert: ({nearest_lat:.6f}, {nearest_lon:.6f}) at {distance:.1f}m")
            else:
                print(f"⚠️  Could not delete nearest point from to_insert")
        else:
            print(f"⚠️  No points found in to_insert within 30 m of ({latitude:.6f}, {longitude:.6f})")
        
        conn.commit()
        # Second insert into panoids the new point
        cursor.execute(
            "INSERT INTO panoids (latitude, longitude, pano_id, geom) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326))",
            (latitude, longitude, pano_id, longitude, latitude)
        )

        # Commit the transaction
        conn.commit()
        print(f"✅ Successfully inserted record: lat={latitude}, lon={longitude}, pano_id={pano_id}")
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return False
    
    finally:
        # Close the connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()


latcenter_nancy = 48.693167;
longcenter_nancy = 6.185472
R_nancy = np.sqrt((latcenter_nancy-48.667770)**2 + (6.146822-longcenter_nancy)**2)

def in_nancy(lat,long):
    return ((long-longcenter_nancy)**2 + (lat-latcenter_nancy)**2 <= R_nancy**2)


def parse_google_maps_url(url):
    """
    Parse Google Maps Street View URL to extract latitude, longitude, and pano_id
    
    Args:
        url (str): Google Maps Street View URL
        
    Returns:
        tuple: (latitude, longitude, pano_id) or (None, None, None) if parsing fails
    """
    try:
        # Parse latitude and longitude from the URL path
        # Pattern: /@latitude,longitude,other_params
        lat_lon_match = re.search(r'/@(-?\d+\.\d+),(-?\d+\.\d+),', url)
        
        if lat_lon_match:
            latitude = float(lat_lon_match.group(1))
            longitude = float(lat_lon_match.group(2))
        else:
            return None, None, None
        
        # Parse pano_id from the URL
        # Look for panoid parameter in the data section
        pano_match = re.search(r'panoid%3D([^%&]+)', url)
        if pano_match:
            pano_id = pano_match.group(1)
        else:
            # Alternative: look for the pano_id in the 3m5 section
            pano_match2 = re.search(r'!3m5!1s([^!]+)!', url)
            if pano_match2:
                pano_id = pano_match2.group(1)
            else:
                return latitude, longitude, None
        
        return latitude, longitude, pano_id
        
    except Exception as e:
        print(f"Error parsing URL: {e}")
        return None, None, None


def create_panoramas_csv(panoid_list):
    """
    Create a CSV file with panoids for the streetview_downloader
    
    Args:
        panoid_list (list): List of pano IDs to write to CSV
    """
    csv_filename = "panoramas.csv"
    
    try:
        with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header (adjust based on your streetview_downloader requirements)
            writer.writerow(['pano_id'])
            
            # Write each panoid
            for panoid in panoid_list:
                writer.writerow([panoid])
        
        print(f"Created {csv_filename} with {len(panoid_list)} panoids")
        return csv_filename
        
    except Exception as e:
        print(f"Error creating CSV: {e}")
        return None


def run_streetview_downloader_single(pano_id, output_dir=None):
    """
    Execute the streetview_downloader command for a single pano ID
    
    Args:
        pano_id (str): Single panorama ID to download
        output_dir (str): Output directory (optional, defaults to ~/street_view_images)
    """
    
    if output_dir is None:
        output_dir = os.path.expanduser("~/street_view_images")
    
    command = [
        "/home/arthur/Bureau/sviewscrap/StreetViewScraper/build/streetview_downloader",
        pano_id,
        "-o", output_dir
    ]
    
    try:
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"Streetview downloader completed successfully for pano ID: {pano_id}")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running streetview downloader for {pano_id}: {e}")
        print(f"stderr: {e.stderr}")
        return False
    except FileNotFoundError:
        print("streetview_downloader executable not found. Check the path.")
        return False


def get_table_counts():
    """
    Get current counts of records in both tables
    
    Returns:
        tuple: (panoids_count, to_insert_count) or (None, None) if error
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
        
        # Get panoids count
        cursor.execute("SELECT COUNT(*) FROM panoids")
        panoids_count = cursor.fetchone()[0]
        
        # Get to_insert count
        cursor.execute("SELECT COUNT(*) FROM to_insert")
        to_insert_count = cursor.fetchone()[0]
        
        return panoids_count, to_insert_count
        
    except Exception as e:
        print(f"❌ Error getting table counts: {e}")
        return None, None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

import time  # Make sure this import is at the top

def selenium_walkthrough(url=None):
    # Setup Firefox options (optional)
    firefox_options = Options()
    # firefox_options.add_argument("--headless")  # Uncomment for headless mode
    move = False
    # Setup WebDriver with automatic driver management
    service = Service(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=firefox_options)
    iter = 0
    keytopress = Keys.ARROW_UP
    
    # ⏱️ START TIMING
    start_time = time.time()
    print(f"🚀 Starting walkthrough at: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
    
    # 📊 GET INITIAL COUNTS
    print("📊 Getting initial database counts...")
    initial_panoids, initial_to_insert = get_table_counts()
    
    if initial_panoids is not None and initial_to_insert is not None:
        print(f"🏁 Starting counts: panoids={initial_panoids:,}, to_insert={initial_to_insert:,}")
    else:
        print("⚠️  Could not get initial counts, continuing anyway...")
        initial_panoids = 0
        initial_to_insert = 0
    
    if url==None:
        coordinates = get_starting_coordinates()
        if coordinates[0] is not None and coordinates[1] is not None:
            url = create_streetview_url(*coordinates)  
    
    # ⏱️ MARK ACTUAL WALKTHROUGH START (after browser setup)
    walkthrough_start_time = time.time()
    try:
        # Navigate to a website
        print("Opening Google...")
        driver.get(url)
        time.sleep(1)
        
        #Consent google data
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(5):
            body.send_keys(Keys.TAB)
            time.sleep(0.1)
        body.send_keys(Keys.ENTER)
        time.sleep(1.3)
        actions = ActionChains(driver)
        #Click to initialize the keyboard shortcut for navigation
        old_lat_long, chained_fail = set_url(driver,actions,url) 
        
        
        while (True):
            try:
                if move:
                    time.sleep(0.8)
                    driver.switch_to.active_element.send_keys(keytopress)
                move = True
                time.sleep(1.6) # maybe we need to make more before it refresh
                current_url = driver.current_url
                lat,long,panoid = parse_google_maps_url(current_url)
                print("early loop lat long panoid")
                print(lat,long,panoid)

                if (lat,long)==old_lat_long:
                    print("cannot go forward")
                    coordinates = get_starting_coordinates()
                    if coordinates[0] is not None and coordinates[1] is not None:
                        url = create_streetview_url(*coordinates)  
                    old_lat_long, chained_fail = set_url(driver,actions,url) 
                    move = False
                    iter+=1
                    continue

                if long==None or lat==None or panoid==None:
                    print("Parsing url problem")
                    break
                if not in_nancy(lat,long):
                    print("Leaving Nancy and setup perimeter")
                    coordinates = get_starting_coordinates()
                    if coordinates[0] is not None and coordinates[1] is not None:
                        url = create_streetview_url(*coordinates)  
                    old_lat_long, chained_fail = set_url(driver,actions,url) 
                    move = False
                    continue
                    
                if not insert_db(lat,long,panoid):
                    print("already seen or db problem")
                    chained_fail+=1

                    if chained_fail>2:
                        print("too much fail aborting trying new url")
                        coordinates = get_starting_coordinates()
                        if coordinates[0] is not None and coordinates[1] is not None:
                            url = create_streetview_url(*coordinates)  
                        old_lat_long, chained_fail = set_url(driver,actions,url) 
                        move = False
                        iter+=1
                        # allow to not try always the same way we already seen and place point one by one
                        if keytopress == Keys.ARROW_DOWN:
                            keytopress = Keys.ARROW_UP
                        else :
                            keytopress = Keys.ARROW_DOWN
                        continue
                    else:
                        continue
                #install images for during the process
                run_streetview_downloader_single(panoid,None)
                old_lat_long = lat,long
                iter+=1
                chained_fail = 0
                
            except Exception as e:
                print(f"Browser interaction failed (browser might be closed): {e}")
                break  # Exit the loop if browser is closed
                
    except Exception as e:
        print(f"Error occurred: {e}")
    
    finally:
        # ⏱️ END TIMING
        end_time = time.time()
        total_duration = end_time - start_time
        walkthrough_duration = end_time - walkthrough_start_time
        
        # This ALWAYS runs, even if browser was closed manually
        print(f"\n🏁 WALKTHROUGH COMPLETED")
        print("=" * 50)
        
        # ⏱️ TIMING INFORMATION
        print(f"⏱️  TIMING STATISTICS:")
        print(f"   🚀 Started at:        {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time))}")
        print(f"   🏁 Completed at:      {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))}")
        print(f"   ⏰ Total duration:    {format_duration(total_duration)}")
        print(f"   🔄 Walkthrough time:  {format_duration(walkthrough_duration)} (excluding browser setup)")
        
        # 📊 GET FINAL COUNTS AND CALCULATE STATISTICS
        print("📊 Getting final database counts...")
        final_panoids, final_to_insert = get_table_counts()
        
        if final_panoids is not None and final_to_insert is not None:
            # Calculate changes
            panoids_added = final_panoids - initial_panoids
            to_insert_deleted = initial_to_insert - final_to_insert
            
            # Calculate total database operations
            total_operations = panoids_added + to_insert_deleted
            
            print(f"📈 FINAL STATISTICS:")
            print(f"   🗄️  Panoids table:")
            print(f"      Initial: {initial_panoids:,}")
            print(f"      Final:   {final_panoids:,}")
            print(f"      ➕ Added:  {panoids_added:,}")
            
            print(f"   📍 To_insert table:")
            print(f"      Initial: {initial_to_insert:,}")
            print(f"      Final:   {final_to_insert:,}")
            print(f"      ➖ Deleted: {to_insert_deleted:,}")
            
            print(f"   🎯 Selenium iterations: {iter}")
            
            # Calculate efficiency metrics
            if iter > 0:
                success_rate = (panoids_added / iter) * 100 if iter > 0 else 0
                print(f"   📊 Success rate: {success_rate:.1f}% ({panoids_added}/{iter} successful inserts)")
            
            # ⚡ PERFORMANCE METRICS
            print(f"\n⚡ PERFORMANCE METRICS:")
            if total_duration > 0:
                operations_per_second = total_operations / total_duration
                panoids_per_second = panoids_added / total_duration
                walkthrough_ops_per_second = total_operations / walkthrough_duration if walkthrough_duration > 0 else 0
                
                print(f"   📊 Total operations: {total_operations:,} ({panoids_added:,} inserts + {to_insert_deleted:,} deletes)")
                print(f"   🚀 Operations/second (total): {operations_per_second:.2f}")
                print(f"   🚀 Operations/second (walkthrough): {walkthrough_ops_per_second:.2f}")
                print(f"   📈 Panoids collected/second: {panoids_per_second:.2f}")
                print(f"   ⏱️  Average time per iteration: {(walkthrough_duration / iter):.2f}s" if iter > 0 else "   ⏱️  No successful iterations")
                
                # Additional timing insights
                if panoids_added > 0:
                    time_per_panoid = walkthrough_duration / panoids_added
                    print(f"   🎯 Average time per successful panoid: {time_per_panoid:.2f}s")
            
            # Summary
            print(f"\n🎯 SUMMARY: Collected {panoids_added:,} new panoids, removed {to_insert_deleted:,} waypoints in {format_duration(total_duration)}")
            
        else:
            print("⚠️  Could not get final counts for statistics")
            print(f"🎯 Selenium iterations completed: {iter}")
            print(f"⏰ Total duration: {format_duration(total_duration)}")
        
        print("=" * 50)
        
        # Try to close browser if still open
        try:
            driver.quit()
        except:
            print("Browser already closed")

def format_duration(seconds):
    """
    Format duration in seconds to human-readable format
    
    Args:
        seconds (float): Duration in seconds
        
    Returns:
        str: Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"
    else:
        hours = int(seconds // 3600)
        remaining_minutes = int((seconds % 3600) // 60)
        remaining_seconds = seconds % 60
        return f"{hours}h {remaining_minutes}m {remaining_seconds:.1f}s"

#to dump db pg_dump -h localhost -U arthur -d imagedb -t panoids > panoids_dump.sql

def get_starting_coordinates():
    """
    Get the first latitude, longitude pair from to_insert table and remove it
    
    Returns:
        tuple: (latitude, longitude) or (None, None) if no coordinates found
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
        
        # Get the first row from to_insert table
        cursor.execute("SELECT latitude, longitude FROM to_insert LIMIT 1")
        result = cursor.fetchone()
        
        if result:
            latitude, longitude = result
            print(f"📍 Retrieved coordinates from to_insert: {latitude}, {longitude}")
            """
            # Delete this point from to_insert since we're using it
            cursor.execute("DELETE FROM to_insert WHERE latitude = %s AND longitude = %s", (latitude, longitude))
            conn.commit()
            print(f"✅ Removed used coordinates from to_insert table")
            """
            return latitude, longitude
        else:
            print("❌ No coordinates found in to_insert table")
            return None, None
            
    except Exception as e:
        print(f"❌ Error getting coordinates from database: {e}")
        return None, None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_streetview_url(latitude, longitude):
    """
    Create a Google Street View URL from coordinates
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
    
    Returns:
        str: Google Street View URL
    """
    return f"https://maps.google.com/maps?q=&layer=c&cbll={latitude},{longitude}"



def set_url(driver,actions,url):
    print(f"Loading new URL from stack: {url[:60]}...")

    # Navigate to new URL
    driver.get(url)
    time.sleep(3.5)
    current_url = driver.current_url
    lat,long,panoid = parse_google_maps_url(current_url)
    if long==None or lat==None or panoid==None:
        print("Timing problem url empty")
    if not insert_db(lat,long,panoid):
        print("already seen or db problem in setting url")
    else:
        run_streetview_downloader_single(panoid,None)
    # Click to reinitialize keyboard shortcuts
    viewport_width = driver.execute_script("return window.innerWidth;")
    viewport_height = driver.execute_script("return window.innerHeight;")    
    middle_x = viewport_width // 2
    middle_y = int(viewport_height * 0.75)
    actions.move_by_offset(middle_x, middle_y).click().perform()
    time.sleep(1.1)
    new_url = driver.current_url
    new_data = parse_google_maps_url(new_url)
    time.sleep(0.15)
    # Reset state for new location
    return (0, 0),0


def get_url_from_clipboard():
    """
    Get URL from clipboard using xclip
    
    Returns:
        str: URL from clipboard or None if failed
    """
    try:
        result = subprocess.run(['xclip', '-selection', 'clipboard', '-o'], 
                              capture_output=True, text=True, check=True)
        url = result.stdout.strip()
        
        # Basic validation to check if it's a Google Maps URL
        if ('google.com/maps' in url or 'google.fr/maps' in url) and '@' in url:
            return url
        else:
            print(f"Clipboard content doesn't appear to be a valid Google Maps URL:")
            print(f"'{url}'")
            return None
            
    except subprocess.CalledProcessError as e:
        print(f"Error reading from clipboard: {e}")
        print("Make sure xclip is installed")
        return None
    except FileNotFoundError:
        print("xclip not found.")
        return None


def find_nearest_points_to_panoids(distance_threshold_m=100):
    """
    Find points in to_insert that are within distance_threshold_m of any panoid
    
    Args:
        distance_threshold_m (float): Distance threshold in meters
    
    Returns:
        list: List of (to_insert_lat, to_insert_lon, nearest_panoid_lat, nearest_panoid_lon, distance_m)
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
        
        # Query to find nearest panoid for each to_insert point within threshold
        query = """
        SELECT 
            ti.latitude as to_insert_lat,
            ti.longitude as to_insert_lon,
            p.latitude as nearest_panoid_lat,
            p.longitude as nearest_panoid_lon,
            ST_Distance(ti.geom::geography, p.geom::geography) as distance_m
        FROM to_insert ti
        CROSS JOIN LATERAL (
            SELECT latitude, longitude, geom
            FROM panoids p
            WHERE ST_DWithin(ti.geom::geography, p.geom::geography, %s)
            ORDER BY ti.geom <-> p.geom
            LIMIT 1
        ) p
        ORDER BY distance_m;
        """
        
        cursor.execute(query, (distance_threshold_m,))
        results = cursor.fetchall()
        
        print(f"📊 Found {len(results)} points in to_insert within {distance_threshold_m}m of panoids")
        
        # Show sample results
        if results:
            print(f"\n📍 Sample nearest points:")
            for i, (ti_lat, ti_lon, p_lat, p_lon, dist) in enumerate(results[:5]):
                print(f"  {i+1}. to_insert({ti_lat:.6f}, {ti_lon:.6f}) -> panoid({p_lat:.6f}, {p_lon:.6f}) | {dist:.1f}m")
        
        return results
        
    except Exception as e:
        print(f"❌ Error finding nearest points: {e}")
        return []
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def delete_close_points_from_to_insert(distance_threshold_m=10, dry_run=True):
    """
    Delete points from to_insert that are too close to existing panoids
    
    Args:
        distance_threshold_m (float): Distance threshold in meters (default: 10m)
        dry_run (bool): If True, only show what would be deleted without actually deleting
    
    Returns:
        int: Number of points deleted (or would be deleted if dry_run=True)
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
        
        if dry_run:
            # Count points that would be deleted
            count_query = """
            SELECT COUNT(*)
            FROM to_insert ti
            WHERE EXISTS (
                SELECT 1 
                FROM panoids p 
                WHERE ST_DWithin(ti.geom::geography, p.geom::geography, %s)
            );
            """
            
            cursor.execute(count_query, (distance_threshold_m,))
            count = cursor.fetchone()[0]
            
            print(f"🔍 DRY RUN: Would delete {count} points from to_insert within {distance_threshold_m}m of panoids")
            
            # Show sample of points that would be deleted
            sample_query = """
            SELECT 
                ti.latitude,
                ti.longitude,
                (
                    SELECT MIN(ST_Distance(ti.geom::geography, p.geom::geography))
                    FROM panoids p
                    WHERE ST_DWithin(ti.geom::geography, p.geom::geography, %s)
                ) as min_distance_m
            FROM to_insert ti
            WHERE EXISTS (
                SELECT 1 
                FROM panoids p 
                WHERE ST_DWithin(ti.geom::geography, p.geom::geography, %s)
            )
            ORDER BY min_distance_m
            LIMIT 10;
            """
            
            cursor.execute(sample_query, (distance_threshold_m,))
            samples = cursor.fetchall()
            
            if samples:
                print(f"\n📍 Sample points that would be deleted:")
                for i, (lat, lon, dist) in enumerate(samples):
                    print(f"  {i+1}. ({lat:.6f}, {lon:.6f}) | {dist:.1f}m from nearest panoid")
            
            return count
        
        else:
            # Actually delete the points
            delete_query = """
            DELETE FROM to_insert 
            WHERE EXISTS (
                SELECT 1 
                FROM panoids p 
                WHERE ST_DWithin(to_insert.geom::geography, p.geom::geography, %s)
            );
            """
            
            cursor.execute(delete_query, (distance_threshold_m,))
            deleted_count = cursor.rowcount
            
            conn.commit()
            
            print(f"✅ Deleted {deleted_count} points from to_insert within {distance_threshold_m}m of panoids")
            
            # Show remaining count
            cursor.execute("SELECT COUNT(*) FROM to_insert")
            remaining = cursor.fetchone()[0]
            print(f"📊 Remaining points in to_insert: {remaining}")
            
            return deleted_count
        
    except Exception as e:
        print(f"❌ Error deleting close points: {e}")
        if conn:
            conn.rollback()
        return 0
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_database_summary():
    """
    Get summary statistics of both tables
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
        
        print("📊 DATABASE SUMMARY")
        print("=" * 40)
        
        # Panoids table stats
        cursor.execute("SELECT COUNT(*) FROM panoids WHERE pano_id IS NOT NULL")
        panoids_with_id = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM panoids")
        total_panoids = cursor.fetchone()[0]
        
        print(f"Panoids table: {total_panoids:,} total ({panoids_with_id:,} with pano_id)")
        
        # To_insert table stats
        cursor.execute("SELECT COUNT(*) FROM to_insert")
        total_to_insert = cursor.fetchone()[0]
        
        print(f"To_insert table: {total_to_insert:,} points")
        
        # Check if geometry columns exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'panoids' AND column_name = 'geom'
        """)
        panoids_has_geom = cursor.fetchone()[0] > 0
        
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'to_insert' AND column_name = 'geom'
        """)
        to_insert_has_geom = cursor.fetchone()[0] > 0
        
        print(f"Geometry columns: panoids={panoids_has_geom}, to_insert={to_insert_has_geom}")
        
        if panoids_has_geom and to_insert_has_geom:
            # Check PostGIS extension
            cursor.execute("SELECT EXISTS(SELECT 1 FROM pg_extension WHERE extname = 'postgis')")
            has_postgis = cursor.fetchone()[0]
            print(f"PostGIS extension: {has_postgis}")
        
    except Exception as e:
        print(f"❌ Error getting database summary: {e}")
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def setup_spatial_columns():
    """
    Setup geometry columns and indexes for spatial operations
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
        
        print("🔧 Setting up spatial columns...")
        
        # Add geometry columns if they don't exist
        try:
            cursor.execute("ALTER TABLE panoids ADD COLUMN geom GEOMETRY(POINT, 4326)")
            print("✅ Added geom column to panoids table")
        except psycopg2.Error:
            print("ℹ️  Geom column already exists in panoids table")
            conn.rollback()
        
        try:
            cursor.execute("ALTER TABLE to_insert ADD COLUMN geom GEOMETRY(POINT, 4326)")
            print("✅ Added geom column to to_insert table")
        except psycopg2.Error:
            print("ℹ️  Geom column already exists in to_insert table")
            conn.rollback()
        
        # Update geometry columns
        print("🔄 Updating geometry columns...")
        
        cursor.execute("UPDATE panoids SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)")
        panoids_updated = cursor.rowcount
        
        cursor.execute("UPDATE to_insert SET geom = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)")
        to_insert_updated = cursor.rowcount
        
        # Create spatial indexes
        try:
            cursor.execute("CREATE INDEX idx_panoids_geom ON panoids USING GIST(geom)")
            print("✅ Created spatial index on panoids")
        except psycopg2.Error:
            print("ℹ️  Spatial index already exists on panoids")
            conn.rollback()
        
        try:
            cursor.execute("CREATE INDEX idx_to_insert_geom ON to_insert USING GIST(geom)")
            print("✅ Created spatial index on to_insert")
        except psycopg2.Error:
            print("ℹ️  Spatial index already exists on to_insert")
            conn.rollback()
        
        conn.commit()
        
        print(f"✅ Setup complete!")
        print(f"   - Updated {panoids_updated:,} panoids geometries")
        print(f"   - Updated {to_insert_updated:,} to_insert geometries")
        
    except Exception as e:
        print(f"❌ Error setting up spatial columns: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def visualize_panoids_and_to_insert_map():
    """
    Fetch all panoids and to_insert points from the database and visualize them on an interactive map
    - Panoids: Black dots
    - To_insert: Red dots with low opacity
    """
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
        
        # Fetch all records from panoids table
        cursor.execute("SELECT latitude, longitude, pano_id FROM panoids")
        panoids_records = cursor.fetchall()
        
        # Fetch all records from to_insert table
        cursor.execute("SELECT latitude, longitude FROM to_insert")
        to_insert_records = cursor.fetchall()
        
        if not panoids_records and not to_insert_records:
            print("No records found in either panoids or to_insert tables")
            return None
        
        print(f"Found {len(panoids_records)} panoids records")
        print(f"Found {len(to_insert_records)} to_insert records")
        
        # Calculate center point from all coordinates
        all_lats = []
        all_lons = []
        
        for record in panoids_records:
            all_lats.append(float(record[0]))
            all_lons.append(float(record[1]))
            
        for record in to_insert_records:
            all_lats.append(float(record[0]))
            all_lons.append(float(record[1]))
        
        if all_lats:
            avg_lat = sum(all_lats) / len(all_lats)
            avg_lon = sum(all_lons) / len(all_lons)
        else:
            # Fallback to Nancy center
            avg_lat = latcenter_nancy
            avg_lon = longcenter_nancy
        
        # Create map centered on average coordinates
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        # Add panoids as black dots
        for record in panoids_records:
            latitude, longitude, pano_id = record
            
            folium.CircleMarker(
                location=[float(latitude), float(longitude)],
                radius=4,
                popup=f"Panoid: {pano_id}<br>Coords: ({latitude:.6f}, {longitude:.6f})",
                tooltip=f"Panoid: {pano_id}",
                color='black',
                fillColor='black',
                fillOpacity=1.0,
                weight=1
            ).add_to(map_viz)
        
        # Add to_insert points as red dots with low opacity
        for i, record in enumerate(to_insert_records):
            latitude, longitude = record
            
            folium.CircleMarker(
                location=[float(latitude), float(longitude)],
                radius=3,
                popup=f"To Insert Point {i+1}<br>Coords: ({latitude:.6f}, {longitude:.6f})",
                tooltip=f"To Insert: ({latitude:.6f}, {longitude:.6f})",
                color='red',
                fillColor='red',
                fillOpacity=0.3,  # Low opacity
                weight=1,
                opacity=0.6  # Border opacity
            ).add_to(map_viz)
        
        # Add Nancy center and boundary circle (same as original)
        nancy_center = [latcenter_nancy, longcenter_nancy]
        nancy_radius = R_nancy * 111000  # Convert to meters approximately
        
        folium.Marker(
            location=nancy_center,
            popup="Nancy Center",
            icon=folium.Icon(color='blue', icon='star')
        ).add_to(map_viz)
        
        folium.Circle(
            location=nancy_center,
            radius=nancy_radius,
            color='blue',
            fill=True,
            fillOpacity=0.1,
        ).add_to(map_viz)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 200px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Legend</b></p>
        <p><span style="color:black;">●</span> Panoids (collected points)</p>
        <p><span style="color:red; opacity:0.6;">●</span> To Insert (planned points)</p>
        <p><span style="color:blue;">★</span> Nancy Center</p>
        <p>Total: {panoids} panoids, {to_insert} to insert</p>
        </div>
        '''.format(panoids=len(panoids_records), to_insert=len(to_insert_records))
        
        map_viz.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map to HTML file
        map_filename = "panoids_and_to_insert_map.html"
        map_viz.save(map_filename)
        print(f"Combined map saved as {map_filename}")
        print(f"Open the file in your web browser to view the interactive map")
        print(f"📊 Visualization shows:")
        print(f"   • {len(panoids_records)} panoids (black dots)")
        print(f"   • {len(to_insert_records)} to_insert points (red dots with low opacity)")
        
        return map_viz
        
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def visualize_overlapping_points(distance_threshold_m=10):
    """
    Create a special visualization highlighting overlapping points between panoids and to_insert
    
    Args:
        distance_threshold_m (float): Distance threshold in meters to consider points as overlapping
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
        
        # Find overlapping points
        overlap_query = """
        SELECT 
            p.latitude as panoid_lat,
            p.longitude as panoid_lon,
            p.pano_id,
            ti.latitude as to_insert_lat,
            ti.longitude as to_insert_lon,
            ST_Distance(p.geom::geography, ti.geom::geography) as distance_m
        FROM panoids p
        JOIN to_insert ti ON ST_DWithin(p.geom::geography, ti.geom::geography, %s)
        ORDER BY distance_m;
        """
        
        cursor.execute(overlap_query, (distance_threshold_m,))
        overlapping_points = cursor.fetchall()
        
        if not overlapping_points:
            print(f"No overlapping points found within {distance_threshold_m}m")
            return visualize_panoids_and_to_insert_map()  # Fall back to regular visualization
        
        print(f"Found {len(overlapping_points)} overlapping point pairs within {distance_threshold_m}m")
        
        # Get all points for context
        cursor.execute("SELECT latitude, longitude, pano_id FROM panoids")
        all_panoids = cursor.fetchall()
        
        cursor.execute("SELECT latitude, longitude FROM to_insert")
        all_to_insert = cursor.fetchall()
        
        # Calculate center
        avg_lat = sum(float(p[0]) for p in overlapping_points) / len(overlapping_points)
        avg_lon = sum(float(p[1]) for p in overlapping_points) / len(overlapping_points)
        
        # Create map
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=14,
            tiles='OpenStreetMap'
        )
        
        # Add all panoids (faded)
        for record in all_panoids:
            latitude, longitude, pano_id = record
            folium.CircleMarker(
                location=[float(latitude), float(longitude)],
                radius=2,
                color='black',
                fillColor='black',
                fillOpacity=0.3,
                weight=1,
                opacity=0.3
            ).add_to(map_viz)
        
        # Add all to_insert points (faded)
        for record in all_to_insert:
            latitude, longitude = record
            folium.CircleMarker(
                location=[float(latitude), float(longitude)],
                radius=2,
                color='red',
                fillColor='red',
                fillOpacity=0.1,
                weight=1,
                opacity=0.2
            ).add_to(map_viz)
        
        # Highlight overlapping points
        for overlap in overlapping_points:
            panoid_lat, panoid_lon, pano_id, to_insert_lat, to_insert_lon, distance = overlap
            
            # Highlight panoid
            folium.CircleMarker(
                location=[float(panoid_lat), float(panoid_lon)],
                radius=6,
                popup=f"OVERLAP: Panoid {pano_id}<br>Distance: {distance:.1f}m",
                color='yellow',
                fillColor='black',
                fillOpacity=1.0,
                weight=3
            ).add_to(map_viz)
            
            # Highlight to_insert point
            folium.CircleMarker(
                location=[float(to_insert_lat), float(to_insert_lon)],
                radius=6,
                popup=f"OVERLAP: To Insert<br>Distance: {distance:.1f}m",
                color='yellow',
                fillColor='red',
                fillOpacity=0.8,
                weight=3
            ).add_to(map_viz)
            
            # Draw line between overlapping points
            folium.PolyLine(
                locations=[[float(panoid_lat), float(panoid_lon)], 
                          [float(to_insert_lat), float(to_insert_lon)]],
                color='yellow',
                weight=2,
                opacity=0.8,
                popup=f"Distance: {distance:.1f}m"
            ).add_to(map_viz)
        
        # Add legend
        legend_html = f'''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 250px; height: 160px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px">
        <p><b>Overlapping Points Analysis</b></p>
        <p><span style="color:yellow; font-weight:bold;">●</span> Overlapping points (highlighted)</p>
        <p><span style="color:black; opacity:0.3;">●</span> Other panoids</p>
        <p><span style="color:red; opacity:0.1;">●</span> Other to_insert points</p>
        <p><span style="color:yellow;">—</span> Distance lines</p>
        <p><b>{len(overlapping_points)} overlaps within {distance_threshold_m}m</b></p>
        </div>
        '''
        
        map_viz.get_root().html.add_child(folium.Element(legend_html))
        
        # Save map
        map_filename = f"overlapping_points_{distance_threshold_m}m.html"
        map_viz.save(map_filename)
        print(f"Overlap analysis map saved as {map_filename}")
        
        return map_viz
        
    except Exception as e:
        print(f"Error creating overlap visualization: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if len(sys.argv) > 1 and sys.argv[1] == "--spatial":
            print("🗄️ Running spatial analysis...")
            
            # Setup spatial columns first
            setup_spatial_columns()
            
            # Get database summary
            get_database_summary()
            
            # Find nearest points (dry run)
            print(f"\n🔍 Finding nearest points...")
            nearest_points = find_nearest_points_to_panoids(distance_threshold_m=100)
            
            # Show what would be deleted (dry run)
            print(f"\n🗑️ Checking what would be deleted at 10m threshold...")
            delete_close_points_from_to_insert(distance_threshold_m=10, dry_run=True)
            
            # Ask user if they want to proceed with deletion
            if nearest_points:
                response = input(f"\nDo you want to delete points within 10m? (y/N): ")
                if response.lower() == 'y':
                    deleted = delete_close_points_from_to_insert(distance_threshold_m=10, dry_run=False)
                    print(f"✅ Deleted {deleted} points")
                else:
                    print("ℹ️  Deletion cancelled")
            
            exit()
    
        # Check for --park flag
        if sys.argv[1] == "--view":
            visualize_panoids_on_map()
        if sys.argv[1] == "--viewinsert":
            visualize_panoids_and_to_insert_map()
        # Check for --park flag 
        if sys.argv[1] == "--stats":
            get_database_summary()
        if sys.argv[1] == "--park":
            url_input = get_url_from_clipboard()
            print(f"Parking mode: parsing URL and downloading panoid")
            if url_input:
                print(f"Found URL in clipboard: {url_input[:80]}...")
            else:
                print("No valid URL found in clipboard.")
                
            # Parse the URL to extract panoid
            lat, lon, panoid = parse_google_maps_url(url_input)
            
            if panoid is None:
                print(f"❌ Could not extract panoid from URL: {url_input}")
                print("Make sure the URL is a valid Google Street View URL")
                exit(1)
            
            print(f"📍 Extracted panoid: {panoid} at location ({lat}, {lon})")
            
            # Run streetview downloader for single panoid with park output
            command = [
                "/home/arthur/Bureau/sviewscrap/StreetViewScraper/build/streetview_downloader",
                panoid,
                "-o", os.path.expanduser("~/street_view_park")
            ]
            
            try:
                print(f"Running command: {' '.join(command)}")
                result = subprocess.run(command, check=True, capture_output=True, text=True)
                print(f"✅ Successfully downloaded panoid {panoid} to ~/street_view_park")
                print(f"📍 Location: {lat}, {lon}")
                print(result.stdout)
            except subprocess.CalledProcessError as e:
                print(f"❌ Error downloading panoid {panoid}: {e}")
                print(f"stderr: {e.stderr}")
            except FileNotFoundError:
                print("❌ streetview_downloader executable not found. Check the path.")
            
            exit()
        else:
            # Normal command line argument (URL)
            url = sys.argv[1]
            print(f"Using URL from command line: {url}")
    else:
        url=None
        print("Usage:")
        print("  python auto_walkthrough.py <url>                    # Normal walkthrough")
        print("  python auto_walkthrough.py --park <panoid>          # Download single panoid")
        print("  python auto_walkthrough.py                          # Use clipboard URL")
        print("  python auto_walkthrough.py                          # Use random image among the one not done")
        print("  python auto_walkthrough.py --view                   # compute the html map")
    
    
    if url:
        print(f"Starting walkthrough from URL...")
        selenium_walkthrough(url)
        print("Walkthrough completed. Generating visualization...")
        visualize_panoids_on_map()
    else:
        print("No URL provided. Starting on a random point")
        selenium_walkthrough(None)
        visualize_panoids_on_map()
        

        
"""

required table structure 
-- Connect to your database
psql -h localhost -U arthur -d imagedb

-- Create panoids table (if not exists)
CREATE TABLE IF NOT EXISTS panoids (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    pano_id VARCHAR(255),
    geom GEOMETRY(POINT, 4326)
);

-- Your to_insert table should have:
-- (You mentioned you already have this)
CREATE TABLE IF NOT EXISTS to_insert (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    geom GEOMETRY(POINT, 4326)
);

"""