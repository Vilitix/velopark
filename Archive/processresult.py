import folium
import psycopg2
from pathlib import Path

def create_velopark_review_html(output_file="velopark_review.html"):
    """
    Create an interactive HTML map for reviewing AI-detected bicycle parking locations.
    Includes Street View links and approve/reject buttons for each detection.
    """
    conn = None
    cursor = None
    
    try:
        # Connect to database
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        # Create processed_data table if it doesn't exist
        create_processed_data_table(cursor, conn)
        
        # Get all unprocessed velopark records (using id as unique identifier)
        cursor.execute("""
            SELECT v.id, v.latitude, v.longitude, v.panoid
            FROM velopark v
            LEFT JOIN processed_data pd ON v.id = pd.velopark_id
            WHERE pd.velopark_id IS NULL
            ORDER BY v.latitude DESC, v.longitude DESC
        """)
        
        records = cursor.fetchall()
        
        if not records:
            print("📊 No unprocessed records found in velopark table")
            return
        
        print(f"📊 Found {len(records)} unprocessed detections to review")
        
        # Calculate center point (average of all coordinates)
        avg_lat = sum(record[1] for record in records) / len(records)
        avg_lon = sum(record[2] for record in records) / len(records)
        
        # Create map centered on average coordinates
        map_viz = folium.Map(
            location=[avg_lat, avg_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )
        
        # Add markers for each detection
        for i, (velopark_id, lat, lon, pano_id) in enumerate(records):
            
            # Create popup with information and action buttons
            popup_html = f"""
            <div style="width: 350px; font-family: Arial, sans-serif;">
                <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; margin-bottom: 10px;">
                    <h4 style="margin: 0; color: #2c3e50;">🚴 Detection #{velopark_id}</h4>
                    <p style="margin: 5px 0; font-size: 12px; color: #7f8c8d;">
                        AI Detection from Street View Analysis
                    </p>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <p style="margin: 3px 0;"><strong>📍 Location:</strong> {lat:.6f}, {lon:.6f}</p>
                    <p style="margin: 3px 0;"><strong>🆔 Pano ID:</strong> {pano_id}</p>
                </div>
                
                <div style="margin-bottom: 15px;">
                    <a href="https://www.google.com/maps/@{lat},{lon},3a,75y,0h,90t/data=!3m4!1e1!3m2!1s{pano_id}!2e0" 
                       target="_blank" 
                       style="display: inline-block; background-color: #4285f4; color: white; padding: 8px 12px; 
                              text-decoration: none; border-radius: 4px; font-size: 14px; margin-right: 5px;">
                        🗺️ View in Street View
                    </a>
                    <a href="https://www.google.com/maps/@{lat},{lon},19z" 
                       target="_blank" 
                       style="display: inline-block; background-color: #34a853; color: white; padding: 8px 12px; 
                              text-decoration: none; border-radius: 4px; font-size: 14px;">
                        🌍 View on Map
                    </a>
                </div>
                
                <div style="border-top: 1px solid #ddd; padding-top: 15px;">
                    <p style="margin: 0 0 10px 0; font-weight: bold; color: #2c3e50;">
                        Review this detection:
                    </p>
                    <div style="display: flex; gap: 10px;">
                        <button onclick="processDetection({velopark_id}, true)" 
                                style="flex: 1; background-color: #27ae60; color: white; border: none; 
                                       padding: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            ✅ Keep (Valid)
                        </button>
                        <button onclick="processDetection({velopark_id}, false)" 
                                style="flex: 1; background-color: #e74c3c; color: white; border: none; 
                                       padding: 10px; border-radius: 4px; cursor: pointer; font-size: 14px;">
                            ❌ Reject (Invalid)
                        </button>
                    </div>
                </div>
                
                <div id="status_{velopark_id}" style="margin-top: 10px; padding: 5px; border-radius: 3px; 
                     text-align: center; font-size: 12px; display: none;">
                </div>
            </div>
            """
            
            # Use blue markers for all detections (since we don't have confidence data)
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=400),
                tooltip=f"Detection #{velopark_id} | {pano_id}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(map_viz)
        
        # Add JavaScript for handling button clicks
        javascript_code = """
        <script>
        let processedCount = 0;
        const totalDetections = """ + str(len(records)) + """;
        
        function processDetection(veloparkId, isValid) {
            const statusDiv = document.getElementById('status_' + veloparkId);
            
            // Show processing message
            statusDiv.style.display = 'block';
            statusDiv.style.backgroundColor = '#f39c12';
            statusDiv.style.color = 'white';
            statusDiv.innerHTML = '⏳ Processing...';
            
            // For local file testing, simulate the backend response
            setTimeout(() => {
                processedCount++;
                statusDiv.style.backgroundColor = isValid ? '#27ae60' : '#e74c3c';
                statusDiv.innerHTML = isValid ? '✅ Kept as valid' : '❌ Marked as invalid';
                
                // Update progress
                updateProgress();
                
                // Disable buttons
                const buttons = statusDiv.parentElement.querySelectorAll('button');
                buttons.forEach(btn => {
                    btn.disabled = true;
                    btn.style.opacity = '0.5';
                    btn.style.cursor = 'not-allowed';
                });
                
                // Store decision in localStorage for persistence
                const decisions = JSON.parse(localStorage.getItem('velopark_decisions') || '{}');
                decisions[veloparkId] = {
                    is_valid: isValid,
                    timestamp: new Date().toISOString()
                };
                localStorage.setItem('velopark_decisions', JSON.stringify(decisions));
                
            }, 1000);
        }
        
        function updateProgress() {
            const progressDiv = document.getElementById('progress-info');
            if (progressDiv) {
                const percentage = Math.round((processedCount / totalDetections) * 100);
                progressDiv.innerHTML = `Progress: ${processedCount}/${totalDetections} (${percentage}%)`;
                
                if (processedCount === totalDetections) {
                    progressDiv.innerHTML += ' - ✅ All detections reviewed!';
                    progressDiv.style.backgroundColor = '#27ae60';
                    
                    // Show export button
                    showExportButton();
                }
            }
        }
        
        function showExportButton() {
            const exportBtn = document.createElement('button');
            exportBtn.innerHTML = '📥 Export Decisions';
            exportBtn.style.cssText = `
                position: fixed; bottom: 20px; right: 20px; 
                background-color: #3498db; color: white; border: none; 
                padding: 12px 20px; border-radius: 5px; cursor: pointer; 
                font-size: 14px; z-index: 1000;
            `;
            exportBtn.onclick = exportDecisions;
            document.body.appendChild(exportBtn);
        }
        
        function exportDecisions() {
            const decisions = JSON.parse(localStorage.getItem('velopark_decisions') || '{}');
            const csvContent = "velopark_id,is_valid,reviewed_at\\n" +
                Object.entries(decisions).map(([id, decision]) => 
                    `${id},${decision.is_valid},${decision.timestamp}`
                ).join('\\n');
            
            const blob = new Blob([csvContent], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'velopark_review_decisions.csv';
            a.click();
            window.URL.revokeObjectURL(url);
        }
        
        // Load previous decisions from localStorage
        window.onload = function() {
            const decisions = JSON.parse(localStorage.getItem('velopark_decisions') || '{}');
            Object.entries(decisions).forEach(([veloparkId, decision]) => {
                const statusDiv = document.getElementById('status_' + veloparkId);
                if (statusDiv) {
                    statusDiv.style.display = 'block';
                    statusDiv.style.backgroundColor = decision.is_valid ? '#27ae60' : '#e74c3c';
                    statusDiv.innerHTML = decision.is_valid ? '✅ Kept as valid' : '❌ Marked as invalid';
                    
                    // Disable buttons
                    const buttons = statusDiv.parentElement.querySelectorAll('button');
                    buttons.forEach(btn => {
                        btn.disabled = true;
                        btn.style.opacity = '0.5';
                        btn.style.cursor = 'not-allowed';
                    });
                    
                    processedCount++;
                }
            });
            updateProgress();
        };
        </script>
        """
        
        # Add the JavaScript to the map
        map_viz.get_root().html.add_child(folium.Element(javascript_code))
        
        # Add a progress indicator
        progress_html = f"""
        <div style="position: fixed; top: 10px; right: 10px; background-color: #3498db; 
             color: white; padding: 10px; border-radius: 5px; z-index: 1000; 
             font-family: Arial, sans-serif;">
            <div id="progress-info">Progress: 0/{len(records)} (0%)</div>
        </div>
        """
        map_viz.get_root().html.add_child(folium.Element(progress_html))
        
        # Save the map
        output_path = Path(output_file)
        map_viz.save(str(output_path))
        
        print(f"✅ Interactive review map created: {output_path.absolute()}")
        print(f"📊 {len(records)} detections ready for review")
        print(f"🌐 Open {output_file} in your web browser to start reviewing")
        print(f"💾 Decisions will be saved locally and can be exported as CSV")
        
        return str(output_path.absolute())
        
    except Exception as e:
        print(f"❌ Error creating review map: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def create_processed_data_table(cursor, conn):
    """
    Create processed_data table if it doesn't exist
    """
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS processed_data (
                id SERIAL PRIMARY KEY,
                velopark_id INTEGER NOT NULL,
                is_valid BOOLEAN NOT NULL,
                reviewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notes TEXT,
                UNIQUE(velopark_id)
            );
        """)
        
        # Create index for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_processed_data_velopark_id 
            ON processed_data(velopark_id);
        """)
        
        conn.commit()
        print("✅ processed_data table ready")
        
    except Exception as e:
        print(f"⚠️ Could not create processed_data table: {e}")


def import_decisions_from_csv(csv_file_path):
    """
    Import review decisions from CSV file to database
    
    Args:
        csv_file_path (str): Path to the CSV file with decisions
    """
    import csv
    
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        # Create processed_data table if needed
        create_processed_data_table(cursor, conn)
        
        imported_count = 0
        
        with open(csv_file_path, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for row in reader:
                velopark_id = int(row['velopark_id'])
                is_valid = row['is_valid'].lower() == 'true'
                
                cursor.execute("""
                    INSERT INTO processed_data (velopark_id, is_valid)
                    VALUES (%s, %s)
                    ON CONFLICT (velopark_id) DO UPDATE SET
                        is_valid = EXCLUDED.is_valid,
                        reviewed_at = CURRENT_TIMESTAMP
                """, (velopark_id, is_valid))
                
                imported_count += 1
        
        conn.commit()
        print(f"✅ Imported {imported_count} decisions to database")
        
    except Exception as e:
        print(f"❌ Error importing decisions: {e}")
        if conn:
            conn.rollback()
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def process_detection_decision(velopark_id, is_valid, notes=None):
    """
    Process a human decision about a detection
    
    Args:
        velopark_id (int): ID of the velopark record
        is_valid (bool): Whether the detection is valid
        notes (str): Optional notes about the decision
    
    Returns:
        bool: Success status
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        # Insert the decision
        cursor.execute("""
            INSERT INTO processed_data (velopark_id, is_valid, notes)
            VALUES (%s, %s, %s)
            ON CONFLICT (velopark_id) DO UPDATE SET
                is_valid = EXCLUDED.is_valid,
                reviewed_at = CURRENT_TIMESTAMP,
                notes = EXCLUDED.notes
        """, (velopark_id, is_valid, notes))
        
        conn.commit()
        
        print(f"✅ Processed detection {velopark_id}: {'Valid' if is_valid else 'Invalid'}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing decision: {e}")
        if conn:
            conn.rollback()
        return False
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

def get_review_statistics():
    """
    Get statistics about the review process
    """
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="imagedb",
            user="arthur",
            password=""
        )
        
        cursor = conn.cursor()
        
        # Get overall statistics
        cursor.execute("SELECT COUNT(*) FROM velopark")
        total_detections = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data")
        reviewed_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data WHERE is_valid = true")
        valid_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM processed_data WHERE is_valid = false")
        invalid_count = cursor.fetchone()[0]
        
        pending_count = total_detections - reviewed_count
        
        print(f"📊 REVIEW STATISTICS")
        print(f"=" * 40)
        print(f"Total AI detections: {total_detections}")
        print(f"Reviewed: {reviewed_count}")
        print(f"Pending review: {pending_count}")
        print(f"Valid detections: {valid_count}")
        print(f"Invalid detections: {invalid_count}")
        
        if reviewed_count > 0:
            accuracy = (valid_count / reviewed_count) * 100
            print(f"AI Accuracy: {accuracy:.1f}%")
        
        return {
            'total': total_detections,
            'reviewed': reviewed_count,
            'pending': pending_count,
            'valid': valid_count,
            'invalid': invalid_count
        }
        
    except Exception as e:
        print(f"❌ Error getting statistics: {e}")
        return None
    
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Example usage and testing functions
def batch_process_decisions(decisions):
    """
    Process multiple decisions at once
    
    Args:
        decisions (list): List of tuples (velopark_id, is_valid, notes)
    """
    success_count = 0
    for velopark_id, is_valid, notes in decisions:
        if process_detection_decision(velopark_id, is_valid, notes):
            success_count += 1
    
    print(f"✅ Processed {success_count}/{len(decisions)} decisions successfully")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats":
            get_review_statistics()
        elif sys.argv[1] == "--create":
            create_velopark_review_html()
        else:
            print("Usage: python process_result.py [--stats|--create]")
    else:
        # Default action: create the review map
        create_velopark_review_html()
        get_review_statistics()