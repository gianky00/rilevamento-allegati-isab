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

# Calcola la ROOT del progetto (tre livelli sopra admin/Crea Setup/build_dist.py -> root)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Add src to path to import version
sys.path.append(os.path.join(ROOT_DIR, "src"))
import version

ENTRY_SCRIPT = "src/app_launcher.py"
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

    # Verify PyInstaller availability
    try:
        import PyInstaller
        log_and_print(f"PyInstaller verified: {PyInstaller.__version__}")
    except ImportError:
        log_and_print("CRITICAL: PyInstaller module not found!", "ERROR")
        log_and_print("Please run: pip install pyinstaller", "ERROR")
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
        log_and_print("Starting Build Process with PyInstaller...")

        kill_existing_process()

        iscc_exe = verify_environment()

        if os.path.exists(DIST_DIR):
            try:
                shutil.rmtree(DIST_DIR)
            except PermissionError:
                log_and_print("ERROR: File locked. Close the app or the dist folder.", "ERROR")
                sys.exit(1)

        os.makedirs(OBF_DIR, exist_ok=True)

        log_and_print("\n--- Step 3/7: Obfuscating Entire SRC recursively with PyArmor ---")

        # Obfuscate the entire src directory recursively
        # Run from 'src' to avoid 'src/' prefix in OBF_DIR
        cmd_pyarmor = [
            sys.executable, "-m", "pyarmor.cli", "gen",
            "-r",                  # RECURSIVE
            "-O", OBF_DIR,         # OUTPUT DIR
            "."                    # SOURCE
        ]

        run_command(cmd_pyarmor, cwd=os.path.join(ROOT_DIR, "src"))

        log_and_print("\n--- Step 4/7: Preparing Assets for Packaging ---")

        # Copy requirements.txt
        if os.path.exists(os.path.join(ROOT_DIR, "src", "requirements.txt")):
            shutil.copy(os.path.join(ROOT_DIR, "src", "requirements.txt"), os.path.join(OBF_DIR, "requirements.txt"))

        # Copy config.json (default config) if exists in root
        if os.path.exists(os.path.join(ROOT_DIR, "config.json")):
             shutil.copy(os.path.join(ROOT_DIR, "config.json"), os.path.join(OBF_DIR, "config.json"))

        log_and_print("\n--- Step 5/7: Packaging with PyInstaller ---")

        # Identify PyArmor runtime
        runtime_dir = None
        for name in os.listdir(OBF_DIR):
            if name.startswith("pyarmor_runtime_") and os.path.isdir(os.path.join(OBF_DIR, name)):
                runtime_dir = name
                break

        if not runtime_dir:
            log_and_print("ERROR: PyArmor runtime folder not found inside obfuscated dir!", "ERROR")
            sys.exit(1)

        # Check for Icon
        icon_path = os.path.join(ROOT_DIR, "src", "resources", "icon.ico")
        if os.path.exists(icon_path):
             log_and_print(f"Using icon: {icon_path}")
        else:
             icon_path = None
             log_and_print("WARNING: src/resources/icon.ico not found.", "WARNING")

        # Construct PyInstaller Command
        cmd_pyinstaller = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--clean",
            f"--name={APP_NAME}",
            f"--distpath={DIST_DIR}",
            f"--workpath={os.path.join(DIST_DIR, 'build')}",
            f"--paths={OBF_DIR}", # Look for modules in OBF_DIR
            "--onedir",
            "--collect-all=PySide6",
            "--collect-all=pymupdf",
            f"--additional-hooks-dir={os.path.abspath(os.path.join(os.path.dirname(__file__), 'hooks'))}",
            "--uac-admin" # FORCE ADMIN PRIVILEGES (UAC)
        ]

        # Add resources data
        if icon_path:
            # On Windows, use semicolon
            sep = ";" if os.name == 'nt' else ":"
            cmd_pyinstaller.append(f"--add-data={icon_path}{sep}resources")

        if os.name == 'nt':
             cmd_pyinstaller.append("--windowed")
             if icon_path:
                 cmd_pyinstaller.append(f"--icon={icon_path}")

        # Hidden imports
        # We must explicitly import the pyarmor runtime and all local obfuscated modules
        # because PyInstaller cannot analyze imports inside obfuscated code.
        hidden_imports = [
            "fitz", "PIL", "pytesseract", "cffi", "cryptography", "cryptography.fernet",
            "numpy", "requests", "logging", "traceback", "uuid", "platform", "hashlib", "shutil", "json", "datetime", "queue", "threading", "subprocess",
            
            # PySide6
            "PySide6", "PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvgWidgets",
            "pymupdf",

            # Top level modules
            "main", "app_launcher", "app_logger", "config_manager", "roi_utility", "license_validator", "license_updater", "app_updater", "version",

            # Core package
            "core",
            "core.analysis_service",
            "core.app_controller",
            "core.archive_service",
            "core.classifier",
            "core.file_service",
            "core.notification_manager",
            "core.ocr_engine",
            "core.path_manager",
            "core.pdf_manager",
            "core.pdf_processor",
            "core.pdf_splitter",
            "core.processing_worker",
            "core.roi_controller",
            "core.roi_manager",
            "core.rule_service",
            "core.session_manager",
            "core.tesseract_manager",

            # GUI package
            "gui",
            "gui.theme",
            "gui.ui_factory",
            "gui.dialogs",
            "gui.dialogs.roi_selector_dialog",
            "gui.dialogs.rule_editor",
            "gui.dialogs.unknown_review",
            "gui.tabs",
            "gui.tabs.config_tab",
            "gui.tabs.dashboard_tab",
            "gui.tabs.help_tab",
            "gui.tabs.processing_tab",
            "gui.widgets",
            "gui.widgets.drop_frame",
            "gui.widgets.pdf_graphics_view",
            "gui.widgets.preview_view",
            "gui.widgets.roi_renderer",

            # Shared package
            "shared",
            "shared.constants",

            # PyArmor runtime
            runtime_dir
        ]

        for mod in hidden_imports:
            cmd_pyinstaller.append(f"--hidden-import={mod}")

        # Entry point: use the obfuscated app_launcher.py
        # Check if it's in OBF_DIR/app_launcher.py or OBF_DIR/src/app_launcher.py
        entry_point = os.path.join(OBF_DIR, "app_launcher.py")
        if not os.path.exists(entry_point):
            entry_point = os.path.join(OBF_DIR, "src", "app_launcher.py")
            # If it's in src/, we need to add OBF_DIR/src to paths
            if os.path.exists(entry_point):
                cmd_pyinstaller.append(f"--paths={os.path.join(OBF_DIR, 'src')}")
            else:
                log_and_print(f"ERROR: Could not find obfuscated entry point app_launcher.py in {OBF_DIR}", "ERROR")
                sys.exit(1)

        cmd_pyinstaller.append(entry_point)

        # Add PYTHONPATH to include OBF_DIR
        env = os.environ.copy()
        env["PYTHONPATH"] = OBF_DIR + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

        # Run PyInstaller
        # We run it from OBF_DIR to help it resolve relative paths if any, though --paths handles modules
        run_command(cmd_pyinstaller, cwd=OBF_DIR, env=env)

        # Check Output
        final_dist_path = os.path.join(DIST_DIR, APP_NAME)
        if not os.path.exists(final_dist_path):
            log_and_print(f"ERROR: Expected output directory '{final_dist_path}' not found.", "ERROR")
            sys.exit(1)

        log_and_print("\n--- Step 6/7: Post-Build Cleanup & License Setup ---")

        # Also copy config.json to output root if needed
        # PyInstaller doesn't automatically copy data files unless specified, and we modified source.
        # We manually copy config.json to the dist folder if it's not there.
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
            setup_output_dir = os.path.join(os.path.dirname(__file__), "Setup")

            # Clean previous setup files to avoid version mix-up
            if os.path.exists(setup_output_dir):
                for f in os.listdir(setup_output_dir):
                    if f.endswith(".exe"):
                        try:
                            os.remove(os.path.join(setup_output_dir, f))
                            log_and_print(f"Cleaned old setup: {f}")
                        except Exception as e:
                            log_and_print(f"Warning: Could not delete old setup {f}: {e}", "WARNING")

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

            run_command(cmd_iscc, env=env)

            # Locate the generated setup file
            if os.path.exists(setup_output_dir):
                log_and_print(f"Installer generated in: {setup_output_dir}")
                
                # Find the latest setup file (Sort by modification time, newest first)
                exe_files = [f for f in os.listdir(setup_output_dir) if f.endswith(".exe")]
                if exe_files:
                    exe_files.sort(key=lambda x: os.path.getmtime(os.path.join(setup_output_dir, x)), reverse=True)
                    setup_filename = exe_files[0]
                    log_and_print(f" - Found newest setup: {setup_filename}")

            if not setup_filename:
                log_and_print(f"WARNING: No executable found in {setup_output_dir}", "WARNING")
        else:
             log_and_print("Skipping Installer compilation (ISCC not found).", "WARNING")

        # --- Step 8: Netlify Deployment Preparation & Upload ---
        skip_deploy = "--no-deploy" in sys.argv
        
        if setup_filename and not skip_deploy:
            log_and_print("\n--- Step 8/8: Preparing & Uploading to Netlify ---")
            prepare_and_deploy_netlify(setup_output_dir, setup_filename)
        elif skip_deploy:
            log_and_print("\n[INFO] Skipping Netlify deployment (--no-deploy flag detected).", "INFO")
        else:
            log_and_print("\n[WARNING] Skipping Netlify deployment because installer was not found.", "WARNING")

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
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body {{
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .card {{
            border: none;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            max-width: 500px;
            width: 90%;
        }}
        .card-header {{
            background-color: white;
            border-bottom: none;
            padding-top: 30px;
            border-radius: 15px 15px 0 0 !important;
        }}
        .app-icon {{
            font-size: 4rem;
            color: #0d6efd;
        }}
        .btn-download {{
            padding: 15px 30px;
            font-size: 1.2rem;
            font-weight: 600;
            border-radius: 50px;
            box-shadow: 0 4px 6px rgba(13, 110, 253, 0.3);
            transition: all 0.3s ease;
        }}
        .btn-download:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 12px rgba(13, 110, 253, 0.4);
        }}
        .features-list {{
            text-align: left;
            margin: 20px 0;
            color: #6c757d;
        }}
        .features-list li {{
            margin-bottom: 8px;
        }}
    </style>
</head>
<body>
    <div class="card text-center p-4">
        <div class="card-header">
            <i class="bi bi-file-earmark-pdf-fill app-icon"></i>
            <h2 class="mt-3 fw-bold text-primary">{APP_NAME}</h2>
            <p class="text-muted">Soluzione professionale per la gestione documentale</p>
        </div>
        <div class="card-body">
            <ul class="list-unstyled features-list mx-auto" style="max-width: 300px;">
                <li><i class="bi bi-check-circle-fill text-success me-2"></i>Divisione automatica PDF</li>
                <li><i class="bi bi-check-circle-fill text-success me-2"></i>Riconoscimento OCR intelligente</li>
                <li><i class="bi bi-check-circle-fill text-success me-2"></i>Gestione Regole e ROI</li>
            </ul>

            <a href="{setup_filename}" class="btn btn-primary btn-download w-100 my-3">
                <i class="bi bi-windows me-2"></i> Scarica per Windows
            </a>

            <div class="mt-4 pt-3 border-top">
                <div class="row text-muted small">
                    <div class="col-6 text-start">
                        Versione: <span class="fw-bold text-dark">v{version_str}</span>
                    </div>
                    <div class="col-6 text-end">
                        Data: {time.strftime('%d/%m/%Y')}
                    </div>
                </div>
            </div>
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
                log_and_print(f"  + Added to zip: {arcname}")

    # Check zip size
    if os.path.exists(zip_path):
        size_mb = os.path.getsize(zip_path) / (1024 * 1024)
        log_and_print(f"Zip created successfully. Size: {size_mb:.2f} MB")

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
