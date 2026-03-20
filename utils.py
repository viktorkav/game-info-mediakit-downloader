import os
import subprocess
import sys
import requests
import zipfile
from datetime import datetime

def get_high_res_url(url):
    """Converts IGDB thumbnail URL to 1080p URL."""
    if not url:
        return None
    if url.startswith("//"):
        url = "https:" + url
    return url.replace("t_thumb", "t_original")

import mimetypes


def reveal_in_file_manager(path):
    """Opens the system file manager and highlights the given file."""
    if sys.platform == "darwin":
        subprocess.call(["open", "-R", path])
    elif sys.platform == "win32":
        subprocess.call(["explorer", "/select,", os.path.normpath(path)])
    else:
        subprocess.call(["xdg-open", os.path.dirname(path)])

def download_image(url, save_path_base):
    """Downloads an image and saves it with the correct extension."""
    url = get_high_res_url(url)
    if not url:
        return None
    
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Detect extension
        content_type = response.headers.get('content-type')
        ext = mimetypes.guess_extension(content_type)
        if not ext:
            # Fallback to URL extension or .jpg
            if ".png" in url: ext = ".png"
            elif ".webp" in url: ext = ".webp"
            else: ext = ".jpg"
            
        # Ensure common extensions are clean
        if ext == '.jpeg': ext = '.jpg'
        
        final_path = f"{save_path_base}{ext}"
        
        with open(final_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return final_path
    except Exception as e:
        print(f"Failed to download {url}: {e}")
        return None

import tempfile
import shutil

def create_mediakit(game_data, output_dir_root=".", progress_callback=None):
    """Creates mediakit in a temp dir, zips it, and saves only the zip to output_dir."""
    game_name = game_data.get("name", "Unknown Game")
    safe_name = "".join([c for c in game_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip()
    
    # Calculate total steps for progress
    # 1 (setup/info) + 1 (cover) + len(screenshots) + len(artworks) + 1 (zip)
    total_steps = 1 + 1 + len(game_data.get("screenshots", [])) + len(game_data.get("artworks", [])) + 1
    current_step = 0

    def update_progress(msg="Working..."):
        nonlocal current_step
        current_step += 1
        pct = min(current_step / total_steps, 0.99) # Keep 1.0 for final completion
        if progress_callback:
            progress_callback(pct, msg)

    with tempfile.TemporaryDirectory() as temp_dir:
        base_dir = os.path.join(temp_dir, safe_name)
        media_dir = os.path.join(base_dir, "media")
        
        # Create directories
        os.makedirs(media_dir, exist_ok=True)
        
        # 1. Create info.md
        info_path = os.path.join(base_dir, "info.md")
        with open(info_path, "w", encoding="utf-8") as f:
            f.write(f"# {game_name}\n\n")
            
            rel_date = game_data.get("first_release_date")
            if rel_date:
                dt = datetime.fromtimestamp(rel_date)
                f.write(f"**Release Date:** {dt.strftime('%Y-%m-%d')}\n\n")

            # Developer / Publisher
            companies = game_data.get("involved_companies", [])
            developers = [c.get("company", {}).get("name") for c in companies if c.get("developer")]
            publishers = [c.get("company", {}).get("name") for c in companies if c.get("publisher")]
            
            if developers:
                f.write(f"**Developer:** {', '.join(developers)}\n")
            if publishers:
                f.write(f"**Publisher:** {', '.join(publishers)}\n")
            f.write("\n")

            # Genres
            genres = game_data.get("genres", [])
            if genres:
                genre_names = [g.get("name") for g in genres]
                f.write(f"**Genres:** {', '.join(genre_names)}\n\n")

            # Platforms
            platforms = game_data.get("platforms", [])
            if platforms:
                platform_names = [p.get("name") for p in platforms]
                f.write(f"**Platforms:** {', '.join(platform_names)}\n\n")
                
            f.write("## Summary\n")
            f.write(f"{game_data.get('summary', 'No summary available.')}\n\n")
            
            story = game_data.get("storyline")
            if story:
                f.write("## Storyline\n")
                f.write(f"{story}\n\n")
                
            websites = game_data.get("websites", [])
            if websites:
                f.write("## Links\n")
                for site in websites:
                    f.write(f"- {site.get('url')}\n")
        
        update_progress("Generating metadata...") # Step 1

        # 2. Download Assets
        # Cover
        cover = game_data.get("cover")
        if cover:
            download_image(cover.get("url"), os.path.join(media_dir, "cover"))
        update_progress("Downloading cover...") # Step 2
            
        # Screenshots
        screenshots = game_data.get("screenshots", [])
        for i, shot in enumerate(screenshots):
            download_image(shot.get("url"), os.path.join(media_dir, f"screenshot_{i+1}"))
            update_progress(f"Downloading screenshot {i+1}/{len(screenshots)}...")
                
        # Artworks
        artworks = game_data.get("artworks", [])
        for i, art in enumerate(artworks):
            download_image(art.get("url"), os.path.join(media_dir, f"artwork_{i+1}"))
            update_progress(f"Downloading artwork {i+1}/{len(artworks)}...")

        # 3. Create Zip
        if progress_callback: progress_callback(0.99, "Compressing to zip...")
        
        zip_filename = f"{safe_name}.zip"
        # Output zip directly to the desired final location
        output_zip_path = os.path.join(output_dir_root, zip_filename)
        
        with zipfile.ZipFile(output_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(base_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Arcname should be relative to the temp base_dir so inside zip we see "GameName/..."
                    # We want the folder structure inside the zip.
                    arcname = os.path.relpath(file_path, temp_dir)
                    zipf.write(file_path, arcname)
                    
        update_progress("Finalizing...") # Final Step
                    
        return output_zip_path
