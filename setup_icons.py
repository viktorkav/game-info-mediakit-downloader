import os
import requests
import sqlite3
import time
from config import MissingIGDBCredentialsError, load_igdb_credentials
from igdb_api import IGDBClient

DB_PATH = "assets/icons.db"
LOGOS_DIR = "assets/logos"

def main():
    try:
        client_id, client_secret = load_igdb_credentials()
    except MissingIGDBCredentialsError as exc:
        print(f"Configuration error: {exc}")
        return

    if not os.path.exists(LOGOS_DIR):
        os.makedirs(LOGOS_DIR)

    # 1. Setup DB
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS platforms
                 (id INTEGER PRIMARY KEY, name TEXT, slug TEXT, icon_path TEXT)''')
    conn.commit()

    # 2. Authenticate
    print("Authenticating with IGDB...")
    client = IGDBClient(client_id, client_secret)
    headers = client._get_headers()

    # 3. Fetch Platforms (Paginated)
    print("Fetching platforms...")
    url = "https://api.igdb.com/v4/platforms"
    offset = 0
    limit = 500
    
    while True:
        body = f"fields id, name, slug, platform_logo.url; limit {limit}; offset {offset}; sort id asc;"
        resp = requests.post(url, headers=headers, data=body)
        
        if resp.status_code != 200:
            print(f"Error: {resp.status_code} - {resp.text}")
            break
            
        data = resp.json()
        if not data:
            break
            
        print(f"Processing {len(data)} platforms (Offset: {offset})...")
        
        for p in data:
            pid = p['id']
            name = p['name']
            slug = p.get('slug', '')
            logo_data = p.get('platform_logo')
            
            icon_path = None
            if logo_data and 'url' in logo_data:
                img_url = logo_data['url']
                if img_url.startswith("//"): img_url = "https:" + img_url
                
                # Download
                ext = img_url.split('.')[-1]
                save_name = f"{slug}_{pid}.{ext}" if slug else f"plat_{pid}.{ext}"
                save_path = os.path.join(LOGOS_DIR, save_name)
                
                if not os.path.exists(save_path):
                    try:
                        r = requests.get(img_url, timeout=5)
                        if r.status_code == 200:
                            with open(save_path, "wb") as f:
                                f.write(r.content)
                            icon_path = save_path
                    except Exception as e:
                        print(f"Failed to dl {name}: {e}")
                else:
                    icon_path = save_path

            # Upsert into DB
            c.execute("INSERT OR REPLACE INTO platforms (id, name, slug, icon_path) VALUES (?, ?, ?, ?)",
                      (pid, name, slug, icon_path))
        
        conn.commit()
        offset += limit
        time.sleep(0.25) # Rate limit courtesy

    print("Done! Database populated.")
    conn.close()

if __name__ == "__main__":
    main()
