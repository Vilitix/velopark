from ultralytics import YOLO
import torch

import os
import shutil
from pathlib import Path
import random

import os
import shutil
from pathlib import Path
import random

def organize_raw_data():
    """
    Organize scattered data from yolo_final into proper structure
    """
    base_dir = Path("/home/arthur/Bureau/velopark_waypoints/yolo_final")
    
    # Create organized directories
    raw_images_dir = base_dir / "raw_data" / "images"
    raw_labels_dir = base_dir / "raw_data" / "labels"
    raw_images_dir.mkdir(parents=True, exist_ok=True)
    raw_labels_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔄 Organizing scattered data...")
    
    # Collect all non-augmented files (without _aug_ in filename)
    image_files = []
    label_files = []
    
    # Search in all possible directories EXCEPT raw_data (to avoid copying to itself)
    search_dirs = [
        base_dir / "train",
        base_dir / "veloparkdataset",
        # base_dir,  # Remove this to avoid scanning raw_data subdirectory
    ]
    
    # Scan root directory files only (not subdirectories)
    for file_path in base_dir.iterdir():
        if file_path.is_file():
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png'] and "_aug_" not in file_path.name:
                image_files.append(file_path)
            elif file_path.suffix == '.txt' and "_aug_" not in file_path.name and file_path.name != "classes.txt":
                label_files.append(file_path)
    
    for search_dir in search_dirs:
        if search_dir.exists():
            # Find images
            for img_pattern in ['*.jpg', '*.jpeg', '*.png']:
                for img_file in search_dir.rglob(img_pattern):
                    if "_aug_" not in img_file.name:  # Only original files
                        image_files.append(img_file)
            
            # Find labels
            for label_file in search_dir.rglob('*.txt'):
                if "_aug_" not in label_file.name and label_file.name != "classes.txt":
                    label_files.append(label_file)
    
    # Remove duplicates
    image_files = list(set(image_files))
    label_files = list(set(label_files))
    
    print(f"📁 Found {len(image_files)} image files and {len(label_files)} label files")
    
    # Copy to organized structure
    copied_pairs = 0
    for img_file in image_files:
        # Find corresponding label
        label_name = f"{img_file.stem}.txt"
        matching_label = None
        
        for label_file in label_files:
            if label_file.name == label_name:
                matching_label = label_file
                break
        
        if matching_label:
            # Check if files are not already in the target location
            target_img = raw_images_dir / img_file.name
            target_label = raw_labels_dir / matching_label.name
            
            # Only copy if not already in target location
            if not target_img.exists() or target_img.resolve() != img_file.resolve():
                shutil.copy2(img_file, target_img)
                print(f"✅ Copied image: {img_file.name}")
            else:
                print(f"⚠️ Image already exists: {img_file.name}")
            
            if not target_label.exists() or target_label.resolve() != matching_label.resolve():
                shutil.copy2(matching_label, target_label)
                print(f"✅ Copied label: {matching_label.name}")
            else:
                print(f"⚠️ Label already exists: {matching_label.name}")
                
            copied_pairs += 1
    
    print(f"📊 Organized {copied_pairs} image-label pairs")
    return copied_pairs

def split_dataset(source_images, source_labels, output_dir, train_ratio=0.8):
    """
    Split dataset into train/val folders
    """
    output_dir = Path(output_dir)
    
    # Create directory structure
    for split in ['train', 'val']:
        (output_dir / 'images' / split).mkdir(parents=True, exist_ok=True)
        (output_dir / 'labels' / split).mkdir(parents=True, exist_ok=True)
    
    # Get all image files
    image_files = []
    for ext in ['*.jpg', '*.jpeg', '*.png']:
        image_files.extend(list(Path(source_images).glob(ext)))
    
    if not image_files:
        print(f"❌ No images found in {source_images}")
        return
    
    random.shuffle(image_files)
    train_count = int(len(image_files) * train_ratio)
    
    print(f"📊 Splitting {len(image_files)} files: {train_count} train, {len(image_files)-train_count} val")
    
    for i, img_file in enumerate(image_files):
        split = 'train' if i < train_count else 'val'
        
        # Copy image
        shutil.copy2(img_file, output_dir / 'images' / split / img_file.name)
        
        # Copy corresponding label
        label_file = Path(source_labels) / f"{img_file.stem}.txt"
        if label_file.exists():
            shutil.copy2(label_file, output_dir / 'labels' / split / label_file.name)
        else:
            print(f"⚠️ Warning: No label for {img_file.name}")




def train_bicycle_parking_detector():
    """
    Train YOLOv11m for bicycle parking detection
    """
    
    # Check if CUDA is available
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🔥 Using device: {device}")
    
    # Load YOLOv11m model
    model = YOLO('yolo11m.pt')  # Changed to small variant

    results = model.train(
        data='/home/arthur/Bureau/velopark_waypoints/yolo_final/veloparkdataset/data.yaml',
        epochs=150,              # Increased for small dataset
        imgsz=512,              
        batch=8,                # Reduced for better gradient estimates
        patience=10,            # Reduced for earlier overfitting detection
        save=True,              
        save_period=5,          # More frequent saves
        cache=True,             
        device=device,
        workers=4,              # Reduced to match smaller batch size
        project='velopark_training',
        name='yolo11s_bicycle_parking_optimized',
        
        # Optimized learning parameters
        optimizer='AdamW',      
        lr0=0.0005,             # Reduced learning rate
        lrf=0.001,              # Gentler decay
        momentum=0.937,
        weight_decay=0.001,     # Increased regularization
        warmup_epochs=5,        # Extended warmup
        warmup_momentum=0.9,    
        warmup_bias_lr=0.05,    
        
        # Reduced augmentation to prevent over-augmentation
        hsv_h=0.01,             
        hsv_s=0.5,              
        hsv_v=0.3,              
        degrees=0.0,            
        translate=0.05,         
        scale=0.3,              
        shear=0.0,              
        perspective=0.0,        
        flipud=0.0,             
        fliplr=0.5,             
        mosaic=0.8,             # Reduced intensity
        mixup=0.0,              
        copy_paste=0.0,         
        
        val=True,               
        plots=True,             
        verbose=True,           
    )

    
    print("✅ Training completed!")
    print(f"📁 Results saved in: {results.save_dir}")
    
    return model, results

if __name__ == "__main__":
    base_dir = "/home/arthur/Bureau/velopark_waypoints/yolo_final"
    print("🚀 Step 5: Starting training...")
    model, results = train_bicycle_parking_detector()