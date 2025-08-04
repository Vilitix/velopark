from ultralytics import YOLO
from pathlib import Path
import cv2
import numpy as np

def predict_velo_parking(image_path, confidence_threshold=0.5):
    """
    Predict if there is bicycle parking in the given image using the trained AI model.
    
    Args:
        image_path (str): Path to the image file
        confidence_threshold (float): Minimum confidence score for detection (0.0-1.0)
    
    Returns:
        dict: {
            'has_velo_parking': bool,
            'confidence': float,
            'detections': list,
            'detection_count': int
        }
    """
    
    # Load the trained model
    model_path = "/home/arthur/Bureau/velopark_waypoints/AI.pt"
    
    try:
        model = YOLO(model_path)
    except Exception as e:
        return {
            'error': f"Failed to load model: {e}",
            'has_velo_parking': False,
            'confidence': 0.0,
            'detections': [],
            'detection_count': 0
        }
    
    # Check if image exists
    if not Path(image_path).exists():
        return {
            'error': f"Image not found: {image_path}",
            'has_velo_parking': False,
            'confidence': 0.0,
            'detections': [],
            'detection_count': 0
        }
    
    try:
        # Run inference on the image
        results = model(image_path)
        
        # Get the first result (single image)
        result = results[0]
        
        # Extract detections
        detections = []
        max_confidence = 0.0
        
        if result.boxes is not None and len(result.boxes) > 0:
            for box in result.boxes:
                confidence = float(box.conf[0])
                
                # Only consider detections above threshold
                if confidence >= confidence_threshold:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    detection = {
                        'confidence': confidence,
                        'bbox': {
                            'x1': int(x1),
                            'y1': int(y1),
                            'x2': int(x2),
                            'y2': int(y2)
                        },
                        'class': 'velo_park'
                    }
                    detections.append(detection)
                    
                    # Update max confidence
                    if confidence > max_confidence:
                        max_confidence = confidence
        
        # Determine if bicycle parking is present
        has_velo_parking = len(detections) > 0
        
        return {
            'has_velo_parking': has_velo_parking,
            'confidence': max_confidence,
            'detections': detections,
            'detection_count': len(detections)
        }
        
    except Exception as e:
        return {
            'error': f"Prediction failed: {e}",
            'has_velo_parking': False,
            'confidence': 0.0,
            'detections': [],
            'detection_count': 0
        }

def predict_and_visualize(image_path, output_path="/home/arthur/Bureau/velopark_waypoints/test_image", confidence_threshold=0.5):
    """
    Predict bicycle parking and save visualization with bounding boxes.
    
    Args:
        image_path (str): Path to input image
        output_path (str): Path to save annotated image (optional)
        confidence_threshold (float): Minimum confidence for detection
    
    Returns:
        dict: Same as predict_velo_parking + 'output_image_path'
    """
    
    # Get prediction results
    prediction = predict_velo_parking(image_path, confidence_threshold)
    
    if 'error' in prediction:
        return prediction
    
    # Load and annotate image
    try:
        image = cv2.imread(image_path)
        
        # Draw bounding boxes for each detection
        for detection in prediction['detections']:
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            # Draw rectangle
            cv2.rectangle(image, 
                         (bbox['x1'], bbox['y1']), 
                         (bbox['x2'], bbox['y2']), 
                         (0, 255, 0), 2)  # Green box
            
            # Add confidence text
            label = f"Velo Park: {confidence:.2f}"
            cv2.putText(image, label, 
                       (bbox['x1'], bbox['y1'] - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # Save annotated image
        if output_path is None:
            input_path = Path(image_path)
            output_path = str(input_path.parent / f"{input_path.stem}_detected{input_path.suffix}")
        
        cv2.imwrite(output_path, image)
        prediction['output_image_path'] = output_path
        
    except Exception as e:
        prediction['error'] = f"Visualization failed: {e}"
    
    return prediction


if __name__ == "__main__":
    # Example usage
    
    # Simple prediction
    image_path = "/home/arthur/Bureau/velopark_waypoints/yolo_final/veloparkdataset/images/val/0CereJnlvbC6EYkJGe2XFQ_View2_NE_FOV90.0.jpg"
    result = predict_and_visualize(image_path)
    
    if result['has_velo_parking']:
        print(f"✅ Bicycle parking detected with {result['confidence']:.2f} confidence")
        print(f"📍 Found {result['detection_count']} parking spot(s)")
    else:
        print("❌ No bicycle parking detected")