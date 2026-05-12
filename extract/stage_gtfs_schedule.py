import pandas as pd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

RAW_DATA_DIR = Path("data/raw")
STAGED_DATA_DIR = Path("data/staged")
STAGED_DATA_DIR.mkdir(parents=True, exist_ok=True)

TARGET_NETWORKS = {
    "2": "Metro Train",
    "3": "Metro Tram",
    "4": "Metro Bus"
}

def process_schedule_files():
    all_trips = []
    all_stop_times = []

    for folder_id, network_name in TARGET_NETWORKS.items():
        folder_path = RAW_DATA_DIR / folder_id
        
        if not folder_path.exists():
            continue

        logging.info(f"Processing schedule for {network_name}...")

        # Trips: Links routes to stop times
        trips_file = folder_path / "trips.txt"
        if trips_file.exists():
            df_trips = pd.read_csv(
                trips_file,
                # Grab only the columns I need to save memory
                usecols=['route_id', 'service_id', 'trip_id', 'direction_id', 'shape_id'],
                dtype={
                    'route_id': str, 
                    'service_id': str, 
                    'trip_id': str,
                    'direction_id': str,
                    'shape_id': str
                },
                low_memory=False
            )
            df_trips['network_type'] = network_name
            all_trips.append(df_trips)

        # Stop Times: This file is huge
        stop_times_file = folder_path / "stop_times.txt"
        if stop_times_file.exists():
            df_stop_times = pd.read_csv(
                stop_times_file,
                # Drop the columns I don't need
                usecols=['trip_id', 'arrival_time', 'departure_time', 'stop_id', 'stop_sequence'],
                dtype={
                    'trip_id': str,
                    'arrival_time': str,  # Keep as string—GTFS 25:00:00 rollovers break time parsers
                    'departure_time': str,
                    'stop_id': str,
                    'stop_sequence': int
                },
                low_memory=False
            )
            df_stop_times['network_type'] = network_name
            all_stop_times.append(df_stop_times)

    # Merge and dump trips to parquet
    if all_trips:
        final_trips = pd.concat(all_trips, ignore_index=True)
        trips_output = STAGED_DATA_DIR / "stg_gtfs_trips.parquet"
        final_trips.to_parquet(trips_output, index=False)
        logging.info(f"Saved {len(final_trips):,} trips to {trips_output}")

    # Merge and dump stop times to parquet
    if all_stop_times:
        final_stop_times = pd.concat(all_stop_times, ignore_index=True)
        stop_times_output = STAGED_DATA_DIR / "stg_gtfs_stop_times.parquet"
        final_stop_times.to_parquet(stop_times_output, index=False)
        logging.info(f"Saved {len(final_stop_times):,} stop times to {stop_times_output}")

if __name__ == "__main__":
    process_schedule_files()