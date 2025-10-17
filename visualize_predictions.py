#!/usr/bin/env python3
"""
Cool YOLO Visualization Script
Processes validation images with best1400images.pt model and creates visually appealing output
with bounding boxes, confidence scores, and cool styling effects.
"""

import torch
import cv2
import numpy as np
import os
from pathlib import Path
import random
from ultralytics import YOLO
import argparse

class CoolVisualizer:
    def __init__(self, model_path, val_dir, output_dir):
        self.model_path = model_path
        self.val_dir = Path(val_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Load the model
        print(f"🚀 Loading model from {model_path}...")
        self.model = YOLO(model_path)
        
        # Cool color palette (RGB)
        self.colors = [
            (255, 100, 100),  # Bright red
            (100, 255, 100),  # Bright green
            (100, 100, 255),  # Bright blue
            (255, 255, 100),  # Bright yellow
            (255, 100, 255),  # Bright magenta
            (100, 255, 255),  # Bright cyan
            (255, 165, 0),    # Orange
            (255, 20, 147),   # Deep pink
            (50, 205, 50),    # Lime green
            (138, 43, 226),   # Blue violet
        ]
        
    def get_gradient_color(self, confidence):
        """Generate gradient color based on confidence (low conf = red, high conf = green)"""
        # Interpolate between red and green based on confidence
        red = int(255 * (1 - confidence))
        green = int(255 * confidence)
        blue = 50
        return (blue, green, red)  # BGR format for OpenCV
    
    def draw_rounded_rectangle(self, img, pt1, pt2, color, thickness=2, radius=15):
        """Draw a rounded rectangle"""
        x1, y1 = pt1
        x2, y2 = pt2
        
        # Draw main rectangle
        cv2.rectangle(img, (x1 + radius, y1), (x2 - radius, y2), color, thickness)
        cv2.rectangle(img, (x1, y1 + radius), (x2, y2 - radius), color, thickness)
        
        # Draw corners
        cv2.ellipse(img, (x1 + radius, y1 + radius), (radius, radius), 180, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y1 + radius), (radius, radius), 270, 0, 90, color, thickness)
        cv2.ellipse(img, (x1 + radius, y2 - radius), (radius, radius), 90, 0, 90, color, thickness)
        cv2.ellipse(img, (x2 - radius, y2 - radius), (radius, radius), 0, 0, 90, color, thickness)
    
    def add_glow_effect(self, img, pt1, pt2, color, intensity=3):
        """Add a glow effect around the bounding box"""
        x1, y1 = pt1
        x2, y2 = pt2
        
        for i in range(intensity):
            thickness = intensity - i
            glow_color = tuple(int(c * (0.3 + 0.7 * i / intensity)) for c in color)
            cv2.rectangle(img, 
                         (x1 - i*2, y1 - i*2), 
                         (x2 + i*2, y2 + i*2), 
                         glow_color, thickness)
    
    def create_label_background(self, img, text, position, color, font_scale=0.8):
        """Create a stylish background for the label text"""
        font = cv2.FONT_HERSHEY_SIMPLEX
        thickness = 2
        
        # Get text size
        (text_width, text_height), baseline = cv2.getTextSize(text, font, font_scale, thickness)
        
        x, y = position
        padding = 8
        
        # Create gradient background
        bg_height = text_height + 2 * padding
        bg_width = text_width + 2 * padding
        
        # Create overlay for transparency effect
        overlay = img.copy()
        
        # Draw rounded background
        cv2.rectangle(overlay, 
                     (x - padding, y - text_height - padding), 
                     (x + text_width + padding, y + padding), 
                     color, -1)
        
        # Apply transparency
        alpha = 0.8
        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        
        return (x, y), (text_width, text_height)
    
    def process_image(self, img_path):
        """Process a single image with the model and create cool visualization"""
        print(f"🎨 Processing {img_path.name}...")
        
        # Load image
        img = cv2.imread(str(img_path))
        if img is None:
            print(f"❌ Could not load image: {img_path}")
            return
        
        original_img = img.copy()
        
        # Run inference
        results = self.model(img)
        
        # Get detections
        if len(results) > 0 and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            
            detection_count = 0
            for box in boxes:
                # Extract box data
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                class_id = int(box.cls[0])
                class_name = self.model.names[class_id]
                
                # Skip low confidence detections
                if confidence < 0.3:
                    continue
                
                detection_count += 1
                
                # Get gradient color based on confidence
                bbox_color = self.get_gradient_color(confidence)
                
                # Add glow effect
                self.add_glow_effect(img, (x1, y1), (x2, y2), bbox_color, intensity=3)
                
                # Draw main bounding box with rounded corners
                self.draw_rounded_rectangle(img, (x1, y1), (x2, y2), bbox_color, thickness=3, radius=10)
                
                # Create label text
                label = f"{class_name} {confidence:.2f}"
                
                # Add label background and text
                text_pos, text_size = self.create_label_background(
                    img, label, (x1, y1 - 5), bbox_color, font_scale=0.7
                )
                
                # Draw text
                cv2.putText(img, label, text_pos, 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # Add confidence bar
                bar_width = int((x2 - x1) * confidence)
                bar_height = 6
                cv2.rectangle(img, (x1, y2 + 5), (x1 + bar_width, y2 + 5 + bar_height), 
                             bbox_color, -1)
                cv2.rectangle(img, (x1, y2 + 5), (x2, y2 + 5 + bar_height), 
                             (100, 100, 100), 2)
        
        else:
            detection_count = 0
        
        # Add watermark/info
        info_text = f"Detections: {detection_count} | Model: best1400images.pt"
        cv2.putText(img, info_text, (10, img.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(img, info_text, (10, img.shape[0] - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
        
        # Save output
        output_path = self.output_dir / f"predicted_{img_path.name}"
        cv2.imwrite(str(output_path), img)
        print(f"✅ Saved: {output_path} (found {detection_count} detections)")
        
        return detection_count
    
    def process_all_images(self, max_images=None):
        """Process all images in the validation directory"""
        # Get all image files
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(list(self.val_dir.glob(f"*{ext}")))
            image_files.extend(list(self.val_dir.glob(f"*{ext.upper()}")))
        
        if not image_files:
            print(f"❌ No images found in {self.val_dir}")
            return
        
        # Limit number of images if specified
        if max_images:
            image_files = image_files[:max_images]
        
        print(f"🎯 Found {len(image_files)} images to process")
        
        total_detections = 0
        processed_count = 0
        
        for img_path in image_files:
            try:
                detections = self.process_image(img_path)
                if detections is not None:
                    total_detections += detections
                    processed_count += 1
            except Exception as e:
                print(f"❌ Error processing {img_path}: {e}")
        
        print(f"\n🎉 Processing complete!")
        print(f"📊 Processed: {processed_count} images")
        print(f"🎯 Total detections: {total_detections}")
        print(f"📁 Output saved to: {self.output_dir}")

def main():
    parser = argparse.ArgumentParser(description="Cool YOLO Visualization")
    parser.add_argument("--model", default="best1400images.pt", 
                       help="Path to YOLO model file")
    parser.add_argument("--val-dir", default="yolofinal_v2/final_dataset/images/val",
                       help="Directory containing validation images")
    parser.add_argument("--output-dir", default="prediction_outputs",
                       help="Directory to save visualization outputs")
    parser.add_argument("--max-images", type=int, default=None,
                       help="Maximum number of images to process")
    
    args = parser.parse_args()
    
    # Check if model exists
    if not os.path.exists(args.model):
        print(f"❌ Model file not found: {args.model}")
        return
    
    # Check if validation directory exists
    if not os.path.exists(args.val_dir):
        print(f"❌ Validation directory not found: {args.val_dir}")
        return
    
    # Create visualizer and process images
    visualizer = CoolVisualizer(args.model, args.val_dir, args.output_dir)
    visualizer.process_all_images(args.max_images)

if __name__ == "__main__":
    main()
