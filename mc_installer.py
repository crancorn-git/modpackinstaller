import os, json, uuid, zipfile, requests, subprocess, shutil, time, sys, platform
from pathlib import Path
from datetime import datetime

# --- CONFIGURATION ---
MODPACK_NAME = "Cranix Modpack"
GITHUB_ZIP_URL = "https://github.com/crancorn-git/modpack/releases/download/1.0.0/modpack.zip"
MC_VERSION = "1.21.11"
FABRIC_LOADER = "0.18.2"
MINECRAFT_VERSION = f"fabric-loader-{FABRIC_LOADER}-{MC_VERSION}"
# Direct API for version metadata
FABRIC_META_URL = f"https://meta.fabricmc.net/v2/versions/loader/{MC_VERSION}/{FABRIC_LOADER}/profile/json"

# --- TERMINAL COLORS ---
GREEN = "\033[38;5;46m"
BRIGHT_GREEN = "\033[1;38;5;82m"
RESET = "\033[0m"

if platform.system() == "Windows":
    os.system("") # Init Windows ANSI

ASCII_ART = fr"""{BRIGHT_GREEN}
  ______ .______          ___      .__   __.  __  ___  ___ 
 /      ||   _  \        /   \     |  \ |  | |  | \  \  /  / 
|  ,----'|  |_)  |      /  ^  \    |   \|  | |  |  \  \/  /  
|  |     |      /      /  /_\  \   |  . `  | |  |   >    <   
|  `----.|  |\  \----./  _____  \  |  |\   | |  |  /  /\  \  
 \______|| _| `._____/__/     \__\ |__| \__| |__| /__/  \__\ 

                PROPRIETARY INSTALLATION TOOL | v14.0
                OFFICIAL RELEASE BY CRANIX LTD
======================================================================================{RESET}"""

def print_prof(text, delay=0.01, color=GREEN):
    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET + "\n")

def get_mc_path():
    if platform.system() == "Darwin":
        return Path.home() / "Library/Application Support/minecraft"
    return Path(os.getenv('APPDATA')) / '.minecraft'

def get_optimal_ram():
    """Calculates best RAM allocation based on physical hardware."""
    try:
        if platform.system() == "Darwin":
            out = subprocess.check_output(['sysctl', '-n', 'hw.memsize']).decode().strip()
            total_gb = int(out) / (1024**3)
        else:
            import ctypes
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong), 
                            ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                            ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                            ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                            ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024**3)
        
        if total_gb < 7: return "-Xmx2G", "2GB (Safety)"
        if total_gb < 15: return "-Xmx4G", "4GB (Optimized)"
        return "-Xmx6G", "6GB (Performance)"
    except: return "-Xmx4G", "4GB (Default)"

def force_install_fabric(mc_path):
    version_dir = mc_path / "versions" / MINECRAFT_VERSION
    version_json = version_dir / f"{MINECRAFT_VERSION}.json"
    print_prof(f"[*] INJECTING FABRIC KERNEL: {MINECRAFT_VERSION}...")
    try:
        version_dir.mkdir(parents=True, exist_ok=True)
        r = requests.get(FABRIC_META_URL, timeout=10)
        with open(version_json, 'w') as f: f.write(r.text)
        return True
    except Exception as e:
        print_prof(f"[!] INJECTION FAILED: {e}")
        return False

def launch_launcher():
    print_prof("[>] HANDSHAKE SUCCESSFUL. BOOTSTRAPPING LAUNCHER...", 0.03, BRIGHT_GREEN)
    if platform.system() == "Darwin":
        subprocess.run(["open", "-a", "Minecraft"])
    else:
        ps_cmd = "$app = Get-StartApps | Where-Object {$_.Name -like '*Minecraft Launcher*'}; Start-Process ('shell:AppsFolder\\' + $app[0].AppID)"
        subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd], capture_output=True)

def run_installer():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(ASCII_ART)
    
    # Check Java
    try:
        subprocess.run(["java", "-version"], capture_output=True)
    except:
        print_prof("[!] JAVA NOT DETECTED. PLEASE INSTALL JAVA 21.", 0.01, BRIGHT_GREEN)
        input("Press Enter to exit...")
        return

    mc_path = get_mc_path()
    modpack_dir = mc_path / "profiles" / MODPACK_NAME
    
    # 1. Fabric
    if not force_install_fabric(mc_path):
        input("Injection error. Press Enter...")
        return

    # 2. Download & Extract
    print_prof(f"[+] FETCHING {MODPACK_NAME} ASSETS FROM CRANIX CLOUD...")
    if modpack_dir.exists(): shutil.rmtree(modpack_dir)
    modpack_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        r = requests.get(GITHUB_ZIP_URL, allow_redirects=True, timeout=20)
        zip_path = modpack_dir / "temp.zip"
        with open(zip_path, 'wb') as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(modpack_dir)
        os.remove(zip_path)

        # Deep Search for Overrides
        over_found = None
        for root, dirs, files in os.walk(modpack_dir):
            if "overrides" in dirs:
                over_found = Path(root) / "overrides"
                break
        if over_found:
            print_prof("[+] APPLYING OVERRIDES LAYER...")
            for item in over_found.iterdir():
                target = modpack_dir / item.name
                if target.exists():
                    if target.is_dir(): shutil.rmtree(target)
                    else: os.remove(target)
                shutil.move(str(item), str(modpack_dir))
        
        # Cleanup extra folders
        for item in modpack_dir.iterdir():
            if item.is_dir() and item.name in ["modpack", "overrides"]: shutil.rmtree(item)
            elif item.name in ["manifest.json", "modlist.html"]: os.remove(item)

        # 3. Profile Setup
        ram_arg, ram_label = get_optimal_ram()
        print_prof(f"[#] MEMORY OPTIMIZED: {ram_label}")
        
        prof_json = mc_path / "launcher_profiles.json"
        with open(prof_json, 'r') as f: data = json.load(f)
        
        # Deduplicate
        data['profiles'] = {k: v for k, v in data.get('profiles', {}).items() if v.get('name') != MODPACK_NAME}
        
        p_id = uuid.uuid4().hex
        data['profiles'][p_id] = {
            "name": MODPACK_NAME,
            "type": "custom",
            "gameDir": str(modpack_dir),
            "lastVersionId": MINECRAFT_VERSION,
            "javaArgs": ram_arg,
            "icon": "Grass"
        }
        with open(prof_json, 'w') as f: json.dump(data, f, indent=2)

        print(BRIGHT_GREEN + "\n" + "="*86)
        print_prof("INSTALLATION SUCCESSFUL. WELCOME TO CRANIX SERVER.", 0.02, BRIGHT_GREEN)
        print("="*86 + RESET + "\n")
        
        launch_launcher()
        time.sleep(3)
    except Exception as e:
        print_prof(f"[!] CRITICAL ERROR: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    run_installer()