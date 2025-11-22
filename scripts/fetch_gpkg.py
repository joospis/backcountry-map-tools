#!/usr/bin/env python3

"""
CLI Script to download USGS Topo GPKG files for a given bounding box.
"""

import os
import sys
import argparse

# --- Path Setup ---
# This block allows the script to be run from anywhere and still find
# the 'lib' directory.
# 'SCRIPT_DIR' is 'proj/scripts'
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 'PROJECT_ROOT' is 'proj/'
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
# Add 'proj/' to the Python path
sys.path.insert(0, PROJECT_ROOT)
# ------------------

# Now we can import from 'lib'
from lib.bbox import BoundingBox
from lib.gpkg_utils import USGSTopoDownloader

def main():
    parser = argparse.ArgumentParser(
        description="Fetch USGS Topo GPKG files intersecting a Bounding Box."
    )
    
    parser.add_argument(
        '--bbox',
        required=True,
        nargs=4,
        type=float,
        metavar=('XMIN', 'YMIN', 'XMAX', 'YMAX'),
        help="Target bounding box in WGS84 (Lon/Lat). Example: -103.0 42.8 -102.5 43.2"
    )
    
    parser.add_argument(
        '--gdb',
        default="../data/MapIndices_National_GDB.gdb",
        help="Path to the MapIndices_National_GDB.gdb file."
    )
    
    parser.add_argument(
        '--format',
        default="GPKG",
        help="Download format (e.g., 'GPKG', 'ShapeFile')."
    )

    args = parser.parse_args()

    # Create the BoundingBox object from the CLI args
    bbox = BoundingBox(*args.bbox)

    print("--- 🗺️  Starting USGS Topo GPKG Download ---")
    print(f"Target BBox: {bbox}")
    print(f"Using GDB: {args.gdb}")

    try:
        downloader = USGSTopoDownloader(
            bbox=bbox,
            download_format=args.format,
            gdb_path=args.gdb
        )
        
        results = downloader.download_by_bbox()
        
        print("\n--- ✅  GPKG Download Complete ---")
        print(f"Final Results: {results}")

    except Exception as e:
        print(f"\n--- ❌  An Error Occurred ---")
        print(f"{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()