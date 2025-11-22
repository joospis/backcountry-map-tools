import os
import time
from osgeo import ogr

# Import from our new library modules
from .download_utils import download_file, extract_zip_and_rename
from .bbox import BoundingBox

# Base URL for the staged USGS Topo Map Vector products
BASE_URL = "https://prd-tnm.s3.amazonaws.com/StagedProducts/TopoMapVector/"

# --- FIXED PATHS ---
# Get the directory of this file (proj/lib)
LIB_DIR = os.path.dirname(os.path.abspath(__file__))
# Get the project root directory (proj)
PROJECT_ROOT = os.path.abspath(os.path.join(LIB_DIR, '..'))
# Define data paths based on the project root
DATA_DIR = os.path.join(PROJECT_ROOT, 'data')

GDB_FILE = os.path.join(DATA_DIR, "MapIndices_National_GDB.gdb")
RAW_DIR = os.path.join(DATA_DIR, "raw", "gpkg")
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted", "gpkg")
# --- END FIXED PATHS ---


class USGSTopoDownloader:
    """
    Queries the national USGS Map Index GDB for 7.5-minute quadrangle
    data intersecting a bounding box and downloads/extracts the GPKG files.
    """
    def __init__(self, bbox: BoundingBox, download_format="GPKG", gdb_path: str = GDB_FILE):
        """
        Initializes the downloader.

        Args:
            gdb_path (str): Path to the national map index GDB (e.g., "MapIndices_National_GDB.gdb").
            bbox (BoundingBox): The target BoundingBox object (WGS84 Lon/Lat).
            download_format (str, optional): The file format. Defaults to "GPKG".
        """
        self.gdb_path = gdb_path
        self.bbox = bbox
        self.raw_dir = RAW_DIR
        self.extracted_dir = EXTRACTED_DIR
        self.download_format = download_format
        self.layer_name = "CellGrid_7_5Minute"
        
        # Ensure the data directories exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.extracted_dir, exist_ok=True)
        
        # Configure OGR to raise exceptions on errors
        ogr.UseExceptions()

    @staticmethod
    def _get_quad_info(cell_name, state_alpha_field):
        """
        Extracts the cleaned quad name and the primary state abbreviation.
        """
        if not state_alpha_field:
            print(f"  [ERROR] STATE_ALPHA field is empty for: {cell_name}. Skipping.")
            return None
            
        state_abbr = state_alpha_field.split(',')[0].strip()
        quad_name_for_url = cell_name.strip().replace(' ', '_')

        return quad_name_for_url, state_abbr

    def _process_quad(self, quad_name, state_abbr):
        """
        Constructs URLs, checks cache, downloads, and extracts the file.
        """
        # 1. Define filenames and paths
        zip_filename = f"VECTOR_{quad_name}_{state_abbr}_7_5_Min_{self.download_format}.zip"
        gpkg_filename = f"VECTOR_{quad_name}_{state_abbr}_7_5_Min_{self.download_format}.gpkg"
        
        zip_filepath = os.path.join(self.raw_dir, zip_filename)
        gpkg_filepath = os.path.join(self.extracted_dir, gpkg_filename)
        
        full_url = f"{BASE_URL}{state_abbr.upper()}/{self.download_format}/{zip_filename}"
        
        print(f"\nAttempting to process: {quad_name} ({state_abbr})")

        # 2. Check for cache (in the extracted directory)
        if os.path.exists(gpkg_filepath):
            print(f"  [INFO] File already exists, skipping download (Cached).")
            print(f"  Path: {gpkg_filepath}")
            return True

        print(f"  URL: {full_url}")

        # 3. Attempt Download
        download_success, dl_msg = download_file(full_url, zip_filepath)
        
        if not download_success:
            print(f"  [ERROR] Download failed: {dl_msg}")
            # If the zip exists but is bad, clean it up
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)
            return False

        # 4. Attempt Extract and Cleanup
        extract_success, ext_msg = extract_zip_and_rename(
            zip_filepath, 
            self.extracted_dir, 
            file_extension=f".{self.download_format.lower()}"
        )

        if not extract_success:
            print(f"  [ERROR] Extraction failed: {ext_msg}")
            return False
        
        return True

    def download_by_bbox(self):
        """
        Reads the GDB, applies the spatial filter, and triggers downloads.
        
        Returns:
            dict: Summary of the operation.
        """
        if not os.path.exists(self.gdb_path):
            return {"status": "FAILED", "message": f"GDB file not found at: {self.gdb_path}"}

        print(f"[INFO] GPKG cache directory: {self.extracted_dir}")
        print(f"[INFO] Target BBOX (Lon/Lat): {self.bbox}")

        dataSource = None
        try:
            driver = ogr.GetDriverByName("OpenFileGDB")
            dataSource = driver.Open(self.gdb_path, 0)

            if dataSource is None:
                return {"status": "FAILED", "message": f"Could not open {self.gdb_path}."}

            layer = dataSource.GetLayer(self.layer_name)
            if layer is None:
                return {"status": "FAILED", "message": f"Could not find layer {self.layer_name}."}
                
            # 1. Set Spatial Filter (BBOX)
            # The BoundingBox NamedTuple unpacks in the correct order
            layer.SetSpatialFilterRect(*self.bbox) 
            
            srs = layer.GetSpatialRef()
            srs_info = srs.ExportToWkt().splitlines()[0] if srs else "UNKNOWN"
            print(f"[INFO] GDB Layer SRS: {srs_info}")
            
            # 2. Iterate over filtered features
            processed_quads = set()
            features_found = 0
            downloads_successful = 0

            print("\n--- Starting Query and Download Loop ---")
            for feature in layer:
                features_found += 1
                
                cell_name = feature.GetField("CELL_NAME")
                state_alpha_field = feature.GetField("STATE_ALPHA")
                
                quad_info = self._get_quad_info(cell_name, state_alpha_field)
                
                if quad_info:
                    quad_name, state_abbr = quad_info
                    quad_key = f"{quad_name}_{state_abbr}"
                    
                    if quad_key in processed_quads:
                        continue
                    processed_quads.add(quad_key)
                    
                    # 4. Download, Extract, and Cache
                    if self._process_quad(quad_name, state_abbr):
                        downloads_successful += 1
                    
            # --- Summary ---
            summary = {
                "status": "SUCCESS",
                "features_found": features_found,
                "unique_quads_identified": len(processed_quads),
                "downloads_successful": downloads_successful
            }
            print("\n--- Process Complete ---")
            print(f"Features found intersecting BBOX in GDB: {summary['features_found']}")
            print(f"Unique 7.5-minute Quads identified: {summary['unique_quads_identified']}")
            print(f"Total Quads successfully downloaded/cached: {summary['downloads_successful']}")
            return summary

        except Exception as e:
            print(f"\n[CRITICAL ERROR] A geospatial or file error occurred: {e}")
            return {"status": "CRITICAL_ERROR", "message": str(e)}
        finally:
            if dataSource:
                del dataSource
                
# ... (if __name__ == "__main__" block remains the same) ...