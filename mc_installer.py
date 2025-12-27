import os, json, uuid, zipfile, requests, subprocess, shutil, time, sys, platform, socket, ctypes
from pathlib import Path
from datetime import datetime
import threading
import customtkinter as ctk
import tkinter as tk

# --- CONFIGURATION ---
MODPACK_NAME = "Cranix Modpack"
GITHUB_ZIP_URL = "https://github.com/crancorn-git/modpack/releases/download/1.0.0/modpack.zip"
VERSION_URL = "https://raw.githubusercontent.com/crancorn-git/modpack/main/version.txt"
SERVER_IP = "play.nickyboi.com"
WEBHOOK_URL = "https://discord.com/api/webhooks/1454533943154966775/YuQyod9nPn0TIsJ6NcnQo_0Tl6CGfUwYy7240SrDS5qdGEcHuni0kLZf25LS8sEFln-i"
DISCORD_CLIENT_ID = "1454529897363017839"

MC_VERSION = "1.21.11"
FABRIC_LOADER = "0.18.2"
MINECRAFT_VERSION = f"fabric-loader-{FABRIC_LOADER}-{MC_VERSION}"
FABRIC_META_URL = f"https://meta.fabricmc.net/v2/versions/loader/{MC_VERSION}/{FABRIC_LOADER}/profile/json"

# --- PALETTE ---
VIOLENT_GREEN = "#1DFF00"
XP_FILL_BRIGHT = "#C7FF1A"
XP_FILL_DARK = "#459400"
PITCH_BLACK = "#00120F" # Deep green-black for that diamond feel
TRACK_BG = "#00211C"

# --- FONT HANDLER ---
def load_font():
    """Bridges the custom font from the EXE bundle to the Windows system."""
    if platform.system() == "Windows":
        # Check if running as EXE or raw Python
        if hasattr(sys, '_MEIPASS'):
            font_path = os.path.join(sys._MEIPASS, "Minecraft.ttf")
        else:
            font_path = os.path.join(os.path.dirname(__file__), "Minecraft.ttf")

        if os.path.exists(font_path):
            # Load font for this process only (0x10 = FR_PRIVATE)
            ctypes.windll.gdi32.AddFontResourceExW(font_path, 0x10, 0)
            return "Minecraft"
    return "Consolas"

CUSTOM_FONT = load_font()

# --- CUSTOM WIDGETS ---

class MinecraftXPBar(tk.Canvas):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg=PITCH_BLACK, highlightthickness=0, **kwargs)
        self.progress = 0

    def set_progress(self, val):
        self.progress = val
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = 480, 16
        segments = 15
        seg_w = w / segments
        for i in range(segments):
            x1, x2 = i * seg_w, (i + 1) * seg_w
            fill_col = TRACK_BG
            if self.progress > (i / segments):
                fill_col = VIOLENT_GREEN
            
            self.create_rectangle(x1, 0, x2, h, fill="black", outline="")
            self.create_rectangle(x1+1, 1, x2-1, h-1, fill=fill_col, outline="")
            if fill_col == VIOLENT_GREEN:
                self.create_line(x1+1, 2, x2-1, 2, fill="#B2FFC8")

class CranixInstaller(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(fg_color=PITCH_BLACK)
        
        self.width, self.height = 600, 320
        x = (self.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.winfo_screenheight() // 2) - (self.height // 2)
        self.geometry(f"{self.width}x{self.height}+{x}+{y}")
        
        if os.path.exists("logo.ico"): self.iconbitmap("logo.ico")
        self.bind("<ButtonPress-1>", self.start_move)
        self.bind("<B1-Motion>", self.do_move)

        # Title Section
        self.title_label = ctk.CTkLabel(self, text="CRANIX NETWORK", 
                                        font=(CUSTOM_FONT, 42), text_color="#B2FFC8")
        self.title_label.pack(pady=(60, 0))

        self.sub_label = ctk.CTkLabel(self, text="MODPACK INSTALLER", 
                                      font=(CUSTOM_FONT, 14), text_color="#B2FFC8")
        self.sub_label.pack(pady=(5, 30))

        self.status_label = ctk.CTkLabel(self, text="PREPARING...", 
                                         font=(CUSTOM_FONT, 11), text_color="#5a827a")
        self.status_label.pack()

        self.xp_bar = MinecraftXPBar(self, width=480, height=16)
        self.xp_bar.pack(pady=15)

        self.footer = ctk.CTkLabel(self, text="CRANIX LTD © 2025 | AUTHORIZED DEPLOYMENT", 
                                   font=("Consolas", 8), text_color="#10302a")
        self.footer.pack(side="bottom", pady=25)

        threading.Thread(target=self.run_install_logic, daemon=True).start()

    def start_move(self, event): self.x = event.x; self.y = event.y
    def do_move(self, event):
        self.geometry(f"+{self.winfo_x() + (event.x - self.x)}+{self.winfo_y() + (event.y - self.y)}")

    def update_status(self, text, progress):
        self.status_label.configure(text=text.upper())
        self.xp_bar.set_progress(progress)
        self.update_idletasks()

    def launch_game(self):
        if platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", "Minecraft"])
        else:
            ps_cmd = "$app = Get-StartApps | Where-Object {$_.Name -like '*Minecraft Launcher*'}; Start-Process ('shell:AppsFolder\\' + $app[0].AppID)"
            subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd], capture_output=True)

    def run_install_logic(self):
        try:
            mc_path = Path.home() / "Library/Application Support/minecraft" if platform.system() == "Darwin" else Path(os.getenv('APPDATA')) / '.minecraft'
            modpack_dir = mc_path / "profiles" / MODPACK_NAME

            self.update_status("Pinging Archive", 0.1)
            version_file = modpack_dir / ".cranix_v"
            skip_download = False
            try:
                r = requests.get(VERSION_URL, timeout=5)
                remote_v = r.text.strip() if r.status_code == 200 else "1.0.0"
                if version_file.exists() and version_file.read_text().strip() == remote_v: skip_download = True
            except: remote_v = "1.0.0"

            self.update_status("Injecting Fabric", 0.3)
            v_dir = mc_path / "versions" / MINECRAFT_VERSION
            v_dir.mkdir(parents=True, exist_ok=True)
            data = requests.get(FABRIC_META_URL, timeout=10).json()
            if "arguments" in data and "game" in data["arguments"]:
                if "--server" not in data["arguments"]["game"]:
                    data["arguments"]["game"].extend(["--server", SERVER_IP])
            with open(v_dir / f"{MINECRAFT_VERSION}.json", 'w') as f: json.dump(data, f, indent=2)

            if not skip_download:
                self.update_status("Downloading Assets", 0.5)
                if modpack_dir.exists(): shutil.rmtree(modpack_dir)
                modpack_dir.mkdir(parents=True, exist_ok=True)
                r = requests.get(GITHUB_ZIP_URL, allow_redirects=True)
                with open(modpack_dir / "temp.zip", 'wb') as f: f.write(r.content)
                self.update_status("Extracting Assets", 0.7)
                with zipfile.ZipFile(modpack_dir / "temp.zip", 'r') as z: z.extractall(modpack_dir)
                os.remove(modpack_dir / "temp.zip")

                ov_dir = None
                for root, dirs, _ in os.walk(modpack_dir):
                    if "overrides" in dirs: ov_dir = Path(root) / "overrides"; break
                if ov_dir:
                    for item in ov_dir.iterdir():
                        target = modpack_dir / item.name
                        if target.exists():
                            if target.is_dir(): shutil.rmtree(target)
                            else: os.remove(target)
                        shutil.move(str(item), str(modpack_dir))
                with open(modpack_dir / ".cranix_v", 'w') as f: f.write(remote_v)

            self.update_status("Syncing Profile", 0.95)
            prof_json = mc_path / "launcher_profiles.json"
            with open(prof_json, 'r') as f: config = json.load(f)
            config['profiles'] = {k: v for k, v in config.get('profiles', {}).items() if v.get('name') != MODPACK_NAME}
            config['profiles'][uuid.uuid4().hex] = {
                "name": MODPACK_NAME, "type": "custom", "gameDir": str(modpack_dir),
                "lastVersionId": MINECRAFT_VERSION, "icon": "Grass"
            }
            with open(prof_json, 'w') as f: json.dump(config, f, indent=2)

            try:
                user = os.environ.get('USERNAME') or "User"
                payload = {"embeds": [{"title": "CRANIX LOG", "description": "✅ **Installation Success**", "color": 11730888, "fields": [{"name": "User", "value": f"`{user}`", "inline": True}]}]}
                requests.post(WEBHOOK_URL, json=payload, timeout=5)
            except: pass

            self.update_status("Ready. Launching...", 1.0)
            time.sleep(1.5)
            self.launch_game()
            self.destroy()

        except Exception as e:
            self.update_status("Sync Failed", 0)
            time.sleep(5); self.destroy()

if __name__ == "__main__":
    app = CranixInstaller()
    app.mainloop()