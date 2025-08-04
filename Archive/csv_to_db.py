import csv
import psycopg2

def copy_csv_to_insert_table(csv_file_path="nancy_road_points.csv"):
    """
    Copy all latitude and longitude from CSV file to the to_insert table
    
    Args:
        csv_file_path (str): Path to the CSV file (default: nancy_road_points.csv)
    
    Returns:
        int: Number of records inserted
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
        
        print(f"📖 Reading CSV file: {csv_file_path}")
        
        # Clear the to_insert table first (optional)
        cursor.execute("TRUNCATE TABLE to_insert")
        print("🗑️  Cleared existing data from to_insert table")
        
        inserted_count = 0
        
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            # Batch insert for better performance
            batch_data = []
            batch_size = 100
            
            for row in reader:
                try:
                    latitude = float(row['latitude'])
                    longitude = float(row['longitude'])
                    
                    batch_data.append((latitude, longitude))
                    
                    # Execute batch when it reaches batch_size
                    if len(batch_data) >= batch_size:
                        cursor.executemany(
                            "INSERT INTO to_insert (latitude, longitude) VALUES (%s, %s)",
                            batch_data
                        )
                        inserted_count += len(batch_data)
                        batch_data = []
                        
                        if inserted_count % 500 == 0:
                            print(f"✅ Inserted {inserted_count} records so far...")
                    
                except (ValueError, KeyError) as e:
                    print(f"❌ Error processing row: {e} - Row data: {row}")
                    continue
            
            # Insert remaining records in the last batch
            if batch_data:
                cursor.executemany(
                    "INSERT INTO to_insert (latitude, longitude) VALUES (%s, %s)",
                    batch_data
                )
                inserted_count += len(batch_data)
        
        # Commit all changes
        conn.commit()
        
        # Verify the insertion
        cursor.execute("SELECT COUNT(*) FROM to_insert")
        total_count = cursor.fetchone()[0]
        
        print(f"\n📊 COPY COMPLETE")
        print("-" * 30)
        print(f"✅ Successfully inserted {inserted_count} records")
        print(f"📋 Total records in to_insert table: {total_count}")
        
        # Show sample of inserted data
        print(f"\n📝 Sample data from to_insert table:")
        cursor.execute("SELECT latitude, longitude FROM to_insert LIMIT 5")
        samples = cursor.fetchall()
        for i, (lat, lon) in enumerate(samples, 1):
            print(f"  {i}. {lat:.6f}, {lon:.6f}")
        
        return inserted_count
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
        return 0
    
    except FileNotFoundError:
        print(f"❌ CSV file not found: {csv_file_path}")
        return 0
    
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
        return 0
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def copy_csv_coordinates_only():
    """
    Alternative function that only copies lat/lon columns from any CSV
    """
    return copy_csv_to_insert_table("nancy_road_points.csv")

def verify_insert_table():
    """
    Verify the contents of the to_insert table
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
        
        # Get table statistics
        cursor.execute("SELECT COUNT(*) FROM to_insert")
        total_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM to_insert")
        bounds = cursor.fetchone()
        min_lat, max_lat, min_lon, max_lon = bounds
        
        print(f"📊 TO_INSERT TABLE STATISTICS")
        print("-" * 35)
        print(f"Total records: {total_count:,}")
        print(f"Latitude range: {min_lat:.6f} to {max_lat:.6f}")
        print(f"Longitude range: {min_lon:.6f} to {max_lon:.6f}")
        
        # Show first few records
        print(f"\nFirst 10 records:")
        cursor.execute("SELECT latitude, longitude FROM to_insert LIMIT 10")
        records = cursor.fetchall()
        for i, (lat, lon) in enumerate(records, 1):
            print(f"  {i:2d}. {lat:.6f}, {lon:.6f}")
        
        return total_count
        
    except Exception as e:
        print(f"❌ Error verifying table: {e}")
        return 0
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# For use in map_image_download.py
if __name__ == "__main__":
    print("🚀 Starting CSV to database copy...")
    
    # Copy all coordinates from nancy_road_points.csv to to_insert table
    count = copy_csv_to_insert_table()
    
    if count > 0:
        print(f"\n🎉 Successfully copied {count} coordinate pairs!")
        
        # Verify the data
        print(f"\n🔍 Verifying inserted data...")
        verify_insert_table()
    else:
        print("❌ No data was copied")


# to use this file you need db with 
"""

CREATE TABLE IF NOT EXISTS to_insert (
    id SERIAL PRIMARY KEY,
    latitude DECIMAL(10, 8) NOT NULL,
    longitude DECIMAL(11, 8) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_to_insert_coords ON to_insert(latitude, longitude);

"""