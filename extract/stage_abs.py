import pandas as pd
import geopandas as gpd
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

ABS_DIR = Path("data/raw/abs")
STAGED_FILE = Path("data/staged/stg_abs_demographics.parquet")

def process_abs_data():
    if not ABS_DIR.exists():
        logging.error("ABS directory not found.")
        return

    # Boundaries: Load SA1 polygons
    boundary_file = ABS_DIR / "SA1_2021_AUST_GDA2020.shp" 
    logging.info(f"Loading SA1 boundaries from {boundary_file}...")
    
    gdf_boundaries = gpd.read_file(boundary_file)
    
    # Filter for Vic (State '2') and Greater Melb ('2GMEL')
    gdf_vic = gdf_boundaries[gdf_boundaries['STE_CODE21'] == '2'].copy()
    gdf_melb = gdf_vic[gdf_vic['GCC_CODE21'] == '2GMEL'].copy()
    logging.info(f"Filtered down to {len(gdf_melb)} SA1 polygons in Greater Melbourne.")

    # Demographics: Load person characteristics
    demo_file = ABS_DIR / "2021Census_G01_VIC_SA1.csv"
    logging.info(f"Loading demographics from {demo_file}...")
    
    df_demo = pd.read_csv(demo_file)
    
    # Fix the join key: force to string to match the shapefile
    df_demo['SA1_CODE21'] = df_demo['SA1_CODE_2021'].astype(str)

    # Join the map with the stats
    logging.info("Joining spatial polygons with demographic counts...")
    gdf_staged = gdf_melb.merge(df_demo, on='SA1_CODE21', how='inner')

    if len(gdf_staged) == 0:
        logging.error("Join failed—zero matches. Check the keys.")
        return

    # Cleanup: just keep SA1 code, total pop, and geometry
    columns_to_keep = [
        'SA1_CODE21', 
        'Tot_P_P', 
        'geometry' 
    ]
    
    gdf_final = gdf_staged[columns_to_keep].rename(columns={
        'Tot_P_P': 'total_population'
    })

    # Dump to GeoParquet
    logging.info(f"Success! Saving {len(gdf_final)} populated areas to {STAGED_FILE}...")
    
    STAGED_FILE.parent.mkdir(parents=True, exist_ok=True)
    gdf_final.to_parquet(STAGED_FILE, index=False)
    
    logging.info("ABS Data Staging Complete.")

if __name__ == "__main__":
    process_abs_data()