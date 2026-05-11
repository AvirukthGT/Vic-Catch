import requests
import json
import logging
from pathlib import Path

# Basic logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Config
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RAW_DATA_DIR / "melbourne_osm_raw.json"

# BBOX for Melbourne Inner South/CBD area
BBOX = "-37.85, 144.90, -37.75, 145.05"

def fetch_overpass_data():
    logging.info(f"Building Overpass query for bounding box: {BBOX}")
    
    # Grab transit, walking, and landuse data for the engine
    query = f"""
    [out:json][timeout:120];
    (
      // Transit stops
      nwr["public_transport"~"platform|stop_position"]({BBOX});
      nwr["highway"="bus_stop"]({BBOX});
      nwr["railway"~"station|tram_stop|halt"]({BBOX});

      // Paths and sidewalks
      way["highway"~"footway|path|pedestrian|steps"]({BBOX});
      way["highway"]["sidewalk"]({BBOX});

      // Bike lanes
      way["highway"="cycleway"]({BBOX});
      way["highway"]["cycleway"]({BBOX});
      nwr["amenity"="bicycle_parking"]({BBOX});

      // Amenities and landuse
      nwr["amenity"~"parking|parking_entrance|parking_space"]({BBOX});
      nwr["landuse"~"residential|commercial|retail|industrial|construction"]({BBOX});
      nwr["amenity"~"school|hospital|university|clinic"]({BBOX});
      nwr["shop"]({BBOX});
    );
    out center tags;
    """
    
    logging.info("Sending POST request to Overpass API. This may take up to 2 minutes...")
    
    # Custom UA so we don't look like a generic scraper
    headers = {
        'User-Agent': 'VicCatch-Transit-Project/0.1.0 (Analytics Engineering Portfolio)'
    }
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, headers=headers)
        response.raise_for_status() 
        
        data = response.json()
        elements_count = len(data.get('elements', []))
        logging.info(f"Success! Retrieved {elements_count} spatial features.")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        logging.info(f"Raw OSM data safely landed in {OUTPUT_FILE}")
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Network or API failure: {e}")
    except json.JSONDecodeError:
        logging.error("Failed to parse the response as JSON. The API might have returned an HTML error page.")

if __name__ == "__main__":
    fetch_overpass_data()