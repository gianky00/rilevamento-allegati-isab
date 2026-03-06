# hook-tkinterdnd2.py
# Hook per PyInstaller per includere correttamente i file necessari per tkinterdnd2.

from PyInstaller.utils.hooks import collect_data_files

# La libreria tkinterdnd2 ha i suoi file di supporto (Tcl) in una sottocartella
# che PyInstaller non sempre trova in automatico. Questo hook forza l'inclusione.
datas = collect_data_files("tkinterdnd2")

print(f"Hook per tkinterdnd2: Inclusi {len(datas)} file di dati.")
for data_file, destination in datas:
    print(f"  - {data_file} -> {destination}")
