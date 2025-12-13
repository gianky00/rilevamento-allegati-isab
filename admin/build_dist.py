import subprocess
import os
import shutil
import sys
import time
import logging
import json
import zipfile
import requests

# --- CONFIGURAZIONE ---
# 1. FIX PORTABILITÀ: Directory corrente = cartella dello script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Calcola la ROOT del progetto (due livelli sopra admin/build_dist.py -> root)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add root to path to import version
sys.path.append(ROOT_DIR)
import version

ENTRY_SCRIPT = "main.py"
APP_NAME = "Intelleo PDF Splitter"
APP_VERSION = version.__version__
DIST_DIR = os.path.join(ROOT_DIR, "dist")
OBF_DIR = os.path.join(DIST_DIR, "obfuscated")
BUILD_LOG = "build_log.txt"

# Netlify Configuration
NETLIFY_SITE_NAME = "intelleo-pdf-splitter"

# Setup Logging
file_handler = logging.FileHandler(BUILD_LOG, mode='w', encoding='utf-8')
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

# --- UTILITÀ DI SISTEMA ---

def log_and_print(message, level="INFO"):
    """Logga su file e stampa a video."""
    print(message)
    sys.stdout.flush()
    if level == "INFO":
        logger.info(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)

def run_command(cmd, cwd=None, shell=False, env=None):
    """Esegue un comando shell stampandolo a video in tempo reale."""
    log_and_print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")

    # Use passed env or default to system env
    if env is None:
        env = os.environ.copy()

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, # Redirect stderr to stdout to see errors in stream
        text=True,
        bufsize=1,
        universal_newlines=True,
        shell=shell,
        env=env
    )

    while True:
        line = process.stdout.readline()
        if not line and process.poll() is not None:
            break
        if line:
            line = line.rstrip()
            print(line)
            sys.stdout.flush()
            logger.info(f"[CMD] {line}")

    return_code = process.poll()
    if return_code != 0:
        log_and_print(f"Error running command: {cmd}", "ERROR")
        sys.exit(return_code)

def kill_existing_process():
    """Uccide eventuali processi 'PDF-Splitter.exe' rimasti appesi."""
    log_and_print("--- Step 0/7: Cleaning active processes ---")
    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_and_print(f"Killed active {APP_NAME}.exe instances (if any).")
            time.sleep(1)
        except Exception:
            pass

def verify_environment():
    """Verifica lo stato dell'ambiente di build."""
    log_and_print("--- Step 1/7: Environment Diagnostics ---")
    log_and_print(f"Running with Python: {sys.executable}")

    # Verify Nuitka availability
    try:
        import nuitka
        log_and_print(f"Nuitka verified at: {os.path.dirname(nuitka.__file__)}")
    except ImportError:
        log_and_print("CRITICAL: Nuitka module not found in this environment!", "ERROR")
        log_and_print("Please run: pip install nuitka zstandard", "ERROR")
        sys.exit(1)

    iscc_path = shutil.which("ISCC.exe")
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
    ]

    if not iscc_path and os.name == 'nt':
        for p in possible_paths:
            if os.path.exists(p):
                iscc_path = p
                break

    if iscc_path:
        log_and_print(f"Inno Setup Compiler found: {iscc_path}")
    else:
        log_and_print("WARNING: Inno Setup Compiler (ISCC.exe) not found! Installer step will be skipped.", "WARNING")

    return iscc_path

def build():
    try:
        log_and_print("Starting Build Process with Nuitka...")

        kill_existing_process()

        iscc_exe = verify_environment()

        if os.path.exists(DIST_DIR):
            try:
                shutil.rmtree(DIST_DIR)
            except PermissionError:
                log_and_print("ERROR: File locked. Close the app or the dist folder.", "ERROR")
                sys.exit(1)

        os.makedirs(OBF_DIR, exist_ok=True)

        log_and_print("\n--- Step 3/7: Obfuscating with PyArmor ---")

        # Files to obfuscate
        target_files = [
            os.path.join(ROOT_DIR, "main.py"),
            os.path.join(ROOT_DIR, "pdf_processor.py"),
            os.path.join(ROOT_DIR, "config_manager.py"),
            os.path.join(ROOT_DIR, "roi_utility.py"),
            os.path.join(ROOT_DIR, "license_validator.py"),
            os.path.join(ROOT_DIR, "license_updater.py"),
            os.path.join(ROOT_DIR, "app_updater.py"),
            os.path.join(ROOT_DIR, "version.py")
        ]

        # Check if files exist
        valid_targets = [f for f in target_files if os.path.exists(f)]

        cmd_pyarmor = [
            sys.executable, "-m", "pyarmor.cli", "gen",
            "-O", OBF_DIR,
        ]
        cmd_pyarmor.extend(valid_targets)

        run_command(cmd_pyarmor)

        log_and_print("\n--- Step 4/7: Preparing Assets for Packaging ---")

        # Copy requirements.txt
        if os.path.exists(os.path.join(ROOT_DIR, "requirements.txt")):
            shutil.copy(os.path.join(ROOT_DIR, "requirements.txt"), os.path.join(OBF_DIR, "requirements.txt"))

        # Copy config.json (default config) if exists
        if os.path.exists(os.path.join(ROOT_DIR, "config.json")):
             shutil.copy(os.path.join(ROOT_DIR, "config.json"), os.path.join(OBF_DIR, "config.json"))

        log_and_print("\n--- Step 5/7: Packaging with Nuitka ---")

        # Identify PyArmor runtime
        runtime_dir = None
        for name in os.listdir(OBF_DIR):
            if name.startswith("pyarmor_runtime_") and os.path.isdir(os.path.join(OBF_DIR, name)):
                runtime_dir = name
                break

        if not runtime_dir:
            log_and_print("ERROR: PyArmor runtime folder not found inside obfuscated dir!", "ERROR")
            sys.exit(1)

        # Nuitka Command
        cmd_nuitka = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            f"--output-dir={DIST_DIR}",
            "--enable-plugin=tk-inter",
            "--show-progress", # Show detailed progress
            # Optimization: Use low memory to avoid exhaustion
            "--low-memory",
            # PREVENT COMPILATION OF PyMuPDF to avoid C1002 (Heap Space) error
            "--nofollow-import-to=fitz",
            "--nofollow-import-to=pymupdf",
            # Include the pyarmor runtime package
            f"--include-package={runtime_dir}",
            # Include tkinterdnd2 package data (binaries)
            "--include-package-data=tkinterdnd2",
            # Point to the entry script in the OBFUSCATED directory
            os.path.join(OBF_DIR, ENTRY_SCRIPT)
        ]

        # Windows-specific options
        if os.name == 'nt':
             # Explicitly disable console window for the final application
             cmd_nuitka.append("--windows-disable-console")

        # Check for Icon
        icon_path = None
        # Look for any .ico file in ROOT_DIR
        for f in os.listdir(ROOT_DIR):
            if f.lower().endswith(".ico"):
                icon_path = os.path.join(ROOT_DIR, f)
                break

        if icon_path:
            log_and_print(f"Using icon: {icon_path}")
            cmd_nuitka.append(f"--windows-icon-from-ico={icon_path}")

        # --- Fix for Hidden Imports ---
        # Since code is obfuscated, Nuitka cannot scan imports. We must explicitly include them.
        explicit_modules = [
            "fitz", # PyMuPDF
            "PIL", # Pillow
            "pytesseract",
            "cffi",
            "cryptography",
            "numpy", # Required by pytesseract
            "tkinterdnd2", # Required for Drag & Drop
            "requests", # Required for license updater
            # Built-in modules are generally handled, but explicit inclusion is safer for key logic
            # However, for built-ins Nuitka usually finds them unless obfuscation hides them completely.
            # But standard library is linked in standalone mode.
        ]

        for mod in explicit_modules:
            cmd_nuitka.append(f"--include-package={mod}")

        # Add PYTHONPATH to include OBF_DIR so Nuitka finds the modules there
        env = os.environ.copy()
        env["PYTHONPATH"] = OBF_DIR + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

        # Important: Run from OBF_DIR so that `import config_manager` works relative to current dir
        run_command(cmd_nuitka, cwd=OBF_DIR, env=env)

        # Rename/Move the output folder
        default_dist_name = "main.dist"
        final_dist_path = os.path.join(DIST_DIR, APP_NAME)

        if os.path.exists(final_dist_path):
            shutil.rmtree(final_dist_path)

        generated_dist = os.path.join(DIST_DIR, default_dist_name)
        if os.path.exists(generated_dist):
            shutil.move(generated_dist, final_dist_path)
        else:
            log_and_print(f"ERROR: Nuitka output directory '{generated_dist}' not found.", "ERROR")
            sys.exit(1)

        # Rename the executable
        default_exe = os.path.join(final_dist_path, "main.exe" if os.name == 'nt' else "main.bin")
        final_exe = os.path.join(final_dist_path, f"{APP_NAME}.exe" if os.name == 'nt' else APP_NAME)
        if os.path.exists(default_exe):
            shutil.move(default_exe, final_exe)

        log_and_print("\n--- Step 6/7: Post-Build Cleanup & License Setup ---")

        # Create empty 'Licenza' folder in output
        lic_dest_dir = os.path.join(final_dist_path, "Licenza")
        os.makedirs(lic_dest_dir, exist_ok=True)
        log_and_print("Created empty 'Licenza' folder structure.")

        # Also copy config.json to output root if needed
        if os.path.exists(os.path.join(OBF_DIR, "config.json")):
             shutil.copy(os.path.join(OBF_DIR, "config.json"), os.path.join(final_dist_path, "config.json"))

        # Copy Tesseract-OCR if exists locally (for portable builds)
        local_tesseract = os.path.join(ROOT_DIR, "Tesseract-OCR")
        if os.path.exists(local_tesseract):
             log_and_print(f"Copying local Tesseract-OCR from {local_tesseract}...")
             shutil.copytree(local_tesseract, os.path.join(final_dist_path, "Tesseract-OCR"), dirs_exist_ok=True)

        log_and_print("\n--- Step 7/7: Compiling Installer with Inno Setup ---")

        setup_filename = None
        if iscc_exe:
            iss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "setup_script.iss"))

            if not os.path.exists(iss_path):
                log_and_print(f"Setup script not found at: {iss_path}", "ERROR")
                sys.exit(1)

            # Inno Setup expects build dir passed as define
            cmd_iscc = [
                iscc_exe,
                f"/DMyAppVersion={APP_VERSION}",
                f"/DBuildDir={final_dist_path}",
                iss_path
            ]

            run_command(cmd_iscc, env=env) # Passing env just in case

            # Locate the generated setup file
            setup_output_dir = os.path.join(DIST_DIR, "Setup")
            if os.path.exists(setup_output_dir):
                log_and_print(f"Installer generated in: {setup_output_dir}")
                # Find the latest setup file
                for f in os.listdir(setup_output_dir):
                    if f.endswith(".exe"):
                        setup_filename = f
                        log_and_print(f" - Found setup: {f}")
                        break
        else:
             log_and_print("Skipping Installer compilation (ISCC not found).", "WARNING")

        # --- Step 8: Netlify Deployment Preparation & Upload ---
        if setup_filename:
            log_and_print("\n--- Step 8/8: Preparing & Uploading to Netlify ---")
            prepare_and_deploy_netlify(setup_output_dir, setup_filename)

        log_and_print("="*60)
        log_and_print("BUILD AND PACKAGING COMPLETE SUCCESS!")
        log_and_print("="*60)

    except Exception as e:
        logger.exception("FATAL ERROR DURING BUILD:")
        sys.exit(1)

def get_netlify_token():
    """Returns the obfuscated Netlify API token."""
    # Obfuscated token parts
    p1 = "nfp_VJbSMoKXxms3"
    p2 = "Xa8gdQkKKedPC6"
    p3 = "EnHQZL9687"
    return p1 + p2 + p3

def get_netlify_site_id(site_name, token):
    """
    Retrieves the Site ID for a given site name using the Netlify API.
    """
    try:
        log_and_print(f"Fetching Site ID for '{site_name}'...")
        url = "https://api.netlify.com/api/v1/sites"
        headers = {"Authorization": f"Bearer {token}"}

        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            sites = response.json()
            for site in sites:
                if site.get("name") == site_name:
                    return site.get("site_id")
            log_and_print(f"Site '{site_name}' not found in account.", "ERROR")
        else:
            log_and_print(f"Error fetching sites: {response.status_code} - {response.text}", "ERROR")
    except Exception as e:
        log_and_print(f"Exception getting Site ID: {e}", "ERROR")
    return None

def generate_index_html(deploy_dir, setup_filename, version_str):
    """Generates a professional index.html download page."""
    html_content = f"""<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Download {APP_NAME}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            text-align: center;
            max-width: 500px;
            width: 90%;
        }}
        h1 {{ margin-bottom: 10px; color: #2c3e50; }}
        p {{ color: #666; margin-bottom: 30px; }}
        .btn {{
            display: inline-block;
            background-color: #007bff;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            font-size: 18px;
            border-radius: 6px;
            transition: background-color 0.3s;
        }}
        .btn:hover {{ background-color: #0056b3; }}
        .version-info {{ margin-top: 20px; font-size: 14px; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{APP_NAME}</h1>
        <p>Strumento professionale per la divisione e classificazione automatica dei PDF.</p>

        <a href="{setup_filename}" class="btn">Scarica per Windows</a>

        <div class="version-info">
            Versione Corrente: <strong>v{version_str}</strong><br>
            Ultimo Aggiornamento: {time.strftime('%d/%m/%Y')}
        </div>
    </div>
</body>
</html>"""

    with open(os.path.join(deploy_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    log_and_print("Generated index.html")

def prepare_and_deploy_netlify(setup_dir, setup_filename):
    """
    Creates a deploy folder with version.json, index.html, and the setup file,
    then uploads to Netlify.
    """
    deploy_dir = os.path.join(ROOT_DIR, "dist", "deploy")
    if os.path.exists(deploy_dir):
        shutil.rmtree(deploy_dir)
    os.makedirs(deploy_dir)

    # 1. Copy Setup File
    src_setup = os.path.join(setup_dir, setup_filename)
    dst_setup = os.path.join(deploy_dir, setup_filename)
    shutil.copy(src_setup, dst_setup)
    log_and_print(f"Copied setup to: {deploy_dir}")

    # 2. Generate version.json
    base_url = version.UPDATE_URL.rsplit('/', 1)[0]
    download_url = f"{base_url}/{setup_filename}"

    version_data = {
        "version": version.__version__,
        "url": download_url
    }

    with open(os.path.join(deploy_dir, "version.json"), "w") as f:
        json.dump(version_data, f, indent=4)
    log_and_print(f"Generated version.json (v{version.__version__})")

    # 3. Generate Landing Page
    generate_index_html(deploy_dir, setup_filename, version.__version__)

    # 4. Netlify Credentials & Upload
    auth_token = get_netlify_token()
    site_id = get_netlify_site_id(NETLIFY_SITE_NAME, auth_token)

    if not site_id:
        log_and_print("CRITICAL: Could not find Netlify Site ID. Deployment aborted.", "ERROR")
        return

    log_and_print(f"Ready to deploy to Site ID: {site_id}")
    log_and_print("Starting automatic upload to Netlify...")

    zip_path = os.path.join(ROOT_DIR, "dist", "deploy.zip")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(deploy_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, deploy_dir)
                zipf.write(file_path, arcname)

    try:
        with open(zip_path, 'rb') as f:
            data = f.read()

        url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
        headers = {
            "Content-Type": "application/zip",
            "Authorization": f"Bearer {auth_token}"
        }

        response = requests.post(url, headers=headers, data=data, timeout=300)

        if response.status_code == 200:
            log_and_print("-" * 40)
            log_and_print("DEPLOY SUCCESSFUL!", "INFO")
            log_and_print(f"Live URL: {response.json().get('url')}")
            log_and_print(f"Admin Console: {response.json().get('admin_url')}")
            log_and_print("-" * 40)
        else:
            log_and_print(f"Upload Failed: {response.status_code} - {response.text}", "ERROR")

    except Exception as e:
        log_and_print(f"Error during Netlify upload: {e}", "ERROR")
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)

if __name__ == "__main__":
    build()
