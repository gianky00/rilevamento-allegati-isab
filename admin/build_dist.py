import subprocess
import os
import shutil
import sys
import time
import logging

# --- CONFIGURAZIONE ---
# 1. FIX PORTABILITÀ: Directory corrente = cartella dello script
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Calcola la ROOT del progetto (due livelli sopra admin/build_dist.py -> root)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

ENTRY_SCRIPT = "main.py"
APP_NAME = "PDF-Splitter"
DIST_DIR = os.path.join(ROOT_DIR, "dist")
OBF_DIR = os.path.join(DIST_DIR, "obfuscated")
BUILD_LOG = "build_log.txt"

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
        stderr=subprocess.STDOUT,
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
            os.path.join(ROOT_DIR, "license_validator.py")
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

        # Build output directory
        # nuitka_output_dir = os.path.join(DIST_DIR, f"{APP_NAME}.dist") # Not directly used in command

        # Nuitka Command
        cmd_nuitka = [
            sys.executable, "-m", "nuitka",
            "--standalone",
            f"--output-dir={DIST_DIR}",
            "--enable-plugin=tk-inter",
            # Include the pyarmor runtime package
            f"--include-package={runtime_dir}",
            # Include tkinterdnd2 package data (binaries)
            "--include-package-data=tkinterdnd2",
            # Point to the entry script in the OBFUSCATED directory
            os.path.join(OBF_DIR, ENTRY_SCRIPT)
        ]

        # Windows-specific options
        if os.name == 'nt':
             cmd_nuitka.append("--disable-console")

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
        # Based on previous PyInstaller hidden_imports list.
        explicit_modules = [
            "fitz", # PyMuPDF
            "PIL", # Pillow
            "pytesseract",
            "cffi",
            "cryptography",
            "numpy", # Required by pytesseract
            "tkinterdnd2", # Required for Drag & Drop
            # Internal modules (obfuscated ones) should be found via PYTHONPATH, but
            # explicit inclusion ensures they are treated as modules if not imported by entry point.
        ]

        for mod in explicit_modules:
            cmd_nuitka.append(f"--include-package={mod}")

        # Add PYTHONPATH to include OBF_DIR so Nuitka finds the modules there
        env = os.environ.copy()
        env["PYTHONPATH"] = OBF_DIR + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")

        # Important: Run from OBF_DIR so that `import config_manager` works relative to current dir
        # if Nuitka uses cwd for resolution.
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
        # NOTE: We DO NOT copy files from source 'Licenza' because they are client-specific.
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

        if iscc_exe:
            iss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "setup_script.iss"))

            if not os.path.exists(iss_path):
                log_and_print(f"Setup script not found at: {iss_path}", "ERROR")
                sys.exit(1)

            # Inno Setup expects build dir passed as define
            cmd_iscc = [
                iscc_exe,
                f"/DMyAppVersion=1.0.0",
                f"/DBuildDir={final_dist_path}",
                iss_path
            ]

            run_command(cmd_iscc, env=env) # Passing env just in case
        else:
             log_and_print("Skipping Installer compilation (ISCC not found).", "WARNING")

        log_and_print("="*60)
        log_and_print("BUILD AND PACKAGING COMPLETE SUCCESS!")
        log_and_print("="*60)

    except Exception as e:
        logger.exception("FATAL ERROR DURING BUILD:")
        sys.exit(1)

if __name__ == "__main__":
    build()
