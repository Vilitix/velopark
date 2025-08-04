from ultralytics import YOLO
import cv2
import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path
import json
from collections import Counter
import seaborn as sns
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for saving
import matplotlib.pyplot as plt

def analyze_street_view_images(image_dir="~/street_view_park", output_dir="~/yolo_analysis"):
    """
    Analyze all JPG images in street_view_park using YOLO and create visualizations
    
    Args:
        image_dir (str): Directory containing street view images
        output_dir (str): Directory to save analysis results
    """
    
    # Expand paths
    image_dir = os.path.expanduser(image_dir)
    output_dir = os.path.expanduser(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"🤖 Starting YOLO analysis of images in {image_dir}")
    
    # Load latest YOLOv8 model
    print("📥 Loading YOLOv8 model...")
    model = YOLO('yolov8n.pt')  # Downloads automatically if not present
    
    # Find all JPG images
    image_extensions = ['*.jpg', '*.jpeg', '*.JPG', '*.JPEG']
    image_files = []
    for ext in image_extensions:
        image_files.extend(Path(image_dir).glob(ext))
    
    if not image_files:
        print(f"❌ No JPG images found in {image_dir}")
        return
    
    print(f"📷 Found {len(image_files)} images to analyze")
    
    # Analysis results storage
    all_detections = []
    class_counts = Counter()
    confidence_scores = []
    images_analyzed = []
    
    # Process each image
    for i, image_path in enumerate(image_files):
        print(f"🔍 Analyzing {i+1}/{len(image_files)}: {image_path.name}")
        
        try:
            # Run YOLO detection
            results = model(str(image_path))
            
            # Extract detection data
            for result in results:
                boxes = result.boxes
                
                if boxes is not None:
                    for box in boxes:
                        # Get class name, confidence, and bounding box
                        class_id = int(box.cls[0])
                        class_name = model.names[class_id]
                        confidence = float(box.conf[0])
                        bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                        
                        # Store detection data
                        detection = {
                            'image_name': image_path.name,
                            'image_path': str(image_path),
                            'class_id': class_id,
                            'class_name': class_name,
                            'confidence': confidence,
                            'bbox': bbox,
                            'bbox_area': (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                        }
                        
                        all_detections.append(detection)
                        class_counts[class_name] += 1
                        confidence_scores.append(confidence)
            
            images_analyzed.append({
                'image_name': image_path.name,
                'image_path': str(image_path),
                'detections_count': len(result.boxes) if result.boxes is not None else 0
            })
            
            # Save annotated image
            annotated_frame = results[0].plot()
            output_path = os.path.join(output_dir, f"annotated_{image_path.name}")
            cv2.imwrite(output_path, annotated_frame)
            
        except Exception as e:
            print(f"❌ Error analyzing {image_path.name}: {e}")
            continue
    
    print(f"✅ Analysis complete! Found {len(all_detections)} total detections")
    
    # Save raw detection data
    save_detection_data(all_detections, images_analyzed, output_dir)
    
    # Create visualizations
    create_analysis_visualizations(all_detections, class_counts, confidence_scores, images_analyzed, output_dir)
    
    # Generate summary report
    generate_analysis_report(all_detections, class_counts, confidence_scores, images_analyzed, output_dir)
    
    return all_detections, class_counts

def save_detection_data(detections, images_data, output_dir):
    """Save detection data to JSON and CSV files"""
    
    # Save as JSON
    json_path = os.path.join(output_dir, "detections.json")
    with open(json_path, 'w') as f:
        json.dump({
            'detections': detections,
            'images': images_data,
            'total_detections': len(detections),
            'total_images': len(images_data)
        }, f, indent=2)
    
    # Save as CSV for easy analysis
    if detections:
        df = pd.DataFrame(detections)
        csv_path = os.path.join(output_dir, "detections.csv")
        df.to_csv(csv_path, index=False)
        print(f"💾 Detection data saved to {json_path} and {csv_path}")

def create_analysis_visualizations(detections, class_counts, confidence_scores, images_data, output_dir):
    """Create comprehensive visualizations of YOLO analysis results"""
    
    # Set up the plotting style
    plt.style.use('default')
    sns.set_palette("husl")
    
    # Create main dashboard figure
    fig = plt.figure(figsize=(20, 16))
    
    # 1. Top detected classes (bar chart)
    ax1 = plt.subplot(3, 3, 1)
    if class_counts:
        top_classes = dict(class_counts.most_common(15))
        bars = ax1.bar(range(len(top_classes)), list(top_classes.values()))
        ax1.set_xticks(range(len(top_classes)))
        ax1.set_xticklabels(list(top_classes.keys()), rotation=45, ha='right')
        ax1.set_title('Top 15 Detected Object Classes')
        ax1.set_ylabel('Count')
        
        # Add value labels on bars
        for bar in bars:
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}', ha='center', va='bottom')
    
    # 2. Confidence score distribution
    ax2 = plt.subplot(3, 3, 2)
    if confidence_scores:
        ax2.hist(confidence_scores, bins=30, alpha=0.7, color='skyblue', edgecolor='black')
        ax2.axvline(np.mean(confidence_scores), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(confidence_scores):.2f}')
        ax2.set_title('Confidence Score Distribution')
        ax2.set_xlabel('Confidence Score')
        ax2.set_ylabel('Frequency')
        ax2.legend()
    
    # 3. Detections per image
    ax3 = plt.subplot(3, 3, 3)
    if images_data:
        detection_counts = [img['detections_count'] for img in images_data]
        ax3.hist(detection_counts, bins=20, alpha=0.7, color='lightgreen', edgecolor='black')
        ax3.set_title('Detections per Image Distribution')
        ax3.set_xlabel('Number of Detections')
        ax3.set_ylabel('Number of Images')
        ax3.axvline(np.mean(detection_counts), color='red', linestyle='--',
                   label=f'Mean: {np.mean(detection_counts):.1f}')
        ax3.legend()
    
    # 4. Class confidence comparison (box plot)
    ax4 = plt.subplot(3, 3, 4)
    if detections:
        df = pd.DataFrame(detections)
        # Get top 10 classes for readability
        top_10_classes = list(class_counts.most_common(10))
        top_10_names = [cls[0] for cls in top_10_classes]
        
        filtered_df = df[df['class_name'].isin(top_10_names)]
        if not filtered_df.empty:
            sns.boxplot(data=filtered_df, x='class_name', y='confidence', ax=ax4)
            plt.setp(ax4.get_xticklabels(), rotation=45, ha='right')
            ax4.set_title('Confidence Scores by Class (Top 10)')
            ax4.set_ylabel('Confidence Score')
    
    # 5. Object size distribution (bbox area)
    ax5 = plt.subplot(3, 3, 5)
    if detections:
        df = pd.DataFrame(detections)
        bbox_areas = df['bbox_area'].values
        ax5.hist(np.log10(bbox_areas + 1), bins=30, alpha=0.7, color='orange', edgecolor='black')
        ax5.set_title('Object Size Distribution (Log Scale)')
        ax5.set_xlabel('Log10(Bounding Box Area)')
        ax5.set_ylabel('Frequency')
    
    # 6. Vehicle-related detections pie chart
    ax6 = plt.subplot(3, 3, 6)
    vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'person']
    vehicle_counts = {cls: class_counts.get(cls, 0) for cls in vehicle_classes}
    other_count = sum(class_counts.values()) - sum(vehicle_counts.values())
    
    if sum(vehicle_counts.values()) > 0:
        vehicle_counts['other'] = other_count
        # Remove zero values
        vehicle_counts = {k: v for k, v in vehicle_counts.items() if v > 0}
        
        ax6.pie(vehicle_counts.values(), labels=vehicle_counts.keys(), autopct='%1.1f%%')
        ax6.set_title('Transportation Objects Distribution')
    
    # 7. Detection heatmap by image position (if we have enough data)
    ax7 = plt.subplot(3, 3, 7)
    if detections:
        df = pd.DataFrame(detections)
        # Create a simplified spatial analysis
        x_centers = []
        y_centers = []
        for _, det in df.iterrows():
            bbox = det['bbox']
            x_center = (bbox[0] + bbox[2]) / 2
            y_center = (bbox[1] + bbox[3]) / 2
            x_centers.append(x_center)
            y_centers.append(y_center)
        
        if x_centers and y_centers:
            ax7.scatter(x_centers, y_centers, alpha=0.6, s=20)
            ax7.set_title('Object Position Distribution')
            ax7.set_xlabel('X Position (pixels)')
            ax7.set_ylabel('Y Position (pixels)')
            ax7.invert_yaxis()  # Invert Y axis to match image coordinates
    
    # 8. Street furniture analysis
    ax8 = plt.subplot(3, 3, 8)
    street_objects = ['traffic light', 'stop sign', 'bench', 'fire hydrant', 'parking meter']
    street_counts = {obj: class_counts.get(obj, 0) for obj in street_objects}
    street_counts = {k: v for k, v in street_counts.items() if v > 0}
    
    if street_counts:
        ax8.bar(street_counts.keys(), street_counts.values(), color='purple', alpha=0.7)
        ax8.set_title('Street Furniture Detections')
        ax8.set_ylabel('Count')
        ax8.tick_params(axis='x', rotation=45)
    else:
        ax8.text(0.5, 0.5, 'No street furniture\ndetected', ha='center', va='center', 
                transform=ax8.transAxes, fontsize=12)
        ax8.set_title('Street Furniture Detections')
    
    # 9. Analysis summary text
    ax9 = plt.subplot(3, 3, 9)
    ax9.axis('off')
    
    total_images = len(images_data)
    total_detections = len(detections)
    avg_detections = total_detections / total_images if total_images > 0 else 0
    most_common_class = class_counts.most_common(1)[0] if class_counts else ("None", 0)
    avg_confidence = np.mean(confidence_scores) if confidence_scores else 0
    
    summary_text = f"""
    ANALYSIS SUMMARY
    
    Total Images: {total_images}
    Total Detections: {total_detections}
    Avg Detections/Image: {avg_detections:.1f}
    Most Common Object: {most_common_class[0]} ({most_common_class[1]}x)
    Avg Confidence: {avg_confidence:.2f}
    Unique Classes: {len(class_counts)}
    
    Top 5 Objects:
    """
    
    for i, (obj, count) in enumerate(class_counts.most_common(5)):
        summary_text += f"\n{i+1}. {obj}: {count}"
    
    ax9.text(0.1, 0.9, summary_text, transform=ax9.transAxes, fontsize=11,
             verticalalignment='top', fontfamily='monospace',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.8))
    
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'yolo_analysis_dashboard.png'), 
                dpi=300, bbox_inches='tight')
    print(f"📊 Dashboard saved to {os.path.join(output_dir, 'yolo_analysis_dashboard.png')}")
    
    # Create detailed class analysis
    create_detailed_class_analysis(detections, class_counts, output_dir)

def create_detailed_class_analysis(detections, class_counts, output_dir):
    """Create detailed analysis plots for specific object classes"""
    
    if not detections:
        return
    
    df = pd.DataFrame(detections)
    
    # Focus on most common classes
    top_classes = [cls[0] for cls in class_counts.most_common(8)]
    
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()
    
    for i, class_name in enumerate(top_classes):
        if i >= 8:
            break
            
        class_data = df[df['class_name'] == class_name]
        
        if len(class_data) > 0:
            # Plot confidence distribution for this class
            axes[i].hist(class_data['confidence'], bins=15, alpha=0.7, 
                        color=plt.cm.tab10(i), edgecolor='black')
            axes[i].set_title(f'{class_name.title()}\n({len(class_data)} detections)')
            axes[i].set_xlabel('Confidence Score')
            axes[i].set_ylabel('Frequency')
            axes[i].axvline(class_data['confidence'].mean(), color='red', 
                           linestyle='--', alpha=0.8)
    
    # Hide unused subplots
    for i in range(len(top_classes), 8):
        axes[i].axis('off')
    
    plt.suptitle('Confidence Distribution by Object Class', fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'class_confidence_analysis.png'), 
                dpi=300, bbox_inches='tight')
    print(f"📊 Class analysis saved to {os.path.join(output_dir, 'class_confidence_analysis.png')}")

def generate_analysis_report(detections, class_counts, confidence_scores, images_data, output_dir):
    """Generate a comprehensive text report"""
    
    report_path = os.path.join(output_dir, 'yolo_analysis_report.txt')
    
    with open(report_path, 'w') as f:
        f.write("🤖 YOLO STREET VIEW ANALYSIS REPORT\n")
        f.write("=" * 50 + "\n\n")
        
        # Basic statistics
        f.write("📊 BASIC STATISTICS\n")
        f.write("-" * 20 + "\n")
        f.write(f"Total images analyzed: {len(images_data)}\n")
        f.write(f"Total objects detected: {len(detections)}\n")
        f.write(f"Unique object classes: {len(class_counts)}\n")
        f.write(f"Average detections per image: {len(detections)/len(images_data):.2f}\n")
        f.write(f"Average confidence score: {np.mean(confidence_scores):.3f}\n\n")
        
        # Top detected classes
        f.write("🏆 TOP 15 DETECTED OBJECTS\n")
        f.write("-" * 25 + "\n")
        for i, (obj, count) in enumerate(class_counts.most_common(15)):
            percentage = (count / len(detections)) * 100
            f.write(f"{i+1:2d}. {obj:<20} {count:4d} ({percentage:5.1f}%)\n")
        f.write("\n")
        
        # Transportation analysis
        vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle', 'person']
        f.write("🚗 TRANSPORTATION ANALYSIS\n")
        f.write("-" * 25 + "\n")
        for vehicle in vehicle_classes:
            count = class_counts.get(vehicle, 0)
            if count > 0:
                f.write(f"{vehicle.capitalize():<12}: {count:4d}\n")
        f.write("\n")
        
        # Street infrastructure
        street_objects = ['traffic light', 'stop sign', 'bench', 'fire hydrant', 'parking meter']
        f.write("🛣️  STREET INFRASTRUCTURE\n")
        f.write("-" * 23 + "\n")
        for obj in street_objects:
            count = class_counts.get(obj, 0)
            f.write(f"{obj.replace('_', ' ').title():<15}: {count:4d}\n")
        f.write("\n")
        
        # Images with most/least detections
        detections_per_image = [(img['image_name'], img['detections_count']) for img in images_data]
        detections_per_image.sort(key=lambda x: x[1], reverse=True)
        
        f.write("📷 IMAGES WITH MOST DETECTIONS\n")
        f.write("-" * 30 + "\n")
        for i, (img_name, count) in enumerate(detections_per_image[:10]):
            f.write(f"{i+1:2d}. {img_name:<30} {count:3d} objects\n")
        f.write("\n")
        
        f.write("📷 IMAGES WITH LEAST DETECTIONS\n")
        f.write("-" * 31 + "\n")
        for i, (img_name, count) in enumerate(detections_per_image[-10:]):
            f.write(f"{i+1:2d}. {img_name:<30} {count:3d} objects\n")
    
    print(f"📋 Analysis report saved to {report_path}")

def create_image_grid_with_annotations(image_dir, output_dir, max_images=16):
    """Create a grid showing sample annotated images"""
    
    # Find annotated images
    annotated_dir = output_dir
    annotated_files = list(Path(annotated_dir).glob("annotated_*.jpg"))
    
    if not annotated_files:
        print("No annotated images found")
        return
    
    # Select a sample of images
    selected_files = annotated_files[:max_images]
    
    # Calculate grid size
    grid_size = int(np.ceil(np.sqrt(len(selected_files))))
    
    fig, axes = plt.subplots(grid_size, grid_size, figsize=(20, 20))
    if grid_size == 1:
        axes = [axes]
    else:
        axes = axes.flatten()
    
    for i, img_path in enumerate(selected_files):
        if i >= len(axes):
            break
            
        img = cv2.imread(str(img_path))
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        axes[i].imshow(img_rgb)
        axes[i].set_title(img_path.name.replace('annotated_', ''), fontsize=8)
        axes[i].axis('off')
    
    # Hide unused subplots
    for i in range(len(selected_files), len(axes)):
        axes[i].axis('off')
    
    plt.suptitle('Sample Annotated Street View Images', fontsize=16)
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'annotated_images_grid.png'), 
                dpi=200, bbox_inches='tight')
    plt.show()

if __name__ == "__main__":
    print("🚀 Starting YOLO analysis of street view images...")
    
    # Run the analysis
    detections, class_counts = analyze_street_view_images()
    
    # Create image grid
    create_image_grid_with_annotations("~/street_view_park", "~/yolo_analysis")
    
    print("✅ YOLO analysis complete!")
    print("📁 Check ~/yolo_analysis/ for all results:")
    print("   • yolo_analysis_dashboard.png - Main dashboard")
    print("   • class_confidence_analysis.png - Detailed class analysis") 
    print("   • annotated_images_grid.png - Sample annotated images")
    print("   • yolo_analysis_report.txt - Comprehensive text report")
    print("   • detections.json/csv - Raw detection data")
    print("   • annotated_*.jpg - All annotated images")