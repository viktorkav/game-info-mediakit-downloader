import os
import sqlite3
from PIL import Image
import customtkinter as ctk

class IconManager:
    def __init__(self, db_path="assets/icons.db"):
        self.db_path = db_path
        self.cache = {}

    def get_icon_by_platform_id(self, platform_id, size=(30, 20)):
        """Fetches icon from local DB by distinct platform ID."""
        if platform_id in self.cache:
            return self.cache[platform_id]
            
        if not os.path.exists(self.db_path):
            return None

        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute("SELECT icon_path FROM platforms WHERE id=?", (platform_id,))
            row = c.fetchone()
            conn.close()
            
            if row and row[0] and os.path.exists(row[0]):
                path = row[0]
                img = Image.open(path)
                # Ensure it fits
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
                self.cache[platform_id] = ctk_img
                return ctk_img
        except Exception as e:
            print(f"DB Icon Error {platform_id}: {e}")
            
        self.cache[platform_id] = None
        return None

    def get_platform_icons(self, platforms):
        """Returns specific icons for the platform list using local DB."""
        if not platforms: return []
        
        icons = []
        # Limit to avoid clutter? Or show all? Let's show up to 6.
        for p in platforms[:6]:
            pid = p.get('id')
            if pid:
                icon = self.get_icon_by_platform_id(pid)
                if icon:
                    icons.append(icon)
        return icons
