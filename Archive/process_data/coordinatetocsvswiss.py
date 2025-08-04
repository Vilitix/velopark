import json
import csv
import os

def convert_bike_parking_to_streetview_csv(json_file="bike_parking.json", output_csv="bike_parking_streetview.csv"):
    """
    Extract coordinates from bike_parking.json and create CSV with Street View URLs
    
    Args:
        json_file (str): Path to the bike_parking.json file
        output_csv (str): Path for the output CSV file
    
    Returns:
        int: Number of bike parking locations processed
    """
    
    try:
        # Read the JSON file
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"📄 Loaded bike parking data from {json_file}")
        
        # Prepare CSV data
        csv_data = []
        processed_count = 0
        
        # Process each feature in the GeoJSON
        for feature in data.get('features', []):
            try:
                # Extract geometry coordinates
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [])
                
                # Skip if no coordinates
                if not coordinates:
                    continue
                
                # Handle different geometry types
                if geometry.get('type') == 'Point':
                    # For Point: coordinates = [longitude, latitude]
                    longitude, latitude = coordinates[0], coordinates[1]
                elif geometry.get('type') == 'MultiPoint':
                    # For MultiPoint: take the first point
                    if coordinates and len(coordinates[0]) >= 2:
                        longitude, latitude = coordinates[0][0], coordinates[0][1]
                    else:
                        continue
                else:
                    # Skip other geometry types for now
                    continue
                
                # Extract properties for additional info
                properties = feature.get('properties', {})
                feature_id = feature.get('id', 'unknown')
                
                # Create Street View URL
                streetview_url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={latitude},{longitude}"
                
                # Create more complete Street View URL (without specific panoid)
                streetview_url_simple = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={latitude},{longitude}"
                
                # Add to CSV data
                csv_row = {
                    'id': feature_id,
                    'latitude': latitude,
                    'longitude': longitude,
                    'streetview_url': streetview_url_simple,
                    'name': properties.get('name', ''),
                    'description': properties.get('description', ''),
                    'capacity': properties.get('capacity', ''),
                    'type': properties.get('type', ''),
                    'operator': properties.get('operator', ''),
                    'location': f"{latitude},{longitude}"
                }
                
                csv_data.append(csv_row)
                processed_count += 1
                
            except Exception as e:
                print(f"❌ Error processing feature {feature.get('id', 'unknown')}: {e}")
                continue
        
        # Write to CSV
        if csv_data:
            fieldnames = ['id', 'latitude', 'longitude', 'streetview_url', 'name', 
                         'description', 'capacity', 'type', 'operator', 'location']
            
            with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_data)
            
            print(f"✅ Successfully created {output_csv} with {processed_count} bike parking locations")
            print(f"📊 Columns: {', '.join(fieldnames)}")
        else:
            print("❌ No valid coordinates found in the JSON file")
            return 0
        
        return processed_count
        
    except FileNotFoundError:
        print(f"❌ File {json_file} not found")
        return 0
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return 0
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 0

def create_streetview_url_for_coordinates(latitude, longitude, heading=0, pitch=0, fov=75):
    """
    Create a Street View URL for given coordinates
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        heading (float): Direction (0-360 degrees, 0=North)
        pitch (float): Up/down angle (-90 to 90 degrees)
        fov (float): Field of view (10-100 degrees)
    
    Returns:
        str: Google Street View URL
    """
    return f"https://www.google.com/maps/@{latitude},{longitude},3a,{fov}y,{heading}h,{pitch}t"

def analyze_bike_parking_distribution(json_file="bike_parking.json"):
    """
    Analyze the distribution of bike parking locations
    
    Args:
        json_file (str): Path to the bike_parking.json file
    
    Returns:
        dict: Analysis results
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data.get('features', [])
        total_locations = len(features)
        
        # Count by geometry type
        geometry_types = {}
        coordinates_found = 0
        
        # Analyze properties
        operators = {}
        types = {}
        capacities = []
        
        for feature in features:
            # Geometry analysis
            geometry = feature.get('geometry', {})
            geom_type = geometry.get('type', 'unknown')
            geometry_types[geom_type] = geometry_types.get(geom_type, 0) + 1
            
            if geometry.get('coordinates'):
                coordinates_found += 1
            
            # Properties analysis
            properties = feature.get('properties', {})
            
            operator = properties.get('operator', 'unknown')
            operators[operator] = operators.get(operator, 0) + 1
            
            bike_type = properties.get('type', 'unknown')
            types[bike_type] = types.get(bike_type, 0) + 1
            
            capacity = properties.get('capacity')
            if capacity and str(capacity).isdigit():
                capacities.append(int(capacity))
        
        analysis = {
            'total_locations': total_locations,
            'coordinates_found': coordinates_found,
            'geometry_types': geometry_types,
            'operators': operators,
            'types': types,
            'capacity_stats': {
                'total_with_capacity': len(capacities),
                'average_capacity': sum(capacities) / len(capacities) if capacities else 0,
                'max_capacity': max(capacities) if capacities else 0,
                'min_capacity': min(capacities) if capacities else 0
            }
        }
        
        return analysis
        
    except Exception as e:
        print(f"❌ Error analyzing bike parking data: {e}")
        return {}

def generate_streetview_urls_batch(coordinates_list, output_csv="streetview_urls.csv"):
    """
    Generate Street View URLs for a list of coordinates
    
    Args:
        coordinates_list (list): List of tuples (latitude, longitude) or (lat, lon, name)
        output_csv (str): Output CSV file path
    
    Returns:
        int: Number of URLs generated
    """
    
    csv_data = []
    
    for i, coords in enumerate(coordinates_list):
        if len(coords) >= 2:
            lat, lon = coords[0], coords[1]
            name = coords[2] if len(coords) > 2 else f"Location_{i+1}"
            
            # Generate URLs with different viewing angles
            urls = {
                'north_view': create_streetview_url_for_coordinates(lat, lon, heading=0),
                'east_view': create_streetview_url_for_coordinates(lat, lon, heading=90),
                'south_view': create_streetview_url_for_coordinates(lat, lon, heading=180),
                'west_view': create_streetview_url_for_coordinates(lat, lon, heading=270),
                'default_view': create_streetview_url_for_coordinates(lat, lon)
            }
            
            csv_row = {
                'name': name,
                'latitude': lat,
                'longitude': lon,
                'north_view_url': urls['north_view'],
                'east_view_url': urls['east_view'],
                'south_view_url': urls['south_view'],
                'west_view_url': urls['west_view'],
                'default_view_url': urls['default_view']
            }
            
            csv_data.append(csv_row)
    
    # Write to CSV
    if csv_data:
        fieldnames = ['name', 'latitude', 'longitude', 'north_view_url', 
                     'east_view_url', 'south_view_url', 'west_view_url', 'default_view_url']
        
        with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_data)
        
        print(f"✅ Generated {output_csv} with {len(csv_data)} locations and multiple viewing angles")
    
    return len(csv_data)

if __name__ == "__main__":
    print("🚴 Swiss Bike Parking to Street View CSV Converter")
    print("=" * 50)
    
    # Convert bike parking data to Street View URLs
    count = convert_bike_parking_to_streetview_csv()
    
    if count > 0:
        print(f"\n📊 Successfully processed {count} bike parking locations")
        
        # Analyze the data
        print("\n📈 Analyzing bike parking distribution...")
        analysis = analyze_bike_parking_distribution()
        
        if analysis:
            print(f"📍 Total locations: {analysis['total_locations']}")
            print(f"🗺️  Locations with coordinates: {analysis['coordinates_found']}")
            print(f"📊 Geometry types: {analysis['geometry_types']}")
            print(f"🏢 Top operators: {dict(list(analysis['operators'].items())[:5])}")
            print(f"🚲 Bike types: {analysis['types']}")
            
            capacity_stats = analysis['capacity_stats']
            if capacity_stats['total_with_capacity'] > 0:
                print(f"📈 Capacity stats:")
                print(f"   • Average capacity: {capacity_stats['average_capacity']:.1f}")
                print(f"   • Max capacity: {capacity_stats['max_capacity']}")
                print(f"   • Min capacity: {capacity_stats['min_capacity']}")
        
        print(f"\n✅ CSV file 'bike_parking_streetview.csv' created successfully!")
        print("🌐 You can now use these URLs to view bike parking locations in Street View")
        
    else:
        print("❌ No bike parking locations were processed")


# Convert Swiss bike parking data
count = convert_bike_parking_to_streetview_csv("bike_parking.json", "swiss_bike_streetview.csv")
print(f"Processed {count} bike parking locations")

# Generate analysis
analysis = analyze_bike_parking_distribution("bike_parking.json")