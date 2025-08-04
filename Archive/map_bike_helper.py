from auto_walkthrough import *

if __name__ == "__main__":
    url_input = get_url_from_clipboard()
    print(f"Parking mode: parsing URL and downloading panoid")
    if url_input:
        print(f"Found URL in clipboard: {url_input[:80]}...")
    else:
        print("No valid URL found in clipboard.")
        
    # Parse the URL to extract panoid
    lat, lon, panoid = parse_google_maps_url(url_input)
    if panoid is None:
        print(f"❌ Could not extract panoid from URL: {url_input}")
        print("Make sure the URL is a valid Google Street View URL")
        exit(1)
    
    print(f"📍 Extracted panoid: {panoid} at location ({lat}, {lon})")
    
    # Run streetview downloader for single panoid with park output
    command = [
        "/home/arthur/Bureau/sviewscrap/StreetViewScraper/build/streetview_downloader",
        panoid,
        "-o", os.path.expanduser("~/streetview_output")
    ]
    
    print(f"📍 Extracted panoid: {panoid} at location ({lat}, {lon})")
    try:
        print(f"Running command: {' '.join(command)}")
        result = subprocess.run(command, check=True, capture_output=True, text=True)
        print(f"✅ Successfully downloaded panoid {panoid} to ~/streetview_output")
        print(f"📍 Location: {lat}, {lon}")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error downloading panoid {panoid}: {e}")
        print(f"stderr: {e.stderr}")
    except FileNotFoundError:
        print("❌ streetview_downloader executable not found. Check the path.")
            