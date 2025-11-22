import os
import time
import requests
import zipfile
import shutil

def download_file(url, local_filepath, stream=True, timeout=30, chunk_size=8192):
    """
    Downloads a file from a URL to a local path.

    Args:
        url (str): The URL to download from.
        local_filepath (str): The local path to save the file.
        stream (bool, optional): Whether to stream the download. Defaults to True.
        timeout (int, optional): Request timeout. Defaults to 30.
        chunk_size (int, optional): Download chunk size. Defaults to 8192.

    Returns:
        tuple: (bool, str) indicating (success, message_or_None)
    """
    try:
        # Ensure the target directory exists
        os.makedirs(os.path.dirname(local_filepath), exist_ok=True)
            
        with requests.get(url, stream=stream, timeout=timeout) as r:
            # Short pause to be polite to the server
            time.sleep(0.5) 
            
            r.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            
            total_size = int(r.headers.get('content-length', 0))
            if total_size == 0:
                return False, f"File size is 0 bytes at {url}"

            print(f"  [INFO] Downloading {url} ({total_size/1024**2:.2f} MB)")
            
            with open(local_filepath, 'wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size): 
                    f.write(chunk)

            print(f"  [SUCCESS] Downloaded to: {local_filepath}")
            return True, None

    except requests.exceptions.HTTPError as errh:
        return False, f"HTTP Error for {url}: {errh}"
    except requests.exceptions.RequestException as err:
        return False, f"An unexpected error occurred for {url}: {err}"

def extract_zip_and_rename(zip_path, extract_dir, file_extension=".gpkg"):
    """
    Extracts the first file with file_extension from a zip, renames it to
    match the zip's basename (with new extension), saves it to extract_dir,
    and deletes the zip.

    Args:
        zip_path (str): Path to the .zip file.
        extract_dir (str): Directory to extract to.
        file_extension (str, optional): The extension to look for. Defaults to ".gpkg".

    Returns:
        tuple: (bool, str) indicating (success, path_to_extracted_file_or_error_msg)
    """
    os.makedirs(extract_dir, exist_ok=True)
    
    # 1. Determine the final target name
    zip_basename = os.path.basename(zip_path)
    target_basename = os.path.splitext(zip_basename)[0] + file_extension
    target_path = os.path.join(extract_dir, target_basename)

    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Find the first file matching the extension
            target_file_info = None
            for f_info in zip_ref.infolist():
                if f_info.filename.endswith(file_extension):
                    target_file_info = f_info
                    break
                    
            if not target_file_info:
                return False, f"No '{file_extension}' file found in {zip_path}"

            # 2. Extract the file, ensuring it's flat in the extract_dir
            # This prevents files zipped with internal paths (e.g., 'folder/file.gpkg')
            # from creating 'extract_dir/folder/file.gpkg'.
            original_filename = target_file_info.filename
            target_file_info.filename = os.path.basename(original_filename)
            
            extracted_file_path = zip_ref.extract(target_file_info, path=extract_dir)

            # 3. Rename extracted file to our standard target_path
            if extracted_file_path != target_path:
                shutil.move(extracted_file_path, target_path)
            
            print(f"  [SUCCESS] Extracted and saved to: {target_path}")

        # 4. Cleanup the zip file
        os.remove(zip_path)
        print(f"  [INFO] Cleaned up zip: {zip_path}")
        
        return True, target_path

    except zipfile.BadZipFile:
        os.remove(zip_path) # Clean up corrupted zip
        return False, f"Bad zip file (deleted): {zip_path}"
    except Exception as e:
        return False, f"Failed to extract/cleanup {zip_path}: {e}"