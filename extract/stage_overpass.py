import json
import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

RAW_FILE = Path("data/raw/melbourne_osm_raw.json")
STAGED_FILE = Path("data/staged/stg_osm_features.parquet")

def categorize_feature(tags):
    """Map raw OSM tags to my business domains for easier filtering in BQ"""
    if not tags:
        return "uncategorized"
        
    # Public transport
    if tags.get("public_transport") in ["platform", "stop_position"] or tags.get("railway") in ["station", "tram_stop", "halt"]:
        return "transit_node"
    if tags.get("highway") == "bus_stop":
        return "transit_node"
        
    # Walk/Bike paths
    if tags.get("highway") in ["footway", "path", "pedestrian", "steps"] or "sidewalk" in tags:
        return "walkway"
    if tags.get("highway") == "cycleway" or "cycleway" in tags:
        return "cycleway"
    if tags.get("amenity") == "bicycle_parking":
        return "bike_parking"
        
    # Land use and amenities
    if tags.get("landuse") in ["commercial", "retail", "residential"]:
        return f"zone_{tags.get('landuse')}"
    if "shop" in tags:
        return "retail_shop"
    if tags.get("amenity") in ["school", "university", "hospital", "clinic"]:
        return "civic_amenity"
    if tags.get("amenity") in ["parking", "parking_entrance", "parking_space"]:
        return "parking"

    return "other"

def process_osm_json():
    if not RAW_FILE.exists():
        logging.error(f"Cannot find {RAW_FILE}. Run fetch_overpass.py first.")
        return

    logging.info(f"Loading raw JSON from {RAW_FILE}...")
    with open(RAW_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    elements = data.get('elements', [])
    logging.info(f"Parsing {len(elements)} elements...")

    parsed_data = []

    for el in elements:
        # Coords: check lat/lon directly (nodes) or the center block (ways/relations)
        lat = el.get('lat') or el.get('center', {}).get('lat')
        lon = el.get('lon') or el.get('center', {}).get('lon')

        if not lat or not lon:
            continue # Skip if no coords

        tags = el.get('tags', {})
        feature_group = categorize_feature(tags)

        parsed_data.append({
            'osm_id': str(el['id']),
            'osm_type': el['type'],
            'feature_group': feature_group,
            'lat': float(lat),
            'lon': float(lon),
            # Save raw tags as JSON just in case I need more detail later
            'raw_tags': json.dumps(tags) 
        })

    # Wrapping it in a dataframe and dump to parquet
    df = pd.DataFrame(parsed_data)
    
    STAGED_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(STAGED_FILE, index=False)
    
    logging.info(f"Successfully staged {len(df)} spatial features into {STAGED_FILE}")
    
    # Quick summary of what I found
    logging.info("\nFeature Group Breakdown:")
    logging.info(df['feature_group'].value_counts())

if __name__ == "__main__":
    process_osm_json()