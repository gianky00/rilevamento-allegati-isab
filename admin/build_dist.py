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
DIST_DIR = "dist"
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

def run_command(cmd, cwd=None):
    """Esegue un comando shell stampandolo a video in tempo reale."""
    log_and_print(f"Running: {' '.join(cmd)}")

    process = subprocess.Popen(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
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
        log_and_print(f"PyInstaller verified at: {os.path.dirname(PyInstaller.__file__)}")
    except ImportError:
        log_and_print("CRITICAL: PyInstaller module not found in this environment!", "ERROR")
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
        log_and_print("CRITICAL: Inno Setup Compiler (ISCC.exe) not found!", "ERROR")
        if os.name == 'nt':
            log_and_print("Please install Inno Setup 6.", "ERROR")
            sys.exit(1)

    return iscc_path

def build():
    try:
        log_and_print("Starting Build Process...")

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

        log_and_print("\n--- Step 5/7: Packaging with PyInstaller ---")
        sep = ";" if os.name == 'nt' else ":"
        runtime_dir = None
        for name in os.listdir(OBF_DIR):
            if name.startswith("pyarmor_runtime_") and os.path.isdir(os.path.join(OBF_DIR, name)):
                runtime_dir = name
                break
        if not runtime_dir:
            log_and_print("ERROR: PyArmor runtime folder not found inside obfuscated dir!", "ERROR")
            sys.exit(1)

        # PyInstaller Command
        cmd_pyinstaller = [
            sys.executable, "-m", "PyInstaller",
            "--name", APP_NAME,
            "--onedir",
            "--console", # Keep console for debugging initially, switch to --windowed for release
            "--clean",
            "--noconfirm",
            "--distpath", DIST_DIR,
            "--workpath", os.path.join(DIST_DIR, "build"),
            f"--paths={OBF_DIR}",
        ]

        # Add PyArmor runtime
        cmd_pyinstaller.extend(["--add-data", f"{os.path.join(OBF_DIR, runtime_dir)}{sep}{runtime_dir}"])

        # Hidden imports relevant to this project
        hidden_imports = [
            "tkinter", "PIL", "fitz", "pytesseract", "cryptography",
            "config_manager", "pdf_processor", "license_validator"
        ]

        for imp in hidden_imports:
            cmd_pyinstaller.extend(["--hidden-import", imp])

        # Point to the obfuscated entry script
        cmd_pyinstaller.append(os.path.join(OBF_DIR, ENTRY_SCRIPT))

        run_command(cmd_pyinstaller)

        log_and_print("\n--- Step 6/7: Post-Build Cleanup & License Setup ---")

        output_folder = os.path.abspath(os.path.join(DIST_DIR, APP_NAME))

        # Ensure 'Licenza' folder exists in output (empty is fine, it will be populated by user or admin)
        lic_dest_dir = os.path.join(output_folder, "Licenza")
        os.makedirs(lic_dest_dir, exist_ok=True)

        # Also copy config.json to output root if needed
        if os.path.exists(os.path.join(OBF_DIR, "config.json")):
             shutil.copy(os.path.join(OBF_DIR, "config.json"), os.path.join(output_folder, "config.json"))

        log_and_print("\n--- Step 7/7: Compiling Installer with Inno Setup ---")

        iss_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "setup_script.iss"))

        if not os.path.exists(iss_path):
            log_and_print(f"Setup script not found at: {iss_path}", "ERROR")
            sys.exit(1)

        cmd_iscc = [
            iscc_exe,
            f"/DMyAppVersion=1.0.0",
            f"/DBuildDir={output_folder}",
            iss_path
        ]

        run_command(cmd_iscc)

        log_and_print("="*60)
        log_and_print("BUILD AND PACKAGING COMPLETE SUCCESS!")
        log_and_print("="*60)

    except Exception as e:
        logger.exception("FATAL ERROR DURING BUILD:")
        sys.exit(1)

if __name__ == "__main__":
    build()
