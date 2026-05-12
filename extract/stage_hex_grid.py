import h3
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

STAGED_FILE = Path("data/staged/stg_melbourne_hex_grid.parquet")

# Study area matching the Overpass script
MELB_SOUTH = -38.20
MELB_WEST = 144.40
MELB_NORTH = -37.50
MELB_EAST = 145.50

# Res 8 is the sweet spot for city precincts (~0.7 sq km per hex)
H3_RESOLUTION = 8 
def generate_hex_grid():
    logging.info(f"Generating H3 Resolution {H3_RESOLUTION} grid for Melbourne...")
    
    # Outer boundary: list of (Lat, Lon) tuples
    outer_boundary = [
        (MELB_SOUTH, MELB_WEST),
        (MELB_NORTH, MELB_WEST),
        (MELB_NORTH, MELB_EAST),
        (MELB_SOUTH, MELB_EAST)
    ]
    
    # h3 v4 needs LatLngPoly
    geo_polygon = h3.LatLngPoly(outer_boundary)

    # Fill the area with hex cells
    hex_ids = h3.polygon_to_cells(geo_polygon, H3_RESOLUTION)
    logging.info(f"Generated {len(hex_ids)} hex cells.")

    hex_data = []
    for hex_id in hex_ids:
        # Get the hex boundary
        boundary = h3.cell_to_boundary(hex_id)
        # H3 uses (lat, lon) but GeoPandas needs (lon, lat)
        flipped_boundary = [(lon, lat) for lat, lon in boundary]
        
        hex_data.append({
            'hex_id': hex_id,
            'geometry': Polygon(flipped_boundary)
        })

    # Wrap in a GeoDataFrame and force WGS84
    gdf = gpd.GeoDataFrame(hex_data, geometry='geometry', crs="EPSG:4326")
    
    STAGED_FILE.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_parquet(STAGED_FILE, index=False)
    
    logging.info(f"Successfully saved hex grid to {STAGED_FILE}")
    
if __name__ == "__main__":
    generate_hex_grid()