"""
dem_utils.py

Library for downloading USGS 1 arc-second DEM tiles, caching them locally,
and generating a clipped DEM using GDAL.
"""

import os
import math
import subprocess

# Import from our new library modules
from .download_utils import download_file
from .bbox import BoundingBox

USGS_BASE = "https://prd-tnm.s3.amazonaws.com/StagedProducts/Elevation/1/TIFF/current"

# Updated cache directory per user request
DEFAULT_CACHE_DIR = "../data/extracted/dem"
DEFAULT_OUT_DIR = "../data/out"


# ---------------------------------------------------------
# Tile naming and URL construction
# ---------------------------------------------------------

def tile_name(lat, lon):
    """
    Convert integer lat/lon degrees to USGS tile key.
    Example: lat = 42, lon = -72  →  'n42w072'
    """
    lat_prefix = "n" if lat >= 0 else "s"
    lon_prefix = "e" if lon >= 0 else "w"
    return f"{lat_prefix}{abs(lat):02d}{lon_prefix}{abs(lon):03d}"


def tile_url(tile_key):
    """Return full HTTPS URL for a tile."""
    # Note: The file on server is USGS_1_{tile_key}.tif
    return f"{USGS_BASE}/{tile_key}/USGS_1_{tile_key}.tif"


# ---------------------------------------------------------
# Tile enumeration
# ---------------------------------------------------------

def tiles_for_bbox(bbox: BoundingBox):
    """
    Return a list of tile keys required to cover a bounding box.
    USGS 1 arc-second tiles are 1° × 1°.
    """
    lon_start = math.floor(bbox.xmin)
    lon_end = math.floor(bbox.xmax)

    lat_start = math.floor(bbox.ymin)
    lat_end = math.floor(bbox.ymax)

    tiles = []
    for lat in range(lat_start, lat_end + 1):
        for lon in range(lon_start, lon_end + 1):
            tiles.append(tile_name(lat, lon))

    return tiles


# ---------------------------------------------------------
# Download + cache
# ---------------------------------------------------------

def download_tile(tile_key, cache_dir=DEFAULT_CACHE_DIR):
    """
    Download tile into the cache directory unless already present.
    Returns the path to the .tif file.
    
    Note: Saves the file as '{tile_key}.tif', not the longer server name.
    """
    os.makedirs(cache_dir, exist_ok=True)

    # The local cache path is named after the key
    out_path = os.path.join(cache_dir, f"{tile_key}.tif")
    
    if os.path.exists(out_path):
        print(f"[CACHE] {tile_key}.tif already exists.")
        return out_path

    url = tile_url(tile_key)
    print(f"[DOWNLOAD] Fetching {tile_key} from {url}")

    success, msg = download_file(url, out_path)

    if not success:
        raise RuntimeError(f"Failed to download {url}: {msg}")

    return out_path


# ---------------------------------------------------------
# GDAL mosaic + clip
# ---------------------------------------------------------

def merge_and_clip(tile_paths, bbox: BoundingBox, out_dir=DEFAULT_OUT_DIR):
    """
    Create a VRT mosaic of the supplied tiles, then clip to bounding box.
    Returns the output .tif path.
    """
    os.makedirs(out_dir, exist_ok=True)

    vrt_path = os.path.join(out_dir, "_tmp_mosaic.vrt")
    out_path = os.path.join(
        out_dir,
        f"DEM_{bbox.xmin}_{bbox.ymin}_{bbox.xmax}_{bbox.ymax}.tif"
    )

    # Build mosaic VRT
    subprocess.run(
        ["gdalbuildvrt", vrt_path, *tile_paths],
        check=True
    )

    # Clip to bounding box using gdalwarp
    subprocess.run(
        [
            "gdalwarp",
            "-te", str(bbox.xmin), str(bbox.ymin), str(bbox.xmax), str(bbox.ymax),
            "-te_srs", "EPSG:4326", # Specify BBOX coordinate system
            "-dstalpha", # Add an alpha band for areas with no data
            vrt_path,
            out_path
        ],
        check=True
    )

    # Clean up the temporary VRT file
    if os.path.exists(vrt_path):
        os.remove(vrt_path)
        
    print(f"[DONE] Wrote clipped DEM to: {out_path}")
    return out_path


# ---------------------------------------------------------
# High-level entry point for external scripts
# ---------------------------------------------------------

def fetch_and_clip_dem(bbox: BoundingBox,
                       cache_dir=DEFAULT_CACHE_DIR,
                       out_dir=DEFAULT_OUT_DIR):
    """
    High-level utility that:
    1. Finds all tiles for the bounding box
    2. Downloads them (using cache)
    3. Mosaics + clips them
    4. Returns output DEM path
    """
    tiles = tiles_for_bbox(bbox)
    if not tiles:
        print("[WARN] No tiles found for the given bounding box.")
        return None
        
    print(f"[INFO] Tiles needed: {tiles}")

    tile_paths = []
    try:
        for tile_key in tiles:
            tile_paths.append(download_tile(tile_key, cache_dir=cache_dir))
    except RuntimeError as e:
        print(f"[ERROR] Failed during tile download: {e}")
        return None

    return merge_and_clip(
        tile_paths, bbox, out_dir=out_dir
    )

# Example Usage
if __name__ == "__main__":
    # Import BoundingBox for the example
    from bbox import BoundingBox
    
    # 1. Define parameters
    # BBOX for a region in Nebraska/South Dakota
    NE_SD_BBOX = BoundingBox(xmin=-103.0, ymin=42.8, xmax=-102.5, ymax=43.2)
    
    # 2. Run the process
    print("--- Fetching DEM ---")
    final_dem_path = fetch_and_clip_dem(
        bbox=NE_SD_BBOX,
        cache_dir=DEFAULT_CACHE_DIR,
        out_dir=DEFAULT_OUT_DIR
    )
    
    if final_dem_path:
        print(f"\nFinal DEM created at: {final_dem_path}")
    else:
        print("\nDEM creation failed.")