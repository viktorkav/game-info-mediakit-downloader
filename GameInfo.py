import customtkinter as ctk
import json
import threading
from tkinter import messagebox, filedialog
from PIL import Image
from io import BytesIO
import requests
import os

from config import MissingIGDBCredentialsError, load_igdb_credentials
from igdb_api import IGDBClient
from utils import create_mediakit, get_high_res_url, reveal_in_file_manager
from icon_manager import IconManager
import webbrowser
from datetime import datetime

# --- Theme Colors ---
COLOR_BG = "#131416"
COLOR_CARD = "#1c1d21"
COLOR_ACCENT = "#2563eb"
COLOR_ACCENT_HOVER = "#1d4ed8"
COLOR_TEXT = "#ffffff"
COLOR_TEXT_SEC = "#a1a1aa"
COLOR_INPUT_BG = "#0d1117"
COLOR_BORDER = "#2d3748"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class GameInfoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        try:
            client_id, client_secret = load_igdb_credentials()
        except MissingIGDBCredentialsError as exc:
            self.withdraw()
            messagebox.showerror("Missing IGDB credentials", str(exc))
            self.destroy()
            return

        self.title("Game Info - Mediakit Downloader")
        self.geometry("1000x800")
        self.configure(fg_color=COLOR_BG)

        self.client = IGDBClient(client_id, client_secret)
        self.icon_manager = IconManager() # Load icons
        self.selected_game = None # Details
        
        self.favorites_file = "favorites.json"
        self.favorites = self.load_favorites()
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -- Views Container --
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew")
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Initialize Views
        self.search_view = SearchView(self.container, self)
        self.details_view = DetailsView(self.container, self)
        
        self.show_search()

    def show_search(self):
        self.details_view.grid_remove()
        self.search_view.grid(row=0, column=0, sticky="nsew")

    def show_details(self, game_id):
        self.search_view.grid_remove()
        self.details_view.grid(row=0, column=0, sticky="nsew")
        self.details_view.load_game(game_id)

    def load_favorites(self):
        if os.path.exists(self.favorites_file):
            try:
                with open(self.favorites_file, 'r') as f:
                    return json.load(f)
            except: return []
        return []

    def save_favorites(self):
        with open(self.favorites_file, 'w') as f:
            json.dump(self.favorites, f)

    def toggle_favorite(self, game_id):
        if game_id in self.favorites:
            self.favorites.remove(game_id)
        else:
            self.favorites.append(game_id)
        self.save_favorites()
        if self.details_view.game_data and self.details_view.game_data['id'] == game_id:
             self.details_view.update_fav_btn()


class SearchView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        
        # Grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1) # WEIGHT ON RESULTS ROW
        
        # 1. Header & Search
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        self.header_frame.grid_columnconfigure(1, weight=1)
        
        self.logo = ctk.CTkLabel(self.header_frame, text="Game Info", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLOR_TEXT)
        self.logo.grid(row=0, column=0, padx=(0, 20))
        
        self.search_entry = ctk.CTkEntry(
            self.header_frame, 
            placeholder_text="Search games...",
            height=40,
            fg_color=COLOR_INPUT_BG,
            border_color=COLOR_BORDER,
            text_color=COLOR_TEXT
        )
        self.search_entry.grid(row=0, column=1, sticky="ew")
        self.search_entry.bind("<Return>", self.perform_search)
        
        self.search_btn = ctk.CTkButton(
            self.header_frame, text="Search", height=40, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER,
            command=self.perform_search
        )
        self.search_btn.grid(row=0, column=2, padx=(10, 0))

        # Favorites Filter
        self.fav_var = ctk.StringVar(value="off")
        self.fav_switch = ctk.CTkSwitch(self.header_frame, text="♥ Only", variable=self.fav_var, onvalue="on", offvalue="off", command=self.perform_search, width=80)
        self.fav_switch.grid(row=0, column=3, padx=10)

        # 2. Results Header
        self.cols_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD, height=30, corner_radius=5)
        self.cols_frame.grid(row=1, column=0, sticky="new", padx=20, pady=(0, 0)) # Fixed header
        self.cols_frame.grid_columnconfigure(0, weight=3) # Title
        self.cols_frame.grid_columnconfigure(1, weight=2) # Platforms
        
        ctk.CTkLabel(self.cols_frame, text="TITLE", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_SEC).grid(row=0, column=0, sticky="w", padx=10, pady=5)
        ctk.CTkLabel(self.cols_frame, text="PLATFORMS", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT_SEC).grid(row=0, column=1, sticky="w", padx=10, pady=5)

        # 3. Results List
        self.results_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.results_scroll.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5, 20))
        self.results_scroll.grid_columnconfigure(0, weight=1)
        
        self.status_label = ctk.CTkLabel(self, text="Ready", text_color=COLOR_TEXT_SEC)
        self.status_label.grid(row=3, column=0, pady=(0, 10))

    def perform_search(self, event=None):
        query = self.search_entry.get()
        is_fav = self.fav_var.get() == "on"
        
        if not query and not is_fav: return
        
        self.status_label.configure(text="Searching...", text_color=COLOR_ACCENT)
        self.search_btn.configure(state="disabled")
        
        # Clear
        for w in self.results_scroll.winfo_children(): w.destroy()
        
        if is_fav:
            ids = self.controller.favorites
            if not ids:
                self._populate_results([])
                self.search_btn.configure(state="normal")
                self.status_label.configure(text="No favorites yet.", text_color="orange")
                return
            threading.Thread(target=self._search_favs, args=(ids,), daemon=True).start()
        else:
            threading.Thread(target=self._search_thread, args=(query,), daemon=True).start()

    def _search_thread(self, query):
        try:
            results = self.controller.client.search_games(query)
            self.after(0, self._populate_results, results)
        except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {e}", text_color="red"))
        finally:
            self.after(0, lambda: self.search_btn.configure(state="normal"))

    def _populate_results(self, results):
        try:
            if not results:
                self.status_label.configure(text="No results found.", text_color="orange")
                return
                
            for i, game in enumerate(results):
                # Row Frame
                row = ctk.CTkFrame(self.results_scroll, fg_color=COLOR_CARD if i%2==0 else COLOR_BG, corner_radius=5, height=40)
                row.pack(fill="x", pady=2)
                row.grid_propagate(False) # Fixed height
                
                row.grid_columnconfigure(0, weight=1) # Title takes space
                row.grid_columnconfigure(1, weight=0) # Platform fits content
                
                # Content
                title = game.get('name', 'Unknown')
                platforms = game.get('platforms', [])
                plat_names = [p.get('name', 'Unknown') for p in platforms]
                plat_text = ", ".join(plat_names) if plat_names else "N/A"
                
                # Title (Left)
                lbl_title = ctk.CTkLabel(row, text=title, text_color=COLOR_TEXT, anchor="w")
                lbl_title.grid(row=0, column=0, padx=10, pady=5, sticky="ew")
                
                # Platform Text (Right)
                # Truncate if too long? Let's just anchor right.
                lbl_plat = ctk.CTkLabel(row, text=plat_text, text_color=COLOR_TEXT_SEC, anchor="e")
                lbl_plat.grid(row=0, column=1, padx=10, pady=5, sticky="e")
                
                # Binding
                for w in [row, lbl_title, lbl_plat]:
                    w.bind("<Double-Button-1>", lambda e, gid=game['id']: self.controller.show_details(gid))
                    w.bind("<Enter>", lambda e, f=row: f.configure(border_width=1, border_color=COLOR_ACCENT))
                    w.bind("<Leave>", lambda e, f=row: f.configure(border_width=0))
            
            self.status_label.configure(text=f"Found {len(results)} games.", text_color="green")
        except Exception as e:
            self.status_label.configure(text=f"UI Error: {e}", text_color="red")
            print(f"UI Error: {e}")

    def _search_favs(self, ids):
         try:
            id_str = ",".join(map(str, ids))
            # Fetch minimal info required for list
            body = f'fields name, platforms.name, cover.url; where id = ({id_str}); limit 50;'
            url = f"{self.controller.client.BASE_URL}/games"
            resp = requests.post(url, headers=self.controller.client._get_headers(), data=body)
            resp.raise_for_status()
            results = resp.json()
            self.after(0, self._populate_results, results)
         except Exception as e:
            self.after(0, lambda: self.status_label.configure(text=f"Error: {e}", text_color="red"))
         finally:
            self.after(0, lambda: self.search_btn.configure(state="normal"))


class DetailsView(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent, fg_color="transparent")
        self.controller = controller
        self.game_data = None
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Content grows
        
        # 1. Top Bar
        self.top_bar = ctk.CTkFrame(self, fg_color="transparent", height=50)
        self.top_bar.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        self.back_btn = ctk.CTkButton(
            self.top_bar, text="← Back to Search", fg_color=COLOR_CARD, hover_color=COLOR_BORDER, width=100,
            command=controller.show_search
        )
        self.back_btn.pack(side="left")

        self.fav_btn = ctk.CTkButton(self.top_bar, text="♥", width=40, font=ctk.CTkFont(size=20), fg_color="transparent", border_width=1, border_color=COLOR_BORDER, command=self.toggle_fav)
        self.fav_btn.pack(side="right")

        # 2. Main Content (Scrollable)
        # Use ScrollableFrame to ensure Download button is always reachable
        self.content = ctk.CTkScrollableFrame(self, fg_color=COLOR_CARD, corner_radius=10)
        self.content.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.content.grid_columnconfigure(1, weight=1) # Info col
        self.content.grid_rowconfigure(0, weight=1)
        
        # Left: Cover Image
        self.cover_frame = ctk.CTkFrame(self.content, fg_color="transparent", width=300)
        self.cover_frame.grid(row=0, column=0, sticky="n", padx=20, pady=20)
        self.cover_label = ctk.CTkLabel(self.cover_frame, text="Loading Cover...")
        self.cover_label.pack()

        # Right: Metadata
        self.info_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        self.info_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.info_frame.grid_columnconfigure(0, weight=1)
        
        self.title_lbl = ctk.CTkLabel(self.info_frame, text="", font=ctk.CTkFont(size=32, weight="bold"), anchor="w", wraplength=500, justify="left")
        self.title_lbl.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        
        self.meta_lbl = ctk.CTkLabel(self.info_frame, text="", text_color=COLOR_TEXT_SEC, anchor="w", justify="left")
        # Hidden/Unused now, but kept for object ref safety if needed or we can clean up. 
        # Actually proper to just ignore it.
        
        # Metadata Container
        self.tags_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.tags_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.tags_frame.grid_columnconfigure(1, weight=1) # Allow values to expand
        
        self.links_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent") 
        # Kept declaration to avoid errors if referenced, but logic removed.
        
        # 3. Bottom Action Bar (Integrated in flow)
        self.action_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(20, 0))
        self.action_frame.grid_columnconfigure(0, weight=1)
        
        # Save Path
        self.path_entry = ctk.CTkEntry(self.action_frame, placeholder_text="Save Path", fg_color=COLOR_INPUT_BG)
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.path_entry.insert(0, path)
        
        self.browse_btn = ctk.CTkButton(self.action_frame, text="📂", width=40, fg_color=COLOR_INPUT_BG, command=self.browse)
        self.browse_btn.grid(row=0, column=1)
        
        # Download
        self.btn_container = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.btn_container.grid(row=3, column=0, sticky="ew", pady=(20, 0))
        self.btn_container.grid_columnconfigure(0, weight=1)

        self.dl_btn = ctk.CTkButton(self.btn_container, text="DOWNLOAD MEDIAKIT", height=50, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=ctk.CTkFont(size=16, weight="bold"), command=self.download)
        self.dl_btn.grid(row=0, column=0, sticky="ew")
        
        self.progress = ctk.CTkProgressBar(self.btn_container, height=20, progress_color=COLOR_ACCENT)
        # Hidden initially
        
        self.status_lbl = ctk.CTkLabel(self.info_frame, text="")
        self.status_lbl.grid(row=4, column=0, sticky="w", pady=(5,0))

    def browse(self):
        d = filedialog.askdirectory()
        if d:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, d)

    def load_game(self, game_id):
        # Reset UI
        self.title_lbl.configure(text="Loading...")
        self.meta_lbl.configure(text="")
        for widget in self.tags_frame.winfo_children(): widget.destroy() # Clear meta
        
        # Hard Reset Cover Label to fix TclError zombie image
        if hasattr(self, 'cover_label') and self.cover_label:
            self.cover_label.destroy()
            
        self.current_cover = None # Clear ref
        
        self.cover_label = ctk.CTkLabel(self.cover_frame, text="Loading Cover...")
        self.cover_label.pack()
        
        # Reset Download UI
        self.dl_btn.configure(state="disabled")
        self.dl_btn.grid(row=0, column=0, sticky="ew") # Ensure visible
        self.progress.grid_remove()
        self.progress.set(0)
        self.status_lbl.configure(text="")
        
        threading.Thread(target=self._fetch, args=(game_id,), daemon=True).start()
        
    def _fetch(self, game_id):
        try:
            data = self.controller.client.get_game_details(game_id)
            if not data:
                raise Exception("No data found")
            self.after(0, self._display, data)
        except Exception as e:
            print(f"Fetch Error: {e}")
            def show_error():
                self.title_lbl.configure(text=f"Error: {e}")
                self.status_lbl.configure(text="Failed to load game details.", text_color="red")
            self.after(0, show_error)
            
    def _display(self, data):
        self.game_data = data
        self.update_fav_btn()
        self.title_lbl.configure(text=data['name'])
        
        # Clear previous metadata
        for widget in self.tags_frame.winfo_children(): widget.destroy()
        
        # Helper for Grid Rows
        def add_row(parent, row_idx, label_text, value_text):
            if not value_text: return row_idx
            
            # Label (Bold)
            k = ctk.CTkLabel(parent, text=f"{label_text}:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_SEC, anchor="nw")
            k.grid(row=row_idx, column=0, sticky="nw", padx=(0, 10), pady=2)
            
            # Value (Normal)
            v = ctk.CTkLabel(parent, text=value_text, text_color=COLOR_TEXT, anchor="nw", justify="left", wraplength=400)
            v.grid(row=row_idx, column=1, sticky="w", pady=2)
            
            return row_idx + 1

        # Build Metadata
        r = 0
        
        # Released
        rel_date = data.get('first_release_date')
        if rel_date:
            date_str = datetime.fromtimestamp(rel_date).strftime('%B %d, %Y')
            r = add_row(self.tags_frame, r, "Released", date_str)

        # Rating
        if 'rating' in data:
            score = round(data['rating'], 1)
            r = add_row(self.tags_frame, r, "Rating", f"{score}/100")

        # Developer
        devs = [c['company']['name'] for c in data.get('involved_companies', []) if c.get('developer')]
        r = add_row(self.tags_frame, r, "Developer", ", ".join(devs))

        # Publisher
        pubs = [c['company']['name'] for c in data.get('involved_companies', []) if c.get('publisher')]
        r = add_row(self.tags_frame, r, "Publisher", ", ".join(pubs))
        
        # Genres
        genres = [g['name'] for g in data.get('genres', [])]
        r = add_row(self.tags_frame, r, "Genres", ", ".join(genres))
        
        # Platforms
        plats = [p['name'] for p in data.get('platforms', [])]
        r = add_row(self.tags_frame, r, "Platforms", ", ".join(plats))
        
        # About / Summary (Integrated)
        summary_text = data.get('summary', 'No summary.')
        r = add_row(self.tags_frame, r, "About", summary_text)
        
        # Trailer Button
        if 'videos' in data and data['videos']:
            vid_id = data['videos'][0].get('video_id')
            if vid_id:
                btn = ctk.CTkButton(self.tags_frame, text="▶ Watch Trailer", height=30, fg_color=COLOR_CARD, border_color=COLOR_ACCENT, border_width=1, command=lambda: webbrowser.open(f"https://www.youtube.com/watch?v={vid_id}"))
                btn.grid(row=r, column=0, columnspan=2, sticky="w", pady=(10, 0))
                r += 1

        # Screenshot Gallery
        if 'screenshots' in data and data['screenshots']:
            gal_lbl = ctk.CTkLabel(self.tags_frame, text="Gallery:", font=ctk.CTkFont(weight="bold"), text_color=COLOR_TEXT_SEC)
            gal_lbl.grid(row=r, column=0, sticky="nw", pady=(20, 5))
            r += 1
            
            self.gal_frame = ctk.CTkFrame(self.tags_frame, fg_color="transparent")
            self.gal_frame.grid(row=r, column=0, columnspan=2, sticky="ew")
            self.gal_frame.grid_columnconfigure((0,1,2), weight=1) # 3 Cols
            r += 1
            
            for i, s in enumerate(data['screenshots']):
                url = get_high_res_url(s['url'])
                if url:
                    # Grid Logic (3 columns)
                    row_g = i // 3
                    col_g = i % 3
                    
                    # Async load thumb
                    f = ctk.CTkFrame(self.gal_frame, width=200, height=120)
                    f.grid(row=row_g, column=col_g, padx=5, pady=5)
                    l = ctk.CTkLabel(f, text="Loading...", width=200, height=120)
                    l.pack()
                    threading.Thread(target=self._load_screenshot, args=(url, l), daemon=True).start()

        # Cover Image
        if 'cover' in data and 'url' in data['cover']:
            url = get_high_res_url(data['cover']['url'])
            if url:
                threading.Thread(target=self._load_cover, args=(url,), daemon=True).start()
        else:
            self.cover_label.configure(text="No Cover", image=None)
            
        self.dl_btn.configure(state="normal")

    def _load_cover(self, url):
        try:
            print(f"Downloading cover from: {url}")
            resp = requests.get(url, stream=True)
            resp.raise_for_status()
            data = resp.content # Raw bytes
            
            # Pass bytes to main thread
            self.after(0, lambda: self._update_cover_ui(data))
            
        except Exception as e:
            print(f"Cover Download Error: {e}")
            self.after(0, lambda: self.cover_label.configure(text=f"Cover Error", image=None))

    def _update_cover_ui(self, data):
        if not self.winfo_exists(): return
        
        try:
            # All image processing on main thread
            pil_img = Image.open(BytesIO(data))
            
            ratio = pil_img.height / pil_img.width
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(300, int(300*ratio)))
            
            self.current_cover = ctk_img # Keep reference
            self.cover_label.configure(image=ctk_img, text="")
            print("Cover updated successfully.")
            
        except Exception as e:
            print(f"Cover Process Error: {e}")
            self.cover_label.configure(text="by Image Error", image=None)

    def _load_screenshot(self, url, label):
        try:
            resp = requests.get(url, stream=True)
            data = resp.content
            self.after(0, lambda: self._update_screenshot_ui(data, label))
        except:
            pass

    def _update_screenshot_ui(self, data, label):
        if not label.winfo_exists(): return
        try:
            pil = Image.open(BytesIO(data))
            # Fixed height 120
            ratio = pil.width / pil.height
            ctk_img = ctk.CTkImage(pil, size=(int(120*ratio), 120))
            label.configure(image=ctk_img, text="")
            label.image = ctk_img # Keep ref
        except:
            label.configure(text="Error")

    def download(self):
        target = self.path_entry.get()
        if not os.path.exists(target): return
        
        self.dl_btn.grid_remove()
        self.progress.grid(row=0, column=0, sticky="ew")
        self.progress.set(0)
        
        threading.Thread(target=self._dl_thread, args=(target,), daemon=True).start()

    def toggle_fav(self):
        if self.game_data:
            self.controller.toggle_favorite(self.game_data['id'])

    def update_fav_btn(self):
        if not self.game_data: return
        is_fav = self.game_data['id'] in self.controller.favorites
        color = COLOR_ACCENT if is_fav else "transparent"
        self.fav_btn.configure(fg_color=color)
        
    def _dl_thread(self, target):
        try:
            def cb(val, msg):
                self.after(0, lambda: self.progress.set(val))
                self.after(0, lambda: self.status_lbl.configure(text=msg))
            
            p = create_mediakit(self.game_data, target, cb)
            self.after(0, lambda: self.status_lbl.configure(text="Complete!", text_color="green"))
            reveal_in_file_manager(p)
        except Exception as e:
            self.after(0, lambda: self.status_lbl.configure(text=str(e), text_color="red"))
        finally:
             self.after(0, self._reset_dl)
             
    def _reset_dl(self):
        self.progress.grid_remove()
        self.dl_btn.grid(row=0, column=0, sticky="ew")

if __name__ == "__main__":
    app = GameInfoApp()
    if app.winfo_exists():
        app.mainloop()
