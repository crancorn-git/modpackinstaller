import os, json, uuid, zipfile, requests, subprocess, shutil, time, sys, ctypes
from pathlib import Path

# --- CONFIGURATION ---
MODPACK_NAME = "Cranix Modpack"
GITHUB_ZIP_URL = "https://github.com/crancorn-git/modpack/releases/download/1.0.0/modpack.zip"
MC_VERSION = "1.21.11"
FABRIC_LOADER = "0.18.2"
MINECRAFT_VERSION = f"fabric-loader-{FABRIC_LOADER}-{MC_VERSION}"

# Official Fabric API to get the version JSON directly
FABRIC_META_URL = f"https://meta.fabricmc.net/v2/versions/loader/{MC_VERSION}/{FABRIC_LOADER}/profile/json"

# --- TERMINAL COLORS ---
GREEN = "\033[38;5;46m"
BRIGHT_GREEN = "\033[1;38;5;82m"
RESET = "\033[0m"

os.system("") # Init ANSI

ASCII_ART = fr"""{BRIGHT_GREEN}
  ______ .______          ___      .__   __.  __  ___  ___ 
 /      ||   _  \        /   \     |  \ |  | |  | \  \  /  / 
|  ,----'|  |_)  |      /  ^  \    |   \|  | |  |  \  \/  /  
|  |     |      /      /  /_\  \   |  . `  | |  |   >    <   
|  `----.|  |\  \----./  _____  \  |  |\   | |  |  /  /\  \  
 \______|| _| `._____/__/     \__\ |__| \__| |__| /__/  \__\ 

                PROPRIETARY INSTALLATION TOOL | v13.0
                OFFICIAL RELEASE BY CRANIX LTD
======================================================================================{RESET}"""

def print_prof(text, delay=0.01, color=GREEN):
    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET + "\n")

def force_install_fabric(mc_path):
    """Bypasses the JAR installer and manually creates the Fabric version files."""
    version_dir = mc_path / "versions" / MINECRAFT_VERSION
    version_json = version_dir / f"{MINECRAFT_VERSION}.json"

    print_prof(f"[*] FORCING FABRIC INJECTION: {MINECRAFT_VERSION}...")
    
    try:
        # 1. Create the directory
        version_dir.mkdir(parents=True, exist_ok=True)

        # 2. Fetch the Version JSON from Fabric Meta API
        r = requests.get(FABRIC_META_URL, timeout=10)
        if r.status_code != 200:
            print_prof("[!] CRITICAL ERROR: COULD NOT FETCH FABRIC DATA.")
            return False
        
        # 3. Save the JSON file
        with open(version_json, 'w') as f:
            f.write(r.text)

        print_prof("[#] FABRIC KERNEL INJECTED SUCCESSFULLY.")
        return True
    except Exception as e:
        print_prof(f"[!] INJECTION ERROR: {e}")
        return False

def launch_minecraft_java():
    print_prof("[>] INITIALIZING SECURE BOOTSTRAP...", 0.03, BRIGHT_GREEN)
    ps_command = (
        "$app = Get-StartApps | Where-Object {$_.Name -like '*Minecraft Launcher*'}; "
        "if($app) { Start-Process -FilePath ('shell:AppsFolder\\' + $app[0].AppID) } "
        "else { Start-Process 'minecraft-java:' }"
    )
    subprocess.run(["powershell", "-WindowStyle", "Hidden", "-Command", ps_command], capture_output=True)

def run_installer():
    os.system('cls' if os.name == 'nt' else 'clear')
    print(ASCII_ART)
    
    mc_path = Path(os.getenv('APPDATA')) / '.minecraft'
    modpack_dir = mc_path / "profiles" / MODPACK_NAME

    # 1. Force Fabric Installation
    if not force_install_fabric(mc_path):
        input("\nPRESS ENTER TO EXIT...")
        return

    # 2. Modpack Sync
    print_prof(f"[+] SYNCHRONIZING {MODPACK_NAME} ASSETS...")
    if modpack_dir.exists(): shutil.rmtree(modpack_dir)
    modpack_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        r = requests.get(GITHUB_ZIP_URL, allow_redirects=True)
        zip_path = modpack_dir / "temp.zip"
        with open(zip_path, 'wb') as f: f.write(r.content)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref: zip_ref.extractall(modpack_dir)
        os.remove(zip_path)

        # Deep search for 'overrides'
        ov_found = None
        for root, dirs, files in os.walk(modpack_dir):
            if "overrides" in dirs:
                ov_found = Path(root) / "overrides"
                break
        
        if ov_found:
            print_prof("[+] MAPPING OVERRIDES LAYER...")
            for item in ov_found.iterdir():
                target = modpack_dir / item.name
                if target.exists():
                    if target.is_dir(): shutil.rmtree(target)
                    else: os.remove(target)
                shutil.move(str(item), str(modpack_dir))
        
        # Cleanup
        for item in modpack_dir.iterdir():
            if item.is_dir() and item.name in ["modpack", "overrides"]: shutil.rmtree(item)
            elif item.name in ["manifest.json", "modlist.html"]: os.remove(item)

        # 3. Inject Profile with Strict Metadata
        print_prof("[+] WRITING CRANIX METADATA TO LAUNCHER_PROFILES.JSON...")
        prof_json = mc_path / "launcher_profiles.json"
        with open(prof_json, 'r') as f: data = json.load(f)
        
        # Remove old Cranix profiles
        data['profiles'] = {k: v for k, v in data.get('profiles', {}).items() if v.get('name') != MODPACK_NAME}
        
        p_id = uuid.uuid4().hex
        data['profiles'][p_id] = {
            "name": MODPACK_NAME,
            "type": "custom",
            "gameDir": str(modpack_dir),
            "lastVersionId": MINECRAFT_VERSION,
            "icon": "Grass"
        }
        with open(prof_json, 'w') as f: json.dump(data, f, indent=2)

        print(BRIGHT_GREEN + "\n" + "="*86)
        print_prof("INITIALIZATION SUCCESSFUL. CRANIX LTD PROTOCOLS ARE LIVE.", 0.02, BRIGHT_GREEN)
        print("="*86 + RESET + "\n")
        
        launch_minecraft_java()
        time.sleep(2)
    except Exception as e:
        print_prof(f"[!] CRITICAL SYSTEM ERROR: {e}")
        input("\nPRESS ENTER TO EXIT...")

if __name__ == "__main__":
    run_installer()