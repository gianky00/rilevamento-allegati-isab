"""
Script per automatizzare il processo di build, offuscamento e packaging.
Gestisce l'offuscamento con PyArmor, il packaging con PyInstaller,
la creazione del setup con Inno Setup, il deploy su Netlify e il deploy locale su rete.
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import time
import zipfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path

import requests

# --- CONFIGURAZIONE ---
os.chdir(Path(__file__).resolve().parent)
ROOT_DIR = Path(__file__).resolve().parents[2]

# Modernizzazione: sys.path.extend al posto di append multipli
sys.path.extend([str(ROOT_DIR / "src"), str(Path(__file__).resolve().parent)])

import bump_version  # noqa: E402

import version  # noqa: E402

ENTRY_SCRIPT = "src/app_launcher.py"
APP_NAME = "Intelleo PDF Splitter"
APP_VERSION = version.__version__
DIST_DIR = ROOT_DIR / "dist"
OBF_DIR = DIST_DIR / "obfuscated"
BUILD_LOG = "build_log.txt"

# Netlify Configuration
NETLIFY_SITE_NAME = "intelleo-pdf-splitter"

# LOCAL NETWORK DEPLOY CONFIGURATION (SYNCROJOB STYLE)
NETWORK_DEPLOY_PATH = Path(r"\\192.168.11.251\Condivisa\ALLEGRETTI\applicazioni\Splitter PDF")

# Setup Logging
file_handler = logging.FileHandler(BUILD_LOG, mode="w", encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

def log_and_print(message, level="INFO"):
    print(message)
    sys.stdout.flush()
    if level == "INFO":
        logger.info(message)
    elif level == "ERROR":
        logger.error(message)
    elif level == "WARNING":
        logger.warning(message)

def run_command(cmd, cwd=None, shell=False, env=None):
    log_and_print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if env is None:
        env = os.environ.copy()
    process = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, universal_newlines=True, shell=shell, env=env
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
    log_and_print("--- Step 0: Cleaning active processes ---")
    if os.name == "nt":
        with suppress(Exception):
            subprocess.run(["taskkill", "/F", "/IM", f"{APP_NAME}.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            log_and_print(f"Killed active {APP_NAME}.exe instances.")
            time.sleep(1)

def verify_environment():
    log_and_print("--- Step 1: Environment Diagnostics ---")
    try:
        import PyInstaller
        log_and_print(f"PyInstaller verified: {PyInstaller.__version__}")
    except ImportError:
        log_and_print("CRITICAL: PyInstaller not found!", "ERROR")
        sys.exit(1)
    iscc_path = shutil.which("ISCC.exe")
    possible_paths = [r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe", r"C:\Program Files\Inno Setup 6\ISCC.exe"]
    if not iscc_path:
        for p in possible_paths:
            if Path(p).exists():
                iscc_path = p
                break
    if iscc_path:
        log_and_print(f"Inno Setup found: {iscc_path}")
    else:
        log_and_print("WARNING: ISCC.exe not found!", "WARNING")
    return iscc_path

def deploy_to_network(setup_dir, setup_filename):
    """Copia il setup sul percorso di rete riorganizzando la directory (Archivio)."""
    log_and_print("\n--- Step Extra: Deploying to Network Path (SyncroJob Style) ---")
    if not NETWORK_DEPLOY_PATH.exists():
        log_and_print(f"ERROR: Network path not reachable: {NETWORK_DEPLOY_PATH}", "ERROR")
        return False

    try:
        archive_dir = NETWORK_DEPLOY_PATH / "Archivio"
        archive_dir.mkdir(exist_ok=True)

        dst_path = NETWORK_DEPLOY_PATH / setup_filename

        # 1. Riorganizzazione: Spostamento vecchio file in Archivio
        if dst_path.exists():
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            old_version_name = f"OLD_{timestamp}_{setup_filename}"

            old_v_json = NETWORK_DEPLOY_PATH / "version.json"
            if old_v_json.exists():
                with suppress(Exception):
                    old_v_data = json.loads(old_v_json.read_text(encoding="utf-8"))
                    v_str = old_v_data.get("version", "unknown").replace(".", "_")
                    old_version_name = f"{APP_NAME}_v{v_str}_{timestamp}.exe"

            target_archive = archive_dir / old_version_name
            log_and_print(f"Archiving existing version to: {target_archive.name}")
            shutil.move(str(dst_path), str(target_archive))

        # 2. Copia nuovo setup
        log_and_print(f"Copying {setup_filename} to {NETWORK_DEPLOY_PATH}...")
        shutil.copy2(str(setup_dir / setup_filename), str(dst_path))

        # 3. Copia version.json aggiornato
        version_json_src = DIST_DIR / "deploy" / "version.json"
        if version_json_src.exists():
            shutil.copy2(str(version_json_src), str(NETWORK_DEPLOY_PATH / "version.json"))
            log_and_print("SUCCESS: version.json updated on network")

        log_and_print("SUCCESS: Network deploy completed and reorganized.")
        return True
    except Exception as e:
        log_and_print(f"FAILED network deploy: {e}", "ERROR")
        return False

def build():
    global APP_VERSION
    try:
        log_and_print("="*60)
        log_and_print(f" STARTING BUILD FOR {APP_NAME} v{APP_VERSION}")
        log_and_print("="*60)

        # 1. Automatic BUMP
        if "--no-bump" not in sys.argv:
            log_and_print("Bumping version...")
            part = "patch"
            if "--minor" in sys.argv:
                part = "minor"
            elif "--major" in sys.argv:
                part = "major"
            new_v = bump_version.bump_version(part)
            if new_v:
                APP_VERSION = new_v
                import importlib
                importlib.reload(version)

        kill_existing_process()
        iscc_exe = verify_environment()

        if DIST_DIR.exists():
            with suppress(PermissionError):
                shutil.rmtree(DIST_DIR)

        OBF_DIR.mkdir(parents=True, exist_ok=True)
        log_and_print("\n--- Step 3: Obfuscating with PyArmor ---")
        # Includiamo esplicitamente tutti i pacchetti per PyArmor
        cmd_pyarmor = [sys.executable, "-m", "pyarmor.cli", "gen", "-r", "-O", str(OBF_DIR), "."]
        run_command(cmd_pyarmor, cwd=str(ROOT_DIR / "src"))

        log_and_print("\n--- Step 4: Preparing Assets ---")
        shutil.copy(str(ROOT_DIR / "src" / "requirements.txt"), str(OBF_DIR / "requirements.txt"))
        if (ROOT_DIR / "config.json").exists():
            shutil.copy(str(ROOT_DIR / "config.json"), str(OBF_DIR / "config.json"))

        runtime_dir = next((p.name for p in OBF_DIR.iterdir() if p.is_dir() and p.name.startswith("pyarmor_runtime_")), None)
        icon_path = str(ROOT_DIR / "src" / "resources" / "icon.ico") if (ROOT_DIR / "src" / "resources" / "icon.ico").exists() else None

        log_and_print("\n--- Step 5: Packaging with PyInstaller ---")
        # Fondamentale aggiungere OBF_DIR ai paths e includere esplicitamente i moduli
        cmd_pyinstaller = [
            sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
            f"--name={APP_NAME}", f"--distpath={DIST_DIR}", f"--workpath={DIST_DIR / 'build'}",
            f"--paths={OBF_DIR}", "--onedir",
            "--collect-all=PySide6", "--collect-all=pymupdf",
            "--collect-all=cryptography", "--collect-all=requests",
            "--collect-all=core", "--collect-all=gui", "--collect-all=shared",
            "--windowed"
        ]
        if icon_path:
            cmd_pyinstaller.extend([f"--icon={icon_path}", f"--add-data={icon_path}{';' if os.name == 'nt' else ':'}resources"])

        # Aggiungiamo i moduli core, gui e shared come hidden-imports per forzarne l'inclusione
        # PyInstaller a volte fallisce l'analisi statica su file offuscati.
        hidden = [
            "fitz", "PIL", "pytesseract", "cffi", "cryptography", "cryptography.fernet",
            "cryptography.hazmat.primitives.kdf.pbkdf2", "cryptography.hazmat.backends.openssl",
            "numpy", "requests", "PySide6", "PySide6.QtCore", "PySide6.QtGui",
            "PySide6.QtWidgets", "PySide6.QtSvgWidgets", "pymupdf", "main",
            "app_launcher", "app_logger", "app_updater", "config_manager",
            "license_updater", "license_validator", "roi_utility", "version",
            "shared", "shared.constants", "shared.security_utils",
            "core", "gui",
            runtime_dir
        ]
        for h in hidden:
            if h:
                cmd_pyinstaller.append(f"--hidden-import={h}")

        cmd_pyinstaller.append(str(OBF_DIR / "app_launcher.py"))
        run_command(cmd_pyinstaller, cwd=str(OBF_DIR))

        final_dist_path = DIST_DIR / APP_NAME
        
        # Copia manuale di cartelle che PyInstaller potrebbe saltare o che servono esterne
        if (OBF_DIR / "config.json").exists():
            shutil.copy(str(OBF_DIR / "config.json"), str(final_dist_path / "config.json"))
        if (ROOT_DIR / "Tesseract-OCR").exists():
            shutil.copytree(str(ROOT_DIR / "Tesseract-OCR"), str(final_dist_path / "Tesseract-OCR"), dirs_exist_ok=True)

        log_and_print("\n--- Step 7: Installer Compilation ---")
        setup_filename = None
        if iscc_exe:
            iss_path = Path(__file__).resolve().parent / "setup_script.iss"
            setup_out = Path(__file__).resolve().parent / "Setup"
            if setup_out.exists():
                [f.unlink() for f in setup_out.iterdir() if f.suffix == ".exe"]
            cmd_iscc = [iscc_exe, f"/DMyAppVersion={APP_VERSION}", f"/DBuildDir={final_dist_path}", str(iss_path)]
            run_command(cmd_iscc)
            exe_files = [f.name for f in setup_out.iterdir() if f.suffix == ".exe"]
            if exe_files:
                exe_files.sort(key=lambda x: (setup_out / x).stat().st_mtime, reverse=True)
                setup_filename = exe_files[0]

        # STEP 8: PREPARE DEPLOY FOLDER
        if setup_filename:
            deploy_dir = DIST_DIR / "deploy"
            deploy_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy(str(Path(__file__).resolve().parent / "Setup" / setup_filename), str(deploy_dir / setup_filename))
            version_data = {"version": APP_VERSION, "url": f"https://{NETLIFY_SITE_NAME}.netlify.app/{setup_filename}"}
            (deploy_dir / "version.json").write_text(json.dumps(version_data, indent=4), encoding="utf-8")
            generate_index_html(deploy_dir, setup_filename, APP_VERSION)

        # NETWORK DEPLOY
        network_success = False
        if setup_filename and "--no-network" not in sys.argv:
            network_success = deploy_to_network(Path(__file__).resolve().parent / "Setup", setup_filename)

        # NETLIFY DEPLOY
        netlify_success = True
        if setup_filename and "--no-deploy" not in sys.argv:
            netlify_success = prepare_and_deploy_netlify(deploy_dir, setup_filename)

        log_and_print("=" * 60)
        log_and_print(f"BUILD {APP_VERSION} COMPLETED!")
        log_and_print(f"Network Deploy: {'OK' if network_success else 'SKIPPED/FAILED'}")
        log_and_print(f"Netlify Deploy: {'OK' if netlify_success else 'SKIPPED/FAILED'}")
        log_and_print("=" * 60)

    except Exception:
        logger.exception("FATAL ERROR:")
        sys.exit(1)

def generate_index_html(deploy_dir, setup_filename, version_str):
    html = f"""<!DOCTYPE html><html><body style='text-align:center; padding:50px; font-family:sans-serif; background:#f4f7f6;'>
    <div style='background:white; padding:40px; border-radius:15px; display:inline-block; box-shadow:0 10px 25px rgba(0,0,0,0.1);'>
    <h1 style='color:#0d6efd;'>{APP_NAME}</h1><p>Versione: <b>v{version_str}</b></p>
    <a href='{setup_filename}' style='display:inline-block; padding:15px 30px; background:#0d6efd; color:white; border-radius:50px; text-decoration:none; font-weight:bold; margin-top:20px;'>Scarica Installer per Windows</a>
    </div></body></html>"""
    (Path(deploy_dir) / "index.html").write_text(html, encoding="utf-8")

def prepare_and_deploy_netlify(deploy_dir, setup_filename):
    """Deploy reale su Netlify usando API."""
    log_and_print("\n--- Step 8: Uploading to Netlify ---")
    try:
        token = "nfp_VJbSMoKXxms3Xa8gdQkKKedPC6EnHQZL9687"
        sites_url = "https://api.netlify.com/api/v1/sites"
        headers = {"Authorization": f"Bearer {token}"}
        r_sites = requests.get(sites_url, headers=headers)
        site_id = next((s['site_id'] for s in r_sites.json() if s['name'] == NETLIFY_SITE_NAME), None)

        if not site_id:
            log_and_print("Error: Netlify Site ID not found", "ERROR")
            return False

        zip_path = DIST_DIR / "deploy.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for f in deploy_dir.iterdir():
                zipf.write(str(f), f.name)

        with open(zip_path, 'rb') as f:
            deploy_url = f"https://api.netlify.com/api/v1/sites/{site_id}/deploys"
            headers["Content-Type"] = "application/zip"
            r_upload = requests.post(deploy_url, headers=headers, data=f, timeout=600)

        if r_upload.status_code == 200:
            log_and_print(f"Netlify Upload SUCCESS: {r_upload.json().get('url')}")
            zip_path.unlink()
            return True
        log_and_print(f"Netlify Upload FAILED: {r_upload.text}", "ERROR")
        return False
    except Exception as e:
        log_and_print(f"Netlify Error: {e}", "ERROR")
        return False

if __name__ == "__main__":
    build()
