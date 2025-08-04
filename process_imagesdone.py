import os
import json
import sqlite3
from pathlib import Path
import psycopg2
from ultralytics import YOLO
import cv2

def process_street_view_images():
    """
    Process all images from ~/street_view_images using AI.pt model.
    Saves progress and resumes from where it left off.
    Inserts bicycle parking locations into velopark table.
    """
    
    # Configuration
    images_dir = Path.home() / "street_view_images"
    progress_file = Path("/home/arthur/Bureau/velopark_waypoints/processing_progress.json")
    model_path = "/home/arthur/Bureau/velopark_waypoints/best1400images.pt"
    confidence_threshold = 0.5
    
    # Initialize progress tracking
    progress = load_progress(progress_file)
    
    # Load AI model
    print("🤖 Loading AI model...")
    try:
        model = YOLO(model_path, verbose=False)
        print("✅ AI model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load AI model: {e}")
        return
    
    # Get all image files
    image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']
    all_images = []
    
    for ext in image_extensions:
        all_images.extend(list(images_dir.rglob(ext)))
    
    # Sort for consistent processing order
    all_images.sort()
    
    if not all_images:
        print(f"❌ No images found in {images_dir}")
        return
    
    print(f"📸 Found {len(all_images)} images to process")
    
    # Filter out already processed images
    processed_images = set(progress.get('processed_images', []))
    remaining_images = [img for img in all_images if str(img) not in processed_images]
    
    print(f"📊 Already processed: {len(processed_images)}")
    print(f"🔄 Remaining to process: {len(remaining_images)}")
    
    if not remaining_images:
        print("✅ All images have been processed!")
        return
    
    # Connect to database
    conn, cursor = connect_to_database()
    if not conn:
        return
    
    # Process remaining images
    detected_count = 0
    error_count = 0
    
    try:
        for i, image_path in enumerate(remaining_images):
            try:
                #print(f"\n🔍 Processing {i+1}/{len(remaining_images)}: {image_path.name}")
                
                # Extract panoid from filename
                panoid = extract_panoid_from_filename(image_path.name)
                if not panoid:
                    print(f"⚠️  Could not extract panoid from filename: {image_path.name}")
                    mark_as_processed(progress, str(image_path), progress_file)
                    continue
                
                # Run AI detection
                results = model(str(image_path), verbose = False)
                result = results[0]
                
                # Check for bicycle parking detections
                has_velo_parking = False
                max_confidence = 0.0
                detection_count = 0
                
                if result.boxes is not None and len(result.boxes) > 0:
                    for box in result.boxes:
                        confidence = float(box.conf[0])
                        if confidence >= confidence_threshold:
                            has_velo_parking = True
                            detection_count += 1
                            if confidence > max_confidence:
                                max_confidence = confidence
                
                if has_velo_parking:
                    #print(f"✅ Bicycle parking detected! Confidence: {max_confidence:.2f}, Count: {detection_count}")
                    
                    # Get coordinates from panoids table
                    latitude, longitude = get_coordinates_from_panoid(cursor, panoid)
                    
                    if latitude is not None and longitude is not None:
                        # Insert into velopark table
                        success = insert_velopark_location(cursor, conn, latitude, longitude, panoid, max_confidence, detection_count)
                        if success:
                            detected_count += 1
                            print(f"📍 Saved to velopark table: ({latitude:.6f}, {longitude:.6f})")
                        else:
                            print(f"⚠️  Failed to save to velopark table")
                    else:
                        print(f"⚠️  Could not find coordinates for panoid: {panoid}")
                #else:
                    #print(f"❌ No bicycle parking detected")
                
                # Mark as processed
                mark_as_processed(progress, str(image_path), progress_file)
                
                # Progress update every 50 images
                if (i + 1) % 50 == 0:
                    print(f"\n📊 Progress: {i+1}/{len(remaining_images)} processed")
                    print(f"🎯 Bicycle parking found: {detected_count}")
                    print(f"❌ Errors: {error_count}")
                
            except Exception as e:
                print(f"❌ Error processing {image_path.name}: {e}")
                error_count += 1
                # Still mark as processed to avoid getting stuck
                mark_as_processed(progress, str(image_path), progress_file)
                continue
    
    except KeyboardInterrupt:
        print(f"\n⏹️  Processing interrupted by user")
        print(f"📊 Progress saved. Processed {i+1} additional images")
    
    finally:
        cursor.close()
        conn.close()
        
        print(f"\n🎉 Processing session complete!")
        print(f"📸 Total images processed this session: {i+1 if 'i' in locals() else 0}")
        print(f"🎯 Bicycle parking locations found: {detected_count}")
        print(f"❌ Errors encountered: {error_count}")

def load_progress(progress_file):
    """Load processing progress from JSON file"""
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️  Could not load progress file: {e}")
    
    return {'processed_images': [], 'last_session': None}

def mark_as_processed(progress, image_path, progress_file):
    """Mark an image as processed and save progress"""
    progress['processed_images'].append(image_path)
    progress['last_session'] = str(Path(image_path).name)
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress, f, indent=2)
    except Exception as e:
        print(f"⚠️  Could not save progress: {e}")

def extract_panoid_from_filename(filename):
    """Extract panoid from image filename"""
    # Assuming filename format like: panoid_View1_N_FOV90.0.jpg
    # Adjust this regex based on your actual filename format
    import re
    
    # Try different patterns based on your streetview downloader output
    patterns = [
        r'^(.+?)_View',  # Everything before _View
    ]
    
    for pattern in patterns:
        match = re.match(pattern, filename)
        if match:
            return match.group(1)
    
    # If no pattern matches, try the whole filename without extension
    return Path(filename).stem.split('_')[0]

def connect_to_database():
    """Connect to PostgreSQL database"""
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        cursor = conn.cursor()
        return conn, cursor
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return None, None


def get_coordinates_from_panoid(cursor, panoid):
    """Get latitude and longitude from panoids table using panoid"""
    try:
        cursor.execute(
            "SELECT latitude, longitude FROM panoids WHERE pano_id = %s",
            (panoid,)
        )
        result = cursor.fetchone()
        
        if result:
            return result[0], result[1]  # latitude, longitude
        else:
            return None, None
            
    except Exception as e:
        print(f"❌ Error querying panoids table: {e}")
        return None, None

def insert_velopark_location(cursor, conn, latitude, longitude, panoid, confidence, detection_count):
    """Insert bicycle parking location into velopark table"""
    try:
        cursor.execute("""
            INSERT INTO velopark (latitude, longitude, panoid)
            VALUES (%s, %s, %s)
        """, (latitude, longitude, panoid))
        
        conn.commit()
        return True
        
    except Exception as e:
        print(f"❌ Error inserting velopark location: {e}")
        conn.rollback()
        return False

def reset_progress():
    """Reset processing progress (useful for restarting from beginning)"""
    progress_file = Path("/home/arthur/Bureau/velopark_waypoints/processing_progress.json")
    if progress_file.exists():
        progress_file.unlink()
        print("✅ Progress reset. Next run will start from the beginning.")
    else:
        print("ℹ️  No progress file found.")

def show_processing_stats():
    """Show current processing statistics"""
    conn, cursor = connect_to_database()
    if not conn:
        return
    
    try:
        # Get velopark count
        cursor.execute("SELECT COUNT(*) FROM velopark")
        velopark_count = cursor.fetchone()[0]
        
        # Get panoids count
        cursor.execute("SELECT COUNT(*) FROM panoids")
        panoids_count = cursor.fetchone()[0]
        
        # Get progress info
        progress_file = Path("/home/arthur/Bureau/velopark_waypoints/processing_progress.json")
        progress = load_progress(progress_file)
        processed_count = len(progress.get('processed_images', []))
        
        print(f"📊 PROCESSING STATISTICS")
        print(f"=" * 40)
        print(f"Images processed: {processed_count}")
        print(f"Bicycle parking found: {velopark_count}")
        print(f"Total panoids in database: {panoids_count}")
        print(f"Detection rate: {(velopark_count/processed_count*100):.1f}%" if processed_count > 0 else "N/A")
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--reset":
            reset_progress()
        elif sys.argv[1] == "--stats":
            show_processing_stats()
        else:
            print("Usage: python process_imagesdone.py [--reset|--stats]")
    else:
        process_street_view_images()



#db necessary 

"""

-- Connect to your database
psql -h localhost -U arthur -d imagedb

-- Create velopark table with unique panoid constraint
CREATE TABLE IF NOT EXISTS velopark (
    id SERIAL PRIMARY KEY,
    name TEXT,
    description TEXT,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL,
    panoid VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for better performance
CREATE INDEX IF NOT EXISTS idx_velopark_panoid ON velopark(panoid);
CREATE INDEX IF NOT EXISTS idx_velopark_coords ON velopark(latitude, longitude);

"""