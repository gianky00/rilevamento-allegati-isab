import hashlib
import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from datetime import date, timedelta
from tkinter import messagebox, ttk

from cryptography.fernet import Fernet

# Import shared secret from the root validator if possible, or duplicate it.
# To keep it simple and robust for the admin tool, we duplicate the key here.
LICENSE_SECRET_KEY = b"8kHs_rmwqaRUk1AQLGX65g4AEkWUDapWVsMFUQpN9Ek="


def _calculate_sha256(filepath):
    """Calculates the SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class LicenseAdminApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestore Licenze (Admin)")
        self.root.geometry("600x480")
        self.root.resizable(False, False)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10, "bold"))

        ttk.Label(root, text="Generatore Licenza Cliente", font=("Segoe UI", 14, "bold")).pack(pady=15)

        # Container
        frm = ttk.LabelFrame(root, text="Dati Cliente", padding=20)
        frm.pack(fill="both", expand=True, padx=20, pady=5)

        # Disk Serial
        ttk.Label(frm, text="Seriale Disco Cliente (Hardware ID):").pack(anchor="w")
        self.ent_disk = ttk.Entry(frm, width=60)
        self.ent_disk.pack(pady=5)
        ttk.Button(frm, text="Incolla dagli appunti", command=self.paste_disk).pack(anchor="e", pady=5)

        # Nome Cliente (solo per organizzazione cartelle)
        ttk.Label(frm, text="Nome Riferimento Cliente (es. AziendaX):").pack(anchor="w", pady=(10, 0))
        self.ent_name = ttk.Entry(frm, width=60)
        self.ent_name.pack(pady=5)

        # Scadenza
        ttk.Label(frm, text="Data Scadenza (YYYY-MM-DD):").pack(anchor="w", pady=(15, 0))
        self.ent_date = ttk.Entry(frm, width=20)
        self.ent_date.pack(anchor="w", pady=5)

        # Default 365 giorni
        scadenza_default = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
        self.ent_date.insert(0, scadenza_default)

        # Bottone Genera
        self.btn_gen = ttk.Button(root, text="GENERA FILE LICENZA", command=self.generate)
        self.btn_gen.pack(fill="x", padx=20, pady=20, ipady=10)

    def paste_disk(self):
        try:
            self.ent_disk.delete(0, tk.END)
            self.ent_disk.insert(0, self.root.clipboard_get().strip())
        except Exception:
            pass

    def generate(self):
        disk_serial = self.ent_disk.get().strip()
        client_name = self.ent_name.get().strip()
        expiry = self.ent_date.get().strip()

        if not disk_serial:
            messagebox.showerror("Errore", "Il Seriale del Disco è obbligatorio!")
            return

        if not client_name:
            client_name = disk_serial  # Fallback se non c'è nome

        # Pulisci il nome cliente per usarlo come cartella
        folder_name = "".join([c for c in client_name if c.isalnum() or c in (" ", "_", "-")]).strip()

        # Cartella di output organizzata
        base_output = os.path.dirname(os.path.abspath(__file__))
        client_dir = os.path.join(base_output, folder_name)
        target_dir = os.path.join(client_dir, "Licenza")

        # Comando PyArmor (genera in cartella temporanea 'dist' locale allo script)
        cmd = [sys.executable, "-m", "pyarmor.cli", "gen", "key", "-e", expiry, "-b", disk_serial]

        try:
            # Esegui comando
            res = subprocess.run(cmd, capture_output=True, text=True)

            if res.returncode == 0:
                # PyArmor di default mette l'output in "dist/pyarmor.rkey" relativo alla CWD
                src_default = os.path.join("dist", "pyarmor.rkey")

                if os.path.exists(src_default):
                    # Crea cartella destinazione
                    if os.path.exists(target_dir):
                        shutil.rmtree(target_dir)
                    os.makedirs(target_dir)

                    # 1. Sposta il file di licenza
                    dst_lic = os.path.join(target_dir, "pyarmor.rkey")
                    shutil.move(src_default, dst_lic)

                    # 1.1 Rimuovi cartella dist temporanea
                    if os.path.exists("dist"):
                        shutil.rmtree("dist", ignore_errors=True)

                    # 2. GENERAZIONE FILE CRITTOGRAFATO
                    # Format dates to DD/MM/YYYY
                    try:
                        expiry_obj = date.fromisoformat(expiry)
                        expiry_str = expiry_obj.strftime("%d/%m/%Y")
                    except ValueError:
                        expiry_str = expiry  # Fallback if invalid format

                    gen_date_str = date.today().strftime("%d/%m/%Y")

                    # NOTE: admin tool logic previously stripped '.' but let's just keep what user entered but strip whitespace.
                    # Ideally the user should paste exactly what the main app showed them.
                    clean_disk_serial = disk_serial

                    payload = {
                        "Hardware ID": clean_disk_serial,
                        "Scadenza Licenza": expiry_str,
                        "Generato il": gen_date_str,
                        "Cliente": client_name,
                    }

                    json_payload = json.dumps(payload).encode("utf-8")
                    cipher = Fernet(LICENSE_SECRET_KEY)
                    encrypted_data = cipher.encrypt(json_payload)

                    config_path = os.path.join(target_dir, "config.dat")
                    with open(config_path, "wb") as f:
                        f.write(encrypted_data)

                    # 3. GENERAZIONE MANIFEST CON CHECKSUM
                    manifest = {
                        "pyarmor.rkey": _calculate_sha256(dst_lic),
                        "config.dat": _calculate_sha256(config_path),
                    }
                    manifest_path = os.path.join(target_dir, "manifest.json")
                    with open(manifest_path, "w") as f:
                        json.dump(manifest, f, indent=4)

                    # Istruzioni per l'utente
                    msg = (
                        f"Licenza GENERATA con successo!\n\n"
                        f"Cliente: {client_name}\n"
                        f"Hardware ID: {disk_serial}\n\n"
                        f"FILE SALVATI IN:\n{target_dir}\n"
                        f"(Troverai 'pyarmor.rkey', 'config.dat' e 'manifest.json')"
                    )

                    messagebox.showinfo("Successo", msg)

                    # Apre la cartella automaticamente
                    if os.name == "nt":
                        os.startfile(target_dir)
                else:
                    messagebox.showerror("Errore", f"File generato non trovato in {src_default}")
            else:
                messagebox.showerror("Errore PyArmor", f"Output errore:\n{res.stderr}")

        except Exception as e:
            messagebox.showerror("Eccezione", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    LicenseAdminApp(root)
    root.mainloop()
