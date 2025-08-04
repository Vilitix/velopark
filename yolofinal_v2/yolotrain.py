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



def organize_raw_data():
    """
    Organize scattered data from yolo_final into proper structure
    Including both original and augmented data
    """
    base_dir = Path("/home/arthur/Bureau/velopark_waypoints/yolofinal_v2")
    
    # Create organized directories
    raw_images_dir = base_dir / "raw_data" / "images"
    raw_labels_dir = base_dir / "raw_data" / "labels"
    raw_images_dir.mkdir(parents=True, exist_ok=True)
    raw_labels_dir.mkdir(parents=True, exist_ok=True)
    
    print("🔄 Organizing scattered data (including augmented)...")
    
    # Collect ALL files (original AND augmented)
    image_files = []
    label_files = []
    
    # Search in all possible directories EXCEPT raw_data (to avoid copying to itself)
    search_dirs = [
        base_dir / "1000photos",
        base_dir / "augmented_dataset",
        base_dir / "initial_image_dataset",  # Add this if you have it
        # Add any other directories with your data
    ]
    
    # Scan root directory files only (not subdirectories)
    for file_path in base_dir.iterdir():
        if file_path.is_file():
            if file_path.suffix.lower() in ['.jpg', '.jpeg', '.png']:
                image_files.append(file_path)
            elif file_path.suffix == '.txt' and file_path.name != "classes.txt":
                label_files.append(file_path)
    
    for search_dir in search_dirs:
        if search_dir.exists():
            print(f"🔍 Scanning: {search_dir}")
            
            # Find images (including augmented ones)
            for img_pattern in ['*.jpg', '*.jpeg', '*.png']:
                for img_file in search_dir.rglob(img_pattern):
                    image_files.append(img_file)
            
            # Find labels (including augmented ones)
            for label_file in search_dir.rglob('*.txt'):
                if label_file.name != "classes.txt":
                    label_files.append(label_file)
    
    # Remove duplicates
    image_files = list(set(image_files))
    label_files = list(set(label_files))
    
    # Separate original and augmented files for reporting
    original_images = [f for f in image_files if "_aug_" not in f.name]
    augmented_images = [f for f in image_files if "_aug_" in f.name]
    original_labels = [f for f in label_files if "_aug_" not in f.name]
    augmented_labels = [f for f in label_files if "_aug_" in f.name]
    
    print(f"📁 Found {len(original_images)} original images and {len(augmented_images)} augmented images")
    print(f"📋 Found {len(original_labels)} original labels and {len(augmented_labels)} augmented labels")
    print(f"📊 Total: {len(image_files)} images and {len(label_files)} labels")
    
    # Copy to organized structure
    copied_pairs = 0
    orphaned_images = 0
    orphaned_labels = 0
    
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
                if "_aug_" in img_file.name:
                    print(f"✅ Copied augmented image: {img_file.name}")
                else:
                    print(f"✅ Copied original image: {img_file.name}")
            
            if not target_label.exists() or target_label.resolve() != matching_label.resolve():
                shutil.copy2(matching_label, target_label)
                if "_aug_" in matching_label.name:
                    print(f"✅ Copied augmented label: {matching_label.name}")
                else:
                    print(f"✅ Copied original label: {matching_label.name}")
                
            copied_pairs += 1
        else:
            print(f"⚠️ No matching label for image: {img_file.name}")
            orphaned_images += 1
    
    # Check for orphaned labels
    used_labels = set()
    for img_file in image_files:
        label_name = f"{img_file.stem}.txt"
        for label_file in label_files:
            if label_file.name == label_name:
                used_labels.add(label_file)
                break
    
    orphaned_labels = len(label_files) - len(used_labels)
    
    print(f"📊 Final statistics:")
    print(f"   ✅ Organized {copied_pairs} image-label pairs")
    print(f"   📷 Original pairs: {len(original_images)} images")
    print(f"   🔄 Augmented pairs: {len(augmented_images)} images")
    print(f"   ⚠️ Orphaned images: {orphaned_images}")
    print(f"   ⚠️ Orphaned labels: {orphaned_labels}")
    
    return copied_pairs

def create_data_yaml(dataset_dir, class_names=['bicycle_parking']):
    """
    Create data.yaml file for YOLO training
    """
    dataset_dir = Path(dataset_dir)
    data_yaml_path = dataset_dir / "data.yaml"
    
    yaml_content = f"""# Bicycle Parking Detection Dataset
# Generated automatically

# Dataset paths
path: {dataset_dir.absolute()}  # dataset root dir
train: images/train  # train images (relative to 'path')
val: images/val  # val images (relative to 'path')

# Classes
nc: {len(class_names)}  # number of classes
names: {class_names}  # class names
"""
    
    with open(data_yaml_path, 'w') as f:
        f.write(yaml_content)
    
    print(f"✅ Created data.yaml at: {data_yaml_path}")
    return data_yaml_path

def complete_dataset_preparation():
    """
    Complete pipeline: organize data, split dataset, and create data.yaml
    """
    base_dir = Path("/home/arthur/Bureau/velopark_waypoints/yolofinal_v2")
    
    print("🚀 Starting complete dataset preparation...")
    
    # Step 1: Organize all data (original + augmented)
    print("\n📦 Step 1: Organizing raw data...")
    organize_raw_data()
    
    # Step 2: Split into train/val
    print("\n📊 Step 2: Splitting dataset...")
    raw_images_dir = base_dir / "raw_data" / "images"
    raw_labels_dir = base_dir / "raw_data" / "labels"
    final_dataset_dir = base_dir / "final_dataset"
    
    split_dataset(
        source_images=raw_images_dir,
        source_labels=raw_labels_dir,
        output_dir=final_dataset_dir,
        train_ratio=0.8
    )
    
    # Step 3: Create data.yaml
    print("\n📝 Step 3: Creating data.yaml...")
    data_yaml_path = create_data_yaml(final_dataset_dir)
    
    # Step 4: Show final statistics
    print("\n📊 Final Dataset Statistics:")
    train_images = len(list((final_dataset_dir / "images" / "train").glob("*")))
    val_images = len(list((final_dataset_dir / "images" / "val").glob("*")))
    train_labels = len(list((final_dataset_dir / "labels" / "train").glob("*")))
    val_labels = len(list((final_dataset_dir / "labels" / "val").glob("*")))
    
    print(f"   🏋️ Training: {train_images} images, {train_labels} labels")
    print(f"   ✅ Validation: {val_images} images, {val_labels} labels")
    print(f"   📄 Data config: {data_yaml_path}")
    
    return final_dataset_dir, data_yaml_path

def train_bicycle_parking_detector():
    """
    Train YOLOv11m for bicycle parking detection using prepared dataset
    """
    
    # Check if CUDA is available
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    print(f"🔥 Using device: {device}")
    
    # Load YOLOv11m model
    model = YOLO('yolo11m.pt')
    
    # Use the prepared dataset
    data_yaml_path = "/home/arthur/Bureau/velopark_waypoints/yolofinal_v2/final_dataset/data.yaml"
    
    if not Path(data_yaml_path).exists():
        print("❌ data.yaml not found. Running dataset preparation first...")
        complete_dataset_preparation()
    
    results = model.train(
        data=data_yaml_path,
        epochs=200,              
        imgsz=512,              
        batch=16,                
        patience=25,            # Increased patience for larger dataset
        save=True,              
        save_period=10,         
        cache=True,             
        device=device,
        workers=4,              
        project='velopark_training',
        name='yolo11m_bicycle_parking_with_augmentation',
        
        # Optimized learning parameters for augmented dataset
        optimizer='AdamW',      
        lr0=0.001,              # Slightly higher LR for more data
        lrf=0.01,               
        momentum=0.937,
        weight_decay=0.0005,    # Reduced regularization (more data = less overfitting)
        warmup_epochs=5,        
        warmup_momentum=0.8,    
        warmup_bias_lr=0.1,     
        
        # Reduced augmentation since we already have augmented data
        hsv_h=0.015,            
        hsv_s=0.7,              
        hsv_v=0.4,              
        degrees=15.0,           
        translate=0.1,          
        scale=0.5,              
        shear=2.0,              
        perspective=0.0001,        
        flipud=0.0,             
        fliplr=0.5,             
        mosaic=1.0,             
        mixup=0.15,              # Small amount of mixup
        copy_paste=0.3,         # Small amount of copy-paste
        
        val=True,               
        plots=True,             
        verbose=True,           
    )

    print("✅ Training completed!")
    print(f"📁 Results saved in: {results.save_dir}")
    
    return model, results


def resume_training(checkpoint_path=None):
    """
    Resume training from a checkpoint
    """
    if checkpoint_path is None:
        # Find the latest checkpoint
        project_dir = Path("velopark_training/yolo11m_bicycle_parking_with_augmentation")
        checkpoint_path = project_dir / "weights" / "last.pt"
    
    if not Path(checkpoint_path).exists():
        print(f"❌ Checkpoint not found: {checkpoint_path}")
        return
    
    print(f"🔄 Resuming training from: {checkpoint_path}")
    
    # Load model from checkpoint
    model = YOLO(checkpoint_path)
    
    # Continue training with same parameters
    data_yaml_path = "/home/arthur/Bureau/velopark_waypoints/yolofinal_v2/final_dataset/data.yaml"
    
    results = model.train(
        data=data_yaml_path,
        epochs=200,              
        imgsz=512,              
        batch=16,                
        patience=25,            # Increased patience for larger dataset
        save=True,              
        save_period=10,         
        cache=True,                         
        device='cuda' if torch.cuda.is_available() else 'cpu',
        workers=4,              
        project='velopark_training',
        name='yolo11m_bicycle_parking_resumed',  # Different name to avoid conflicts
        resume=True,            # Important: resume flag
        
        # Same parameters as before
        optimizer='AdamW',      
        lr0=0.001,              # Slightly higher LR for more data
        lrf=0.01,               
        momentum=0.937,
        weight_decay=0.0005,    # Reduced regularization (more data = less overfitting)
        warmup_epochs=5,        
        warmup_momentum=0.8,    
        warmup_bias_lr=0.1,    
        
        hsv_h=0.015,            
        hsv_s=0.7,              
        hsv_v=0.4,              
        degrees=15.0,           
        translate=0.1,          
        scale=0.5,              
        shear=2.0,              
        perspective=0.0001,        
        flipud=0.0,             
        fliplr=0.5,             
        mosaic=1.0,             
        mixup=0.15,              # Small amount of mixup
        copy_paste=0.3,         # Small amount of copy-paste
        
        val=True,               
        plots=True,             
        verbose=True,             
    )
    
    return model, results

# Add to your main section:
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--prepare":
            complete_dataset_preparation()
        elif sys.argv[1] == "--train":
            print("🚀 Starting training...")
            model, results = train_bicycle_parking_detector()
        elif sys.argv[1] == "--resume":
            print("🔄 Resuming training...")
            model, results = resume_training()
        elif sys.argv[1] == "--organize":
            organize_raw_data()
        else:
            print("Usage: python yolotrain.py [--prepare|--train|--resume|--organize]")
    else:
        # Default: complete pipeline
        print("🚀 Running complete pipeline...")
        complete_dataset_preparation()
        print("\n🚀 Starting training...")
        model, results = train_bicycle_parking_detector()

