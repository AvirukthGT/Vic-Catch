import pandas as pd
from pathlib import Path
import logging

# Quick logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Config
RAW_DATA_DIR = Path("data/raw")
STAGED_DATA_DIR = Path("data/staged")

# Create staging if it doesn't exist
STAGED_DATA_DIR.mkdir(parents=True, exist_ok=True)

# PTV Victorian data uses these folder IDs for metro modes
TARGET_NETWORKS = {
    "2": "Metro Train",
    "3": "Metro Tram",
    "4": "Metro Bus"
}

def process_gtfs_files():
    all_stops = []
    all_routes = []

    for folder_id, network_name in TARGET_NETWORKS.items():
        folder_path = RAW_DATA_DIR / folder_id
        
        if not folder_path.exists():
            logging.warning(f"Folder {folder_id} ({network_name}) not found at {folder_path}. Skipping.")
            continue

        logging.info(f"Processing {network_name}...")

        # Stops: Force IDs to strings so Parquet doesn't choke on mixed types
        stops_file = folder_path / "stops.txt"
        if stops_file.exists():
            df_stops = pd.read_csv(
                stops_file, 
                dtype={
                    'stop_id': str, 
                    'stop_code': str, 
                    'zone_id': str, 
                    'parent_station': str
                },
                low_memory=False
            )
            df_stops['network_type'] = network_name
            all_stops.append(df_stops)

        # Routes: Same string enforcement for IDs
        routes_file = folder_path / "routes.txt"
        if routes_file.exists():
            df_routes = pd.read_csv(
                routes_file, 
                dtype={
                    'route_id': str, 
                    'agency_id': str, 
                    'route_short_name': str
                },
                low_memory=False
            )
            df_routes['network_type'] = network_name
            all_routes.append(df_routes)

    # Merge and save to parquet
    if all_stops:
        final_stops = pd.concat(all_stops, ignore_index=True)
        stops_output = STAGED_DATA_DIR / "stg_gtfs_stops.parquet"
        final_stops.to_parquet(stops_output, index=False)
        logging.info(f"Successfully saved {len(final_stops)} stops to {stops_output}")

    if all_routes:
        final_routes = pd.concat(all_routes, ignore_index=True)
        routes_output = STAGED_DATA_DIR / "stg_gtfs_routes.parquet"
        final_routes.to_parquet(routes_output, index=False)
        logging.info(f"Successfully saved {len(final_routes)} routes to {routes_output}")

if __name__ == "__main__":
    process_gtfs_files()