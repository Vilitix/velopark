import cv2
import albumentations as A
import numpy as np
import shutil
import os
from pathlib import Path

def create_augmentation_pipeline():
    """
    Create augmentation pipeline optimized for street view images
    Fixed parameter names for newer Albumentations versions
    """
    return A.Compose([
        # Lighting and color augmentations
        A.OneOf([
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=1.0),
            A.RandomGamma(gamma_limit=(80, 120), p=1.0),
            A.CLAHE(clip_limit=4.0, tile_grid_size=(8, 8), p=1.0),
        ], p=0.8),
        
        # Weather and atmospheric effects (simplified to avoid parameter issues)
        A.OneOf([
            A.RandomFog(p=1.0),  # Use default parameters
            A.RandomRain(rain_type='drizzle', p=1.0),  # Simplified parameters
            A.RandomSunFlare(p=1.0),  # Use default parameters
        ], p=0.3),
        
        # Blur and noise
        A.OneOf([
            A.MotionBlur(blur_limit=7, p=1.0),
            A.MedianBlur(blur_limit=5, p=1.0),
            A.GaussianBlur(blur_limit=5, p=1.0),
        ], p=0.4),
        
        # Noise (fixed parameter names)
        A.OneOf([
            A.GaussNoise(var_limit=(10.0, 50.0), mean=0, p=1.0),  # Added mean parameter
            A.ISONoise(color_shift=(0.01, 0.05), intensity=(0.1, 0.5), p=1.0),
        ], p=0.3),
        
        # Geometric transformations (no rotation)
        A.OneOf([
            A.HorizontalFlip(p=1.0),
            A.Affine(scale=(0.8, 1.2), translate_percent=(-0.1, 0.1), rotate=0, p=1.0),  # Use Affine instead of ShiftScaleRotate
        ], p=0.5),
        
        # Perspective and distortion (simplified)
        A.OneOf([
            A.Perspective(scale=(0.05, 0.1), p=1.0),
            A.ElasticTransform(alpha=1, sigma=50, p=1.0),  # Removed alpha_affine
        ], p=0.3),
        
        # Color space manipulations
        A.OneOf([
            A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0),
            A.RGBShift(r_shift_limit=15, g_shift_limit=15, b_shift_limit=15, p=1.0),
            A.ChannelShuffle(p=1.0),
        ], p=0.4),
        
        # Quality degradation (fixed parameter names)
        A.OneOf([
            A.ImageCompression(quality_lower=60, quality_upper=100, compression_type=A.ImageCompression.ImageCompressionType.JPEG, p=1.0),
            A.Downscale(scale_min=0.75, scale_max=0.95, p=1.0),  # Removed interpolation parameter
        ], p=0.2),
        
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))

def load_yolo_annotations(label_path):
    """
    Load YOLO format annotations from file
    """
    bboxes = []
    class_labels = []
    
    if os.path.exists(label_path):
        with open(label_path, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 5:
                    class_id = int(parts[0])
                    x_center, y_center, width, height = map(float, parts[1:])
                    bboxes.append([x_center, y_center, width, height])
                    class_labels.append(class_id)
    
    return bboxes, class_labels

def save_yolo_annotations(bboxes, class_labels, output_path):
    """
    Save annotations in YOLO format
    """
    with open(output_path, 'w') as f:
        for bbox, class_id in zip(bboxes, class_labels):
            x_center, y_center, width, height = bbox
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n")

def debug_dataset_structure(dataset_path):
    """
    Debug function to check dataset structure
    """
    dataset_path = Path(dataset_path)
    print(f"🔍 Checking dataset structure at: {dataset_path}")
    
    if not dataset_path.exists():
        print(f"❌ Dataset path does not exist!")
        return False
    
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    print(f"📁 Images directory: {images_dir}")
    print(f"   Exists: {images_dir.exists()}")
    
    if images_dir.exists():
        image_files = list(images_dir.glob('*'))
        print(f"   Files found: {len(image_files)}")
        if image_files:
            print(f"   Sample files: {[f.name for f in image_files[:5]]}")
    
    print(f"📁 Labels directory: {labels_dir}")
    print(f"   Exists: {labels_dir.exists()}")
    
    if labels_dir.exists():
        label_files = list(labels_dir.glob('*'))
        print(f"   Files found: {len(label_files)}")
        if label_files:
            print(f"   Sample files: {[f.name for f in label_files[:5]]}")
    
    return True

def augment_yolo_dataset(dataset_path, output_path, augmentations_per_image=3):
    """
    Augment YOLO dataset with images and corresponding labels
    """
    
    # Debug dataset structure first
    debug_dataset_structure(dataset_path)
    
    dataset_path = Path(dataset_path)
    output_path = Path(output_path)
    
    # Create output directories
    output_images_dir = output_path / 'images'
    output_labels_dir = output_path / 'labels'
    
    output_images_dir.mkdir(parents=True, exist_ok=True)
    output_labels_dir.mkdir(parents=True, exist_ok=True)
    
    images_dir = dataset_path / 'images'
    labels_dir = dataset_path / 'labels'
    
    if not images_dir.exists():
        print(f"❌ Images directory not found: {images_dir}")
        return
    
    # Get all image files with more specific search
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.JPG', '.JPEG', '.PNG']
    image_files = []
    
    for ext in image_extensions:
        found_files = list(images_dir.glob(f'*{ext}'))
        image_files.extend(found_files)
        print(f"Found {len(found_files)} files with extension {ext}")
    
    print(f"📁 Total images found: {len(image_files)} in {images_dir}")
    
    if len(image_files) == 0:
        print("❌ No images found! Please check:")
        print("   1. Images are in the 'images' subdirectory")
        print("   2. Images have supported extensions (.jpg, .png, etc.)")
        print("   3. File permissions are correct")
        return
    
    # Create simplified augmentation pipeline to avoid warnings
    transform = A.Compose([
        A.OneOf([
            A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=1.0),
            A.HueSaturationValue(hue_shift_limit=20, sat_shift_limit=30, val_shift_limit=20, p=1.0),
        ], p=0.8),
        
        A.OneOf([
            A.HorizontalFlip(p=1.0),
            A.GaussNoise(var_limit=(10.0, 50.0), p=1.0),
        ], p=0.5),
        
        A.OneOf([
            A.MotionBlur(blur_limit=7, p=1.0),
            A.RandomGamma(gamma_limit=(80, 120), p=1.0),
        ], p=0.4),
        
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels']))
    
    # Simple transform for images without bboxes
    simple_transform = A.Compose([
        A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.8),
        A.HorizontalFlip(p=0.5),
        A.GaussNoise(var_limit=(10.0, 30.0), p=0.3),
    ])
    
    total_processed = 0
    total_augmented = 0
    
    for image_path in image_files:
        try:
            print(f"Processing: {image_path.name}")
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                print(f"❌ Could not load image: {image_path}")
                continue
            
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Load corresponding label file
            label_path = labels_dir / f"{image_path.stem}.txt"
            
            # Load annotations
            bboxes, class_labels = load_yolo_annotations(label_path)
            
            # Copy original files to output
            shutil.copy2(image_path, output_images_dir / image_path.name)
            if label_path.exists():
                shutil.copy2(label_path, output_labels_dir / label_path.name)
            
            total_processed += 1
            
            # Generate augmented versions
            for i in range(augmentations_per_image):
                try:
                    # Apply augmentation
                    if len(bboxes) > 0:
                        augmented = transform(image=image, bboxes=bboxes, class_labels=class_labels)
                        aug_image = augmented['image']
                        aug_bboxes = augmented['bboxes']
                        aug_class_labels = augmented['class_labels']
                    else:
                        augmented = simple_transform(image=image)
                        aug_image = augmented['image']
                        aug_bboxes = []
                        aug_class_labels = []
                    
                    # Generate output filename
                    base_name = image_path.stem
                    aug_image_name = f"{base_name}_aug_{i+1}{image_path.suffix}"
                    aug_label_name = f"{base_name}_aug_{i+1}.txt"
                    
                    # Save augmented image
                    aug_image_bgr = cv2.cvtColor(aug_image, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(str(output_images_dir / aug_image_name), aug_image_bgr)
                    # Verify the file was actually written
                    if not (output_images_dir / aug_image_name).exists():
                        print(f"❌ Failed to write: {aug_image_name}")
                        continue
                    else:
                        print(f"✅ Saved: {aug_image_name}")
                    # Save augmented labels
                    save_yolo_annotations(aug_bboxes, aug_class_labels, output_labels_dir / aug_label_name)
                    
                    total_augmented += 1
                    
                except Exception as e:
                    print(f"❌ Error augmenting {image_path.name} (iteration {i+1}): {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ Error processing {image_path}: {e}")
            continue
    
    print(f"\n🎯 AUGMENTATION COMPLETE:")
    print(f"   📁 Original images: {len(image_files)}")
    print(f"   ✅ Successfully processed: {total_processed}")
    print(f"   🔄 Total augmentations generated: {total_augmented}")
    print(f"   📁 Output directory: {output_path}")
    print(f"   📊 Total images in output: {total_processed + total_augmented}")



# Usage examples
if __name__ == "__main__":
    # Set paths
    input_dataset = "/home/arthur/Bureau/velopark_waypoints/initial_image_dataset"
    output_dataset = "/home/arthur/Bureau/velopark_waypoints/augmented_dataset"
    
    print("🚀 Starting YOLO dataset augmentation...")
    print(f"📁 Input: {input_dataset}")
    print(f"📁 Output: {output_dataset}")
    
    # Augment dataset
    augment_yolo_dataset(
        dataset_path=input_dataset,
        output_path=output_dataset,
        augmentations_per_image=5
    )
    
    print("✅ Augmentation completed!")


import os

labels_dir = "/home/arthur/Bureau/velopark_waypoints/augmented_dataset/labels"

for filename in os.listdir(labels_dir):
    if filename.endswith(".txt"):
        path = os.path.join(labels_dir, filename)
        with open(path, "r") as f:
            lines = f.readlines()
        with open(path, "w") as f:
            for line in lines:
                parts = line.strip().split()
                if parts and '.' in parts[0]:
                    parts[0] = str(int(float(parts[0])))
                f.write(" ".join(parts) + "\n")
