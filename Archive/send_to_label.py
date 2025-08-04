import os
import sys
import csv
import shutil
from pathlib import Path

def send_images_to_label(count=100):
    """
    Send the next batch of images to labeling folder based on current progress.
    
    Args:
        count (int): Number of images to process (default: 100)
    """
    
    # File paths
    nb_processed_file = Path("/home/arthur/Bureau/velopark_waypoints/nb_processed")
    rdorder_csv = Path("/home/arthur/Bureau/velopark_waypoints/rdorder.csv")
    source_dir = Path.home() / "street_view_images"
    dest_dir = Path.home() / "street_viewtolabel"
    
    # Check if required files exist
    if not nb_processed_file.exists():
        print(f"❌ nb_processed file not found: {nb_processed_file}")
        print("Creating nb_processed file with initial value 0")
        with open(nb_processed_file, 'w') as f:
            f.write('0')
        current_processed = 0
    else:
        # Read current processed count
        try:
            with open(nb_processed_file, 'r') as f:
                current_processed = int(f.read().strip())
        except ValueError:
            print("❌ Invalid number in nb_processed file, starting from 0")
            current_processed = 0
    
    if not rdorder_csv.exists():
        print(f"❌ rdorder.csv not found: {rdorder_csv}")
        print("Please run the file shuffling script first to generate rdorder.csv")
        return False
    
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return False
    
    # Create destination directory
    dest_dir.mkdir(exist_ok=True)
    print(f"📁 Destination directory: {dest_dir}")
    
    print(f"📊 Starting from line {current_processed + 1} in rdorder.csv")
    print(f"🎯 Processing {count} images")
    
    # Read CSV and extract filenames
    filenames_to_copy = []
    total_lines = 0
    
    try:
        with open(rdorder_csv, 'r', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            
            # Skip header
            next(reader, None)
            
            # Convert to list to count total lines
            all_rows = list(reader)
            total_lines = len(all_rows)
            
            # Check if we have enough remaining lines
            if current_processed >= total_lines:
                print(f"✅ All images have been processed! (Processed: {current_processed}, Total: {total_lines})")
                return True
            
            # Extract the required range
            end_index = min(current_processed + count, total_lines)
            
            for i in range(current_processed, end_index):
                if i < len(all_rows):
                    row = all_rows[i]
                    if row:  # Skip empty rows
                        filename = row[0].strip()
                        if filename:
                            filenames_to_copy.append(filename)
            
            print(f"📋 Found {len(filenames_to_copy)} filenames to process")
            print(f"📈 Will process lines {current_processed + 1} to {current_processed + len(filenames_to_copy)}")
            
    except Exception as e:
        print(f"❌ Error reading rdorder.csv: {e}")
        return False
    
    # Copy files
    stats = {
        'copied': 0,
        'not_found': 0,
        'already_exists': 0,
        'errors': 0
    }
    
    print(f"\n🔄 Starting file copy operation...")
    
    for i, filename in enumerate(filenames_to_copy):
        try:
            # Handle both direct filenames and relative paths
            if '/' in filename:
                # It's a relative path from street_view_images
                source_file = source_dir / filename
            else:
                # It's just a filename, search for it
                source_file = None
                # Try different image extensions
                for ext in ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']:
                    if filename.endswith(ext):
                        potential_file = source_dir / filename
                        if potential_file.exists():
                            source_file = potential_file
                            break
                    else:
                        # Try adding extension if not present
                        potential_file = source_dir / (filename + ext)
                        if potential_file.exists():
                            source_file = potential_file
                            filename = filename + ext  # Update filename for destination
                            break
                
                if source_file is None:
                    # Search recursively
                    for file_path in source_dir.rglob(filename):
                        if file_path.is_file():
                            source_file = file_path
                            break
            
            if source_file is None or not source_file.exists():
                print(f"   ❌ {filename}: File not found")
                stats['not_found'] += 1
                continue
            
            # Destination file path
            dest_file = dest_dir / source_file.name
            
            # Check if already exists
            if dest_file.exists():
                print(f"   ⚠️  {source_file.name}: Already exists, skipping")
                stats['already_exists'] += 1
                continue
            
            # Copy the file
            shutil.copy2(source_file, dest_file)
            stats['copied'] += 1
            
            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"   📊 Progress: {i + 1}/{len(filenames_to_copy)} files processed")
            
        except Exception as e:
            print(f"   ❌ Error copying {filename}: {e}")
            stats['errors'] += 1
    
    # Update nb_processed file
    new_processed_count = current_processed + len(filenames_to_copy)
    try:
        with open(nb_processed_file, 'w') as f:
            f.write(str(new_processed_count))
        print(f"✅ Updated nb_processed: {current_processed} → {new_processed_count}")
    except Exception as e:
        print(f"⚠️  Warning: Could not update nb_processed file: {e}")
    
    # Print summary
    print(f"\n📊 COPY OPERATION SUMMARY:")
    print(f"   ✅ Successfully copied: {stats['copied']}")
    print(f"   ❌ Files not found: {stats['not_found']}")
    print(f"   ⚠️  Already exists: {stats['already_exists']}")
    print(f"   ❌ Copy errors: {stats['errors']}")
    print(f"   📁 Total files in destination: {len(list(dest_dir.glob('*')))}")
    
    # Show remaining work
    remaining = total_lines - new_processed_count
    print(f"   📈 Progress: {new_processed_count}/{total_lines} ({(new_processed_count/total_lines*100):.1f}%)")
    print(f"   🔄 Remaining files: {remaining}")
    
    return stats['copied'] > 0

def show_status():
    """
    Show current processing status
    """
    nb_processed_file = Path("/home/arthur/Bureau/velopark_waypoints/nb_processed")
    rdorder_csv = Path("/home/arthur/Bureau/velopark_waypoints/rdorder.csv")
    dest_dir = Path.home() / "street_viewtolabel"
    
    # Get current processed count
    if nb_processed_file.exists():
        try:
            with open(nb_processed_file, 'r') as f:
                current_processed = int(f.read().strip())
        except ValueError:
            current_processed = 0
    else:
        current_processed = 0
    
    # Get total count from CSV
    total_lines = 0
    if rdorder_csv.exists():
        try:
            with open(rdorder_csv, 'r', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                next(reader, None)  # Skip header
                total_lines = sum(1 for _ in reader)
        except Exception:
            total_lines = 0
    
    # Count files in destination
    files_in_dest = len(list(dest_dir.glob('*'))) if dest_dir.exists() else 0
    
    print(f"📊 PROCESSING STATUS:")
    print(f"   📈 Processed from CSV: {current_processed}/{total_lines}")
    if total_lines > 0:
        print(f"   📊 Progress: {(current_processed/total_lines*100):.1f}%")
    print(f"   📁 Files in labeling folder: {files_in_dest}")
    print(f"   🔄 Remaining to process: {max(0, total_lines - current_processed)}")

def reset_progress():
    """
    Reset the progress counter to 0
    """
    nb_processed_file = Path("/home/arthur/Bureau/velopark_waypoints/nb_processed")
    
    try:
        with open(nb_processed_file, 'w') as f:
            f.write('0')
        print("✅ Progress reset to 0")
    except Exception as e:
        print(f"❌ Error resetting progress: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("📋 Usage:")
        print("   python send_to_label.py <count>     - Send next <count> images to labeling")
        print("   python send_to_label.py --status    - Show current status")
        print("   python send_to_label.py --reset     - Reset progress counter")
        print("\nExample:")
        print("   python send_to_label.py 100")
        sys.exit(1)
    
    if sys.argv[1] == "--status":
        show_status()
    elif sys.argv[1] == "--reset":
        reset_progress()
    else:
        try:
            count = int(sys.argv[1])
            if count <= 0:
                print("❌ Count must be a positive number")
                sys.exit(1)
            
            print(f"🚀 Sending {count} images to labeling folder...")
            success = send_images_to_label(count)
            
            if success:
                print("✅ Operation completed successfully!")
            else:
                print("❌ Operation failed!")
                
        except ValueError:
            print("❌ Invalid number provided")
            sys.exit(1)