# VeloPark Waypoints - AI-Powered Bicycle Parking Detection

## 📊 Project Summary

This project successfully developed an AI-powered system to automatically detect and map bicycle parking locations in Nancy, France using street view imagery and YOLOv11 object detection. The system achieved remarkable performance, capable of processing an entire city's street view data in just 53 hours total (50 hours for data collection + 3 hours for AI processing).

repository structure is in a mess because it was not meant to be used more than one time and by someone else sorry 

### Key Achievements
- **Data Collection**: 50,000+ street view images from Nancy
- **AI Training**: YOLOv11 model trained on 1,400 images (420 augmented from 70 manually labeled instances)
- **Training Performance**: 200 epochs in 48 hours on consumer hardware (Asus Zenbook 13, no GPU)
- **Detection Results**: Thousands of bicycle parking locations successfully identified
- **Processing Speed**: Complete city analysis in ~53 hours total

### Project Conclusion

The project demonstrated exceptional performance for bicycle parking detection in Nancy. However, it was discontinued after achieving these results for two primary reasons:
1. **Existing Coverage**: OpenStreetMap contributors had already mapped most bicycle parking locations in Nancy
2. **Geographic Limitations**: Bicycle parking designs vary significantly between countries and cities, requiring model retraining for different locations

**Future Applications**: This AI approach shows strong potential for rural cities and areas with limited existing mapping data, particularly when combined with free data sources like Mapillary for contributing to OpenStreetMap.

## Project Objective

This project aimed to map and identify bicycle parking locations in Nancy, France using street view imagery and artificial intelligence. The goal was to train an AI model to automatically recognize bicycle parking facilities from street-level images, with potential for expansion to other cities.

## 🔧 Tools & Technologies

- **Street View Scraper**: [StreetViewScraper](https://github.com/Jskinner9/StreetViewScraper) for downloading panoramic images
- **Selenium WebDriver**: Browser automation for navigation
- **PostgreSQL**: Database storage for coordinates and panorama IDs
- **YOLO v11**: Object detection for analyzing street view images
- **Label Studio**: Image annotation and labeling platform
- **Albumentations**: Data augmentation library
- **Python**: Primary development language

## 🚀 Current Implementation

### Automated Street View Navigation (`auto_walkthrough.py`)

The main workflow consists of:

1. **Starting Point**: Begin with a Google Street View URL
2. **Image Extraction**: Parse panorama ID from current location
3. **Data Storage**: Save coordinates and panorama ID to PostgreSQL database
4. **Image Download**: Use StreetViewScraper to download high-resolution images
5. **Navigation**: Move through Street View using keyboard shortcuts
6. **Iteration**: Repeat process to map entire street networks

### AI Training Pipeline

The project has evolved to include a complete machine learning workflow:

1. **Data Collection**: Downloaded approximately 50,000 street view images from Nancy
2. **Random Sampling**: Used `send_to_label.py` to select 1,000 random images for manual labeling
3. **Manual Annotation**: Labeled images using Label Studio, identifying 70 bicycle parking instances
4. **Data Augmentation**: Used Albumentations to expand the 70 labeled instances to 420 training samples
5. **Model Training**: Trained YOLOv11 model for 200 epochs over 48 hours
6. **AI Detection**: Applied trained model to the entire 50,000 image dataset
7. **Result Management**: All detected bicycle parking locations stored in `velopark` database table

### Current Status

- **Training Data**: 420 augmented samples from 70 manually identified bicycle parking instances
- **Model**: YOLOv11 trained for 200 epochs (48 hours)
- **Detection Results**: Thousands of potential bicycle parking locations identified
- **Challenge**: Managing and validating the large volume of AI detections (~1/5 of total dataset processed)
- **Review Tools**: Multiple Python scripts developed for human validation of AI results

## Current Challenges & Limitations

### Navigation Issues
- **Dead Ends**: Frequent encounters with walls and impassable areas
- **Imprecise Movement**: Camera redirection using arrow keys is slow and inaccurate
- **Non-Grid Roads**: Nancy's street layout doesn't follow 90° angles, complicating navigation
- **Manual Intervention**: Requires human placement of starting points every 5 minutes 
- **Limited Coverage**: Only maps ~20% of Nancy's major roads after 3 hours

### AI Validation Challenges
- **Volume Overload**: Too many AI detections to manually review efficiently
- **Review Interface**: Multiple attempts at creating user-friendly validation tools
- **Quality Control**: Need to balance between keeping all detections vs. manual filtering
- **Scale**: Current results represent only ~20% of total available data

### Search Strategy Problems
- **Inefficient BFS**: Breadth-first search is nearly impossible and extremely slow
- **Limited Exploration**: Checking left/right every 5 locations provides minimal backup routes
- **Small Road Issues**: Frequently stuck in narrow streets with multiple turns

## 🔍 Alternative Approaches Attempted

### 1. YOLO Object Detection ✅ **IMPLEMENTED**
- **Tool**: YOLOv11 (upgraded from YOLOv5)
- **Purpose**: Detect bicycle parking infrastructure directly from street view images
- **Success**: Successfully trained model with 420 augmented samples
- **Evolution**: Shifted from detecting bicycles to detecting parking infrastructure itself
- **Results**: Generated thousands of potential bicycle parking locations

### 2. Existing Bicycle Parking Databases
- **Data Sources**: Swiss (`bike_parking.json`) and Paris datasets
- **Processing**: `coordinatetocsvswiss.py` generates Street View URLs from coordinates
- **Issues**: 
  - Bicycle parking designs vary significantly between countries
  - Only metadata available, no images
  - Many Parisian parking locations not visible in Street View
  - Need to filter useful viewpoints manually

### 3. Satellite-Based Detection
- **Reference**: [German Master's Thesis](https://mediatum.ub.tum.de/doc/1634128/7kxtht1y6kwdfc9mjqalfom08.pdf)
- **Limitation**: Nancy's bicycle parking facilities are too small to detect via satellite imagery
- **Context**: German bicycle parking areas are much larger and more visible from above  