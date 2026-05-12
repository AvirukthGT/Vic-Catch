import requests
import json
import logging
import time
from pathlib import Path

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
RAW_DATA_DIR = Path("data/raw")
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = RAW_DATA_DIR / "melbourne_osm_raw.json"

# Melbourne Metro study area
MELB_SOUTH = -38.20
MELB_WEST = 144.40
MELB_NORTH = -37.50
MELB_EAST = 145.50

# ~11km tiles so I don't time out the API
STEP = 0.1 

def generate_tiles(south, west, north, east, step):
    """Split the study area into manageable tiles"""
    tiles = []
    current_lat = south
    while current_lat < north:
        current_lon = west
        while current_lon < east:
            tiles.append(
                f"{current_lat:.4f},{current_lon:.4f},{current_lat+step:.4f},{current_lon+step:.4f}"
            )
            current_lon += step
        current_lat += step
    return tiles

def fetch_tile(bbox_str):
    """Hit the API for one specific chunk"""
    query = f"""
    [out:json][timeout:120];
    (
      nwr["public_transport"~"platform|stop_position"]({bbox_str});
      nwr["highway"="bus_stop"]({bbox_str});
      nwr["railway"~"station|tram_stop|halt"]({bbox_str});
      way["highway"~"footway|path|pedestrian|steps"]({bbox_str});
      way["highway"]["sidewalk"]({bbox_str});
      way["highway"="cycleway"]({bbox_str});
      way["highway"]["cycleway"]({bbox_str});
      nwr["amenity"="bicycle_parking"]({bbox_str});
      nwr["amenity"~"parking|parking_entrance|parking_space"]({bbox_str});
      nwr["landuse"~"residential|commercial|retail|industrial|construction"]({bbox_str});
      nwr["amenity"~"school|hospital|university|clinic"]({bbox_str});
      nwr["shop"]({bbox_str});
    );
    out center tags;
    """
    
    headers = {'User-Agent': 'VicCatch-Transit-Project/0.1.0 (Analytics Engineering Portfolio)'}
    
    try:
        response = requests.post(OVERPASS_URL, data={'data': query}, headers=headers)
        if response.status_code == 429:
            logging.warning("Rate limited! Server requested a backoff. Sleeping for 30s...")
            time.sleep(30)
            return fetch_tile(bbox_str) # Try again
            
        response.raise_for_status()
        return response.json().get('elements', [])
        
    except Exception as e:
        logging.error(f"Failed to fetch tile {bbox_str}: {e}")
        return []

def run_tiled_extraction():
    tiles = generate_tiles(MELB_SOUTH, MELB_WEST, MELB_NORTH, MELB_EAST, STEP)
    logging.info(f"Generated {len(tiles)} tiles for Greater Melbourne.")
    
    unique_elements = {} # Key by ID to dedupe on the fly
    
    for i, bbox in enumerate(tiles):
        logging.info(f"Fetching tile {i+1}/{len(tiles)} [BBOX: {bbox}]...")
        elements = fetch_tile(bbox)
        
        for el in elements:
            unique_elements[el['id']] = el
            
        logging.info(f"Retrieved {len(elements)} items. Total unique items so far: {len(unique_elements)}")
        
        # Don't hammer the server (wait 8s between tiles)
        if i < len(tiles) - 1:
            time.sleep(8) 

    # Wrap it back into the standard Overpass JSON format
    final_payload = {
        "version": 0.6,
        "generator": "VicCatch Tiled Python Script",
        "elements": list(unique_elements.values())
    }
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)
        
    logging.info(f"Extraction complete! Saved {len(unique_elements)} unique features to {OUTPUT_FILE}")

if __name__ == "__main__":
    run_tiled_extraction()