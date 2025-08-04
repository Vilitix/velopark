import osmnx as ox
import networkx as nx
import numpy as np
import pandas as pd
import csv
from geopy.distance import geodesic
from shapely.geometry import Point, LineString
import geopandas as gpd

def generate_road_points_in_circle(center_lon, center_lat, radius_km, point_spacing_m=50, output_csv="road_points.csv"):
    """
    Generate evenly spaced points along all roads within a circular area
    
    Args:
        center_lon (float): Longitude of circle center
        center_lat (float): Latitude of circle center  
        radius_km (float): Radius of circle in kilometers
        point_spacing_m (float): Distance between points in meters (default: 50m)
        output_csv (str): Output CSV file path
    
    Returns:
        int: Number of points generated
    """
    
    try:
        print(f"🗺️  Downloading road network for circle center ({center_lat}, {center_lon}) with radius {radius_km}km...")
        
        # Download road network within the circular area
        # Add buffer to ensure we get complete road segments
        graph = ox.graph_from_point(
            (center_lat, center_lon), 
            dist=radius_km * 1000 + 500,  # Add 500m buffer
            network_type='drive'  # Get drivable roads
        )
        
        print(f"📊 Downloaded graph with {len(graph.nodes)} nodes and {len(graph.edges)} edges")
        
        # Convert to GeoDataFrame of edges (road segments)
        edges_gdf = ox.graph_to_gdfs(graph, nodes=False, edges=True)
        
        # Create circle boundary for filtering
        center_point = Point(center_lon, center_lat)
        
        # Convert radius from km to degrees (approximate)
        # 1 degree ≈ 111 km at equator
        radius_deg = radius_km / 111.0
        
        all_points = []
        processed_edges = 0
        
        print(f"🛣️  Processing {len(edges_gdf)} road segments...")
        
        for idx, edge in edges_gdf.iterrows():
            try:
                # Get the geometry of the road segment
                line_geom = edge['geometry']
                
                if line_geom is None:
                    continue
                
                # Calculate total length of this road segment in meters
                # Use approximate conversion: 1 degree ≈ 111 km
                line_length_m = line_geom.length * 111000
                
                # Calculate number of points needed for this segment
                num_points = max(2, int(line_length_m / point_spacing_m))
                
                # Generate evenly spaced points along the line
                for i in range(num_points):
                    # Get point at fraction i/(num_points-1) along the line
                    fraction = i / (num_points - 1) if num_points > 1 else 0
                    point_on_line = line_geom.interpolate(fraction, normalized=True)
                    
                    point_lon = point_on_line.x
                    point_lat = point_on_line.y
                    
                    # Check if point is within the circular boundary
                    point_geom = Point(point_lon, point_lat)
                    distance_from_center = geodesic(
                        (center_lat, center_lon), 
                        (point_lat, point_lon)
                    ).kilometers
                    
                    if distance_from_center <= radius_km:
                        all_points.append({
                            'latitude': point_lat,
                            'longitude': point_lon,
                            'distance_from_center_km': distance_from_center,
                            'road_segment_id': f"{idx[0]}_{idx[1]}_{idx[2]}" if len(idx) == 3 else f"{idx[0]}_{idx[1]}"
                        })
                
                processed_edges += 1
                if processed_edges % 100 == 0:
                    print(f"   Processed {processed_edges}/{len(edges_gdf)} edges, generated {len(all_points)} points so far...")
                    
            except Exception as e:
                print(f"   ⚠️  Error processing edge {idx}: {e}")
                continue
        
        # Remove duplicate points (within 10m of each other)
        # Remove duplicate points (within 10m of each other) - ULTRA FAST VERSION
        print(f"🧹 Removing duplicate points...")

        if len(all_points) > 0:
            # Use set with rounded coordinates for O(n) deduplication
            seen_coords = set()
            unique_points = []
            
            # Round to ~10m precision (0.0001 degrees ≈ 11m)
            for point in all_points:
                # Create a rounded coordinate tuple
                rounded_lat = round(point['latitude'], 4)
                rounded_lon = round(point['longitude'], 4)
                coord_key = (rounded_lat, rounded_lon)
                
                if coord_key not in seen_coords:
                    seen_coords.add(coord_key)
                    unique_points.append(point)
            
            print(f"📊 Ultra-fast deduplication: {len(all_points)} → {len(unique_points)} points (removed {len(all_points) - len(unique_points)} duplicates)")
        else:
            unique_points = []
        
        print(f"📊 Generated {len(unique_points)} unique road points (removed {len(all_points) - len(unique_points)} duplicates)")
        
        # Sort points by distance from center
        unique_points.sort(key=lambda p: p['distance_from_center_km'])
        
        # Write to CSV
        if unique_points:
            with open(output_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['point_id', 'latitude', 'longitude', 'distance_from_center_km', 'road_segment_id']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                for i, point in enumerate(unique_points, 1):
                    writer.writerow({
                        'point_id': i,
                        'latitude': point['latitude'],
                        'longitude': point['longitude'],
                        'distance_from_center_km': point['distance_from_center_km'],
                        'road_segment_id': point['road_segment_id']
                    })
            
            print(f"✅ Successfully created {output_csv} with {len(unique_points)} road points")
            print(f"📏 Point spacing: ~{point_spacing_m}m")
            print(f"🎯 Circle center: ({center_lat}, {center_lon})")
            print(f"📐 Circle radius: {radius_km}km")
            
            return len(unique_points)
        else:
            print("❌ No points generated")
            return 0
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return 0

def calculate_point_spacing(lat1, lon1, lat2, lon2):
    """
    Calculate the distance between two points in meters
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
    
    Returns:
        float: Distance in meters
    """
    return geodesic((lat1, lon1), (lat2, lon2)).meters

"""
# Example usage based on your points
if __name__ == "__main__":
    # Your example points
    point1 = (6.1759861, 48.6787675)  # (longitude, latitude)
    point2 = (6.1760165, 48.6786763)
    
    # Calculate spacing between your example points
    spacing = calculate_point_spacing(point1[1], point1[0], point2[1], point2[0])
    print(f"🔍 Distance between your example points: {spacing:.1f} meters")
    
    # Generate road points for Nancy area (adjust center and radius as needed)
    nancy_center_lon = 6.185472
    nancy_center_lat = 48.693167
    radius_km = 5  # 5km radius
    

    count = generate_road_points_in_circle(
        center_lon=nancy_center_lon,
        center_lat=nancy_center_lat,
        radius_km=radius_km,
        point_spacing_m=spacing,  # Use the spacing from your example
        output_csv="nancy_road_points.csv"
    )
    
    print(f"🎉 Generated {count} road points for Nancy area")
    """


import folium
import pandas as pd
import numpy as np

def visualize_road_points_on_map(csv_file="nancy_road_points.csv", output_html="nancy_road_points_map.html"):
    """
    Visualize all road points from CSV on an interactive map similar to visualize_panoids_on_map
    
    Args:
        csv_file (str): Path to the CSV file containing road points
        output_html (str): Output HTML file name for the map
    
    Returns:
        folium.Map: The created map object
    """
    
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        if df.empty:
            print("❌ No records found in CSV file")
            return None
        
        print(f"📊 Found {len(df)} road points in {csv_file}")
        
        # Calculate center point (average of all coordinates)
        avg_lat = df['latitude'].mean()
        avg_lon = df['longitude'].mean()
        
        print(f"🎯 Map center: ({avg_lat:.6f}, {avg_lon:.6f})")
        
        # Create map centered on average coordinates
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=13,
            tiles='OpenStreetMap'
        )
        
        # Add road points as markers
        for i, row in df.iterrows():
            lat = row['latitude']
            lon = row['longitude']
            point_id = row['point_id']
            distance_km = row.get('distance_from_center_km', 0)
            road_segment = row.get('road_segment_id', 'unknown')
            
            # Create popup with information
            popup_text = f"""
            <div style="width: 250px;">
                <b>Road Point {point_id}</b><br>
                Latitude: {lat:.6f}<br>
                Longitude: {lon:.6f}<br>
                Distance from center: {distance_km:.3f} km<br>
                Road segment: {road_segment}<br>
                <a href="https://www.google.com/maps/@{lat},{lon},3a,75y,0h,90t" target="_blank">View in Street View</a>
            </div>
            """
            
            # Color points based on distance from center
            if distance_km < 1:
                color = 'red'
            elif distance_km < 2:
                color = 'orange'
            elif distance_km < 3:
                color = 'yellow'
            else:
                color = 'green'
            
            # Add marker with smaller size for performance
            folium.CircleMarker(
                location=[lat, lon],
                popup=popup_text,
                radius=3,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                weight=1
            ).add_to(map_viz)
            
            # Add progress indicator for large datasets
            if (i + 1) % 1000 == 0:
                print(f"   Added {i + 1}/{len(df)} points to map...")
        
        # Add Nancy center and boundary circle (same as in auto_walkthrough.py)
        nancy_center_lat = 48.693167
        nancy_center_lon = 6.185472
        R_nancy = np.sqrt((nancy_center_lat - 48.667770)**2 + (6.146822 - nancy_center_lon)**2)
        
        nancy_center = [nancy_center_lat, nancy_center_lon]
        nancy_radius = R_nancy * 111000  # Convert to meters approximately
        
        folium.Marker(
            location=nancy_center,
            popup="Nancy Center",
            icon=folium.Icon(color='blue', icon='star')
        ).add_to(map_viz)
        
        folium.Circle(
            location=nancy_center,
            radius=nancy_radius,
            color='blue',
            fill=True,
            fillOpacity=0.1,
            popup=f"Nancy Boundary (R={R_nancy:.3f}°)"
        ).add_to(map_viz)
        
        # Add legend
        legend_html = '''
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 150px; height: 120px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:14px; padding: 10px
                    ">
        <p><b>Road Points Legend</b></p>
        <p><i class="fa fa-circle" style="color:red"></i> < 1 km from center</p>
        <p><i class="fa fa-circle" style="color:orange"></i> 1-2 km</p>
        <p><i class="fa fa-circle" style="color:yellow"></i> 2-3 km</p>
        <p><i class="fa fa-circle" style="color:green"></i> > 3 km</p>
        </div>
        '''
        map_viz.get_root().html.add_child(folium.Element(legend_html))
        
        # Add statistics
        stats_html = f'''
        <div style="position: fixed; 
                    top: 50px; right: 50px; width: 200px; height: 100px; 
                    background-color: white; border:2px solid grey; z-index:9999; 
                    font-size:12px; padding: 10px
                    ">
        <p><b>Nancy Road Network</b></p>
        <p>Total Points: {len(df)}</p>
        <p>Coverage: {df['distance_from_center_km'].max():.1f} km radius</p>
        <p>Avg Spacing: ~{calculate_average_spacing(df):.0f}m</p>
        </div>
        '''
        map_viz.get_root().html.add_child(folium.Element(stats_html))
        
        # Save map to HTML file
        map_viz.save(output_html)
        print(f"✅ Map saved as {output_html}")
        print(f"🌐 Open the file in your web browser to view the interactive map")
        print(f"📍 Total road points plotted: {len(df)}")
        
        return map_viz
        
    except FileNotFoundError:
        print(f"❌ CSV file {csv_file} not found")
        return None
    except Exception as e:
        print(f"❌ Error creating map: {e}")
        return None

def calculate_average_spacing(df):
    """Calculate approximate average spacing between consecutive points"""
    if len(df) < 2:
        return 0
    
    # Sample first 100 points to estimate spacing
    sample_size = min(100, len(df) - 1)
    total_distance = 0
    
    for i in range(sample_size):
        lat1, lon1 = df.iloc[i]['latitude'], df.iloc[i]['longitude']
        lat2, lon2 = df.iloc[i + 1]['latitude'], df.iloc[i + 1]['longitude']
        
        # Approximate distance in meters
        distance = ((lat2 - lat1)**2 + (lon2 - lon1)**2)**0.5 * 111000
        total_distance += distance
    
    return total_distance / sample_size

def create_heatmap_visualization(csv_file="nancy_road_points.csv", output_html="nancy_road_heatmap.html"):
    """
    Create a heatmap visualization of road point density
    
    Args:
        csv_file (str): Path to the CSV file containing road points
        output_html (str): Output HTML file name for the heatmap
    
    Returns:
        folium.Map: The created heatmap
    """
    
    try:
        from folium.plugins import HeatMap
        
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        if df.empty:
            print("❌ No records found in CSV file")
            return None
        
        print(f"🔥 Creating heatmap for {len(df)} road points...")
        
        # Calculate center point
        avg_lat = df['latitude'].mean()
        avg_lon = df['longitude'].mean()
        
        # Create base map
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Prepare data for heatmap (lat, lon, weight)
        heat_data = [[row['latitude'], row['longitude'], 1] for idx, row in df.iterrows()]
        
        # Add heatmap layer
        HeatMap(heat_data, radius=15, blur=10, max_zoom=1).add_to(map_viz)
        
        # Add Nancy boundary
        nancy_center_lat = 48.693167
        nancy_center_lon = 6.185472
        R_nancy = np.sqrt((nancy_center_lat - 48.667770)**2 + (6.146822 - nancy_center_lon)**2)
        nancy_radius = R_nancy * 111000
        
        folium.Circle(
            location=[nancy_center_lat, nancy_center_lon],
            radius=nancy_radius,
            color='blue',
            fill=False,
            popup="Nancy Boundary"
        ).add_to(map_viz)
        
        # Save heatmap
        map_viz.save(output_html)
        print(f"🔥 Heatmap saved as {output_html}")
        
        return map_viz
        
    except ImportError:
        print("❌ folium.plugins.HeatMap not available. Install with: pip install folium[extras]")
        return None
    except Exception as e:
        print(f"❌ Error creating heatmap: {e}")
        return None

# Add this to the end of map_download.py
if __name__ == "__main__":
    # Your existing code...
    
    # Add visualization calls
    print("\n" + "="*50)
    print("🗺️  VISUALIZATION SECTION")
    print("="*50)
    
    # Check if CSV file exists and visualize
    csv_file = "nancy_road_points.csv"
    
    try:
        # Test if file exists
        df_test = pd.read_csv(csv_file)
        print(f"📊 Found existing {csv_file} with {len(df_test)} points")
        
        # Create regular map visualization
        print("🗺️  Creating interactive map...")
        map_obj = visualize_road_points_on_map(csv_file, "nancy_road_points_map.html")
        
        # Create heatmap visualization
        print("🔥 Creating density heatmap...")
        heatmap_obj = create_heatmap_visualization(csv_file, "nancy_road_heatmap.html")
        
        if map_obj:
            print("✅ Interactive map created: nancy_road_points_map.html")
        if heatmap_obj:
            print("✅ Heatmap created: nancy_road_heatmap.html")
            
    except FileNotFoundError:
        print(f"⚠️  {csv_file} not found. Run road point generation first.")
        
        # Generate points first, then visualize
        print("🔄 Generating road points...")
        nancy_center_lon = 6.185472
        nancy_center_lat = 48.693167
        radius_km = 3  # Smaller radius for faster testing
        
        count = generate_road_points_in_circle(
            center_lon=nancy_center_lon,
            center_lat=nancy_center_lat,
            radius_km=radius_km,
            point_spacing_m=50,
            output_csv=csv_file
        )
        
        if count > 0:
            print(f"✅ Generated {count} points. Creating visualizations...")
            visualize_road_points_on_map(csv_file, "nancy_road_points_map.html")
            create_heatmap_visualization(csv_file, "nancy_road_heatmap.html")
    
    print("\n🎉 Visualization complete!")
    print("📁 Open these files in your browser:")
    print("   • nancy_road_points_map.html - Interactive point map")
    print("   • nancy_road_heatmap.html - Density heatmap")