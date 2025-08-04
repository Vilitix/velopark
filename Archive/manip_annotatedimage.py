import csv
import os

def extract_tagged_image_filenames(input_csv='imagevelo.csv', output_csv='tagged_images.csv'):
    """
    Extract filenames from image paths for rows with non-empty tag columns
    
    Args:
        input_csv (str): Path to input CSV file
        output_csv (str): Path to output CSV file
    
    Returns:
        int: Number of rows processed
    """
    try:
        processed_count = 0
        
        with open(input_csv, 'r', encoding='utf-8') as infile:
            # Read the CSV
            reader = csv.DictReader(infile)
            
            # Check if required columns exist
            if 'tag' not in reader.fieldnames:
                print("❌ 'tag' column not found in CSV")
                return 0
            
            if 'image' not in reader.fieldnames:
                print("❌ 'image' column not found in CSV")
                return 0
            
            # Collect rows with non-empty tags
            tagged_rows = []
            
            for row in reader:
                tag_value = row.get('tag', '').strip()
                image_value = row.get('image', '').strip()
                
                # Check if tag is not empty
                if tag_value and image_value:
                    # Extract filename from image path
                    # Example: "/data/local-files/?d=street_view_images/00-vfNxEOHw-tVbu51OmgA_View1_N_FOV90.0.jpg"
                    # Result: "00-vfNxEOHw-tVbu51OmgA_View1_N_FOV90.0.jpg"
                    filename = image_value.split('/')[-1]
                    
                    tagged_rows.append({
                        'filename': filename,
                        'tag': tag_value,
                        'original_image_path': image_value
                    })
                    processed_count += 1
        
        # Write to output CSV
        if tagged_rows:
            with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
                fieldnames = ['filename', 'tag', 'original_image_path']
                writer = csv.DictWriter(outfile, fieldnames=fieldnames)
                
                # Write header
                writer.writeheader()
                
                # Write data
                writer.writerows(tagged_rows)
            
            print(f"✅ Successfully processed {processed_count} tagged images")
            print(f"📁 Output saved to: {output_csv}")
            
            # Show sample of results
            if processed_count > 0:
                print(f"\n📋 Sample results (first 5):")
                for i, row in enumerate(tagged_rows[:5]):
                    print(f"   {i+1}. {row['filename']} (tag: {row['tag']})")
                if processed_count > 5:
                    print(f"   ... and {processed_count - 5} more")
        else:
            print("⚠️ No rows found with non-empty tags")
        
        return processed_count
        
    except FileNotFoundError:
        print(f"❌ File not found: {input_csv}")
        return 0
    except Exception as e:
        print(f"❌ Error processing CSV: {e}")
        return 0

def extract_filenames_only(input_csv='imagevelo.csv', output_csv='filenames_only.csv'):
    """
    Extract only filenames (without tag info) to a simple CSV
    
    Args:
        input_csv (str): Path to input CSV file
        output_csv (str): Path to output CSV file with just filenames
    
    Returns:
        int: Number of filenames extracted
    """
    try:
        filenames = []
        
        with open(input_csv, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            
            for row in reader:
                tag_value = row.get('tag', '').strip()
                image_value = row.get('image', '').strip()
                
                if tag_value and image_value:
                    filename = image_value.split('/')[-1]
                    filenames.append(filename)
        
        # Write simple CSV with just filenames
        with open(output_csv, 'w', newline='', encoding='utf-8') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['filename'])  # Header
            
            for filename in filenames:
                writer.writerow([filename])
        
        print(f"✅ Extracted {len(filenames)} filenames to {output_csv}")
        return len(filenames)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

import csv
import os
import shutil
from pathlib import Path

def move_tagged_images(tagged_csv='tagged_images.csv', 
                      source_dir='/home/arthur/streetview_output', 
                      dest_dir='/home/arthur/streetview_newoutput'):
    """
    Move image files listed in tagged_images.csv from source to destination directory
    
    Args:
        tagged_csv (str): Path to CSV file containing filename column
        source_dir (str): Source directory path
        dest_dir (str): Destination directory path
    
    Returns:
        dict: Statistics about the move operation
    """
    
    # Create destination directory if it doesn't exist
    dest_path = Path(dest_dir)
    dest_path.mkdir(parents=True, exist_ok=True)
    print(f"📁 Destination directory: {dest_dir}")
    
    # Statistics tracking
    stats = {
        'total_files': 0,
        'moved_successfully': 0,
        'file_not_found': 0,
        'move_errors': 0,
        'already_exists': 0
    }
    
    try:
        with open(tagged_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            # Check if filename column exists
            if 'filename' not in reader.fieldnames:
                print("❌ 'filename' column not found in CSV")
                return stats
            
            print(f"📋 Processing files from {tagged_csv}...")
            
            for row_num, row in enumerate(reader, 1):
                filename = row.get('filename', '').strip()
                
                if not filename:
                    print(f"   ⚠️  Row {row_num}: Empty filename, skipping")
                    continue
                
                stats['total_files'] += 1
                
                # Full paths
                source_file = Path(source_dir) / filename
                dest_file = Path(dest_dir) / filename
                
                try:
                    # Check if source file exists
                    if not source_file.exists():
                        print(f"   ❌ {filename}: Source file not found")
                        stats['file_not_found'] += 1
                        continue
                    
                    # Check if destination file already exists
                    if dest_file.exists():
                        print(f"   ⚠️  {filename}: Already exists in destination, skipping")
                        stats['already_exists'] += 1
                        continue
                    
                    # Move the file
                    shutil.move(str(source_file), str(dest_file))
                    print(f"   ✅ {filename}: Moved successfully")
                    stats['moved_successfully'] += 1
                    
                except Exception as e:
                    print(f"   ❌ {filename}: Move failed - {e}")
                    stats['move_errors'] += 1
    
    except FileNotFoundError:
        print(f"❌ CSV file not found: {tagged_csv}")
        return stats
    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        return stats
    
    # Print summary
    print(f"\n📊 MOVE OPERATION SUMMARY:")
    print(f"   📁 Total files processed: {stats['total_files']}")
    print(f"   ✅ Successfully moved: {stats['moved_successfully']}")
    print(f"   ❌ File not found: {stats['file_not_found']}")
    print(f"   ⚠️  Already exists: {stats['already_exists']}")
    print(f"   ❌ Move errors: {stats['move_errors']}")
    
    return stats

def move_tagged_images_with_subprocess(tagged_csv='tagged_images.csv', 
                                     source_dir='/home/arthur/streetview_output', 
                                     dest_dir='/home/arthur/streetview_newoutput'):
    """
    Alternative version using subprocess to run mv commands
    """
    import subprocess
    
    # Create destination directory
    os.makedirs(dest_dir, exist_ok=True)
    
    stats = {'total': 0, 'success': 0, 'failed': 0}
    
    try:
        with open(tagged_csv, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                filename = row.get('filename', '').strip()
                if not filename:
                    continue
                
                stats['total'] += 1
                source_path = f"{source_dir}/{filename}"
                dest_path = f"{dest_dir}/{filename}"
                
                try:
                    # Run mv command
                    result = subprocess.run(['mv', source_path, dest_path], 
                                          capture_output=True, text=True, check=True)
                    print(f"✅ Moved: {filename}")
                    stats['success'] += 1
                    
                except subprocess.CalledProcessError as e:
                    print(f"❌ Failed to move {filename}: {e.stderr.strip()}")
                    stats['failed'] += 1
                except Exception as e:
                    print(f"❌ Error with {filename}: {e}")
                    stats['failed'] += 1
    
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print(f"\n📊 Summary: {stats['success']}/{stats['total']} files moved successfully")
    return stats

# Usage examples

if __name__ == "__main__":
    # Method 1: Using Python's shutil (recommended)
    print("🚀 Moving tagged images using shutil...")
    move_tagged_images('tagged_images.csv')
    
    print("\n" + "="*50 + "\n")
    
    # Method 2: Using subprocess mv command
    print("🚀 Alternative: Moving using subprocess mv...")
    # move_tagged_images_with_subprocess('tagged_images.csv')

def quick_extract_panoids(input_csv='tagged_images.csv', output_csv='panoids.csv'):
    """
    Quick and simple version
    """
    try:
        panoids = []
        
        with open(input_csv, 'r') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                filename = row.get('filename', '')
                if filename and '_' in filename:
                    panoid = filename.split('_View')[0]
                    if panoid not in panoids:  # Avoid duplicates
                        panoids.append(panoid)
        
        with open(output_csv, 'w', newline='') as outfile:
            writer = csv.writer(outfile)
            writer.writerow(['panoid'])
            for panoid in panoids:
                writer.writerow([panoid])
        
        print(f"✅ Extracted {len(panoids)} unique panoids")
        return len(panoids)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

