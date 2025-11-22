#!/usr/bin/env python3

"""
CLI Script to download and clip USGS 1-arc-second DEM tiles for a given bounding box.
"""

import os
import sys
import argparse

# --- Path Setup ---
# This block allows the script to be run from anywhere and still find
# the 'lib' directory.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
sys.path.insert(0, PROJECT_ROOT)
# ------------------

# Now we can import from 'lib'
from lib.bbox import BoundingBox
# We need the updated dem_utils, which I'll provide below
from lib.dem_utils import fetch_and_clip_dem, DEFAULT_CACHE_DIR, DEFAULT_OUT_DIR

def main():
    parser = argparse.ArgumentParser(
        description="Fetch and clip USGS 1-arc-second DEM tiles for a Bounding Box."
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
        '--cache-dir',
        default=DEFAULT_CACHE_DIR,
        help=f"Directory to cache downloaded DEM tiles. Default: {DEFAULT_CACHE_DIR}"
    )
    
    parser.add_argument(
        '--out-dir',
        default=DEFAULT_OUT_DIR,
        help=f"Directory to save the final clipped DEM. Default: {DEFAULT_OUT_DIR}"
    )

    args = parser.parse_args()

    # Create the BoundingBox object from the CLI args
    bbox = BoundingBox(*args.bbox)

    print("--- 🏔️  Starting USGS DEM Download & Clip ---")
    print(f"Target BBox: {bbox}")
    print(f"Cache Dir: {args.cache_dir}")
    print(f"Output Dir: {args.out_dir}")

    try:
        final_dem_path = fetch_and_clip_dem(
            bbox=bbox,
            cache_dir=args.cache_dir,
            out_dir=args.out_dir
        )
        
        if final_dem_path:
            print(f"\n--- ✅  DEM Process Complete ---")
            print(f"Final clipped DEM saved to: {final_dem_path}")
        else:
            print("\n--- ⚠️  DEM Process Finished (No output) ---")

    except Exception as e:
        print(f"\n--- ❌  An Error Occurred ---")
        print(f"{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()