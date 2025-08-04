import os
import random
import csv
from pathlib import Path

def create_shuffled_file_list():
    """
    Get all file names from ~/street_view_images directory, shuffle them,
    and write the result to rdorder.csv
    """
    
    # Define the directories
    street_view_dir = Path.home() / "street_view_images"
    output_file = Path("/home/arthur/Bureau/velopark_waypoints/rdorder.csv")
    
    print(f"📂 Scanning directory: {street_view_dir}")
    
    # Check if directory exists
    if not street_view_dir.exists():
        print(f"❌ Directory does not exist: {street_view_dir}")
        return False
    
    # Get all files from the directory
    all_files = []
    
    # Common image extensions to look for
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    try:
        for file_path in street_view_dir.rglob('*'):
            if file_path.is_file():
                # Check if it's an image file
                if any(file_path.name.endswith(ext) for ext in image_extensions):
                    all_files.append(file_path.name)
        
        if not all_files:
            print(f"❌ No image files found in {street_view_dir}")
            return False
        
        print(f"📊 Found {len(all_files)} image files")
        
        # Shuffle the list
        random.shuffle(all_files)
        print(f"🔀 Files shuffled randomly")
        
        # Write to CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['filename'])
            
            # Write each filename
            for filename in all_files:
                writer.writerow([filename])
        
        print(f"✅ Successfully wrote {len(all_files)} filenames to {output_file}")
        print(f"📁 Output file: {output_file.absolute()}")
        
        # Show first few examples
        print(f"\n📝 First 5 shuffled files:")
        for i, filename in enumerate(all_files[:5]):
            print(f"  {i+1}. {filename}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing files: {e}")
        return False

def create_shuffled_file_list_with_paths():
    """
    Alternative version that includes relative paths from street_view_images
    """
    
    street_view_dir = Path.home() / "street_view_images"
    output_file = Path("/home/arthur/Bureau/velopark_waypoints/rdorder.csv")
    
    print(f"📂 Scanning directory: {street_view_dir}")
    
    if not street_view_dir.exists():
        print(f"❌ Directory does not exist: {street_view_dir}")
        return False
    
    all_files = []
    image_extensions = ['.jpg', '.jpeg', '.png', '.JPG', '.JPEG', '.PNG']
    
    try:
        # Walk through all subdirectories
        for file_path in street_view_dir.rglob('*'):
            if file_path.is_file() and any(file_path.name.endswith(ext) for ext in image_extensions):
                # Get relative path from street_view_images directory
                relative_path = file_path.relative_to(street_view_dir)
                all_files.append(str(relative_path))
        
        if not all_files:
            print(f"❌ No image files found in {street_view_dir}")
            return False
        
        print(f"📊 Found {len(all_files)} image files")
        
        # Shuffle the list
        random.shuffle(all_files)
        print(f"🔀 Files shuffled randomly")
        
        # Write to CSV file
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['relative_path'])
            
            # Write each relative path
            for filepath in all_files:
                writer.writerow([filepath])
        
        print(f"✅ Successfully wrote {len(all_files)} file paths to {output_file}")
        print(f"📁 Output file: {output_file.absolute()}")
        
        # Show first few examples
        print(f"\n📝 First 5 shuffled files:")
        for i, filepath in enumerate(all_files[:5]):
            print(f"  {i+1}. {filepath}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing files: {e}")
        return False

def analyze_street_view_directory():
    """
    Analyze the structure of the street_view_images directory
    """
    street_view_dir = Path.home() / "street_view_images"
    
    if not street_view_dir.exists():
        print(f"❌ Directory does not exist: {street_view_dir}")
        return
    
    print(f"📂 Analyzing: {street_view_dir}")
    print("=" * 50)
    
    # Count files by extension
    extension_counts = {}
    total_files = 0
    subdirs = set()
    
    for file_path in street_view_dir.rglob('*'):
        if file_path.is_file():
            total_files += 1
            ext = file_path.suffix.lower()
            extension_counts[ext] = extension_counts.get(ext, 0) + 1
            
            # Track subdirectories
            if file_path.parent != street_view_dir:
                subdirs.add(file_path.parent.relative_to(street_view_dir))
    
    print(f"📊 Total files: {total_files}")
    print(f"📁 Subdirectories: {len(subdirs)}")
    
    if subdirs:
        print(f"   Subdirectories found: {sorted(subdirs)}")
    
    print(f"\n📋 File extensions:")
    for ext, count in sorted(extension_counts.items()):
        print(f"   {ext or '(no extension)'}: {count} files")
    
    # Show image files specifically
    image_extensions = ['.jpg', '.jpeg', '.png']
    image_count = sum(extension_counts.get(ext, 0) for ext in image_extensions)
    print(f"\n🖼️  Total image files: {image_count}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--analyze":
            analyze_street_view_directory()
        elif sys.argv[1] == "--with-paths":
            create_shuffled_file_list_with_paths()
        else:
            print("Usage: python order_imagesprelabel.py [--analyze|--with-paths]")
    else:
        # Default: create shuffled file list with just filenames
        create_shuffled_file_list()