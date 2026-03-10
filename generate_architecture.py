import os
import sys
from diagrams import Diagram, Cluster, Edge
from diagrams.onprem.client import User
from diagrams.programming.language import Python
from diagrams.generic.storage import Storage
from diagrams.generic.device import Tablet
from diagrams.custom import Custom

# Aggiunta di Graphviz al PATH per Windows
graphviz_bin = r"C:\Program Files\Graphviz\bin"
if os.path.exists(graphviz_bin):
    os.environ["PATH"] += os.pathsep + graphviz_bin

# Icone più specifiche o alternative per evitare sovrapposizioni visive
from diagrams.onprem.compute import Server
from diagrams.onprem.security import Vault as SecurityVault
from diagrams.onprem.aggregator import Fluentd

# Configurazione attributi del grafico per Alta Fedeltà
graph_attr = {
    "fontsize": "32", # Aumentato per legibilità
    "bgcolor": "white",
    "fontname": "Verdana Bold",
    "pad": "2.0",
    "nodesep": "1.8",
    "ranksep": "2.2",
    "dpi": "300",
    "splines": "ortho", # Linee ortogonali per ordine
    "concentrate": "true"
}

# Assicuriamoci che la directory di output esista
output_dir = "docs/assets"
os.makedirs(output_dir, exist_ok=True)

try:
    with Diagram("Rilevamento Allegati ISAB - Architettura di Sistema", 
                 filename=os.path.join(output_dir, "architecture"),
                 show=False, 
                 direction="TB",
                 graph_attr=graph_attr):

        user = User("Utente finale\n(Drag & Drop)")

        with Cluster("BOOTSTRAP & SECURITY"):
            launcher = Python("App Launcher")
            lic_check = SecurityVault("License Validator\n(HWID Lock)")
            config = Python("Config Manager")
            
            launcher >> Edge(label="1. Verify", color="red", style="dashed") >> lic_check
            launcher >> Edge(label="2. Load Settings", color="blue") >> config

        with Cluster("PRESENTATION LAYER (PySide6)"):
            main_ui = Tablet("Main App UI\n(Window)")
            dashboard = Server("Dashboard Tab")
            config_tab = Server("Config Tab")
            ui_factory = Server("UI Factory\n(Custom Widgets)")
            
            launcher >> Edge(label="3. Initialize", color="darkgreen") >> main_ui
            main_ui >> Edge(color="gray50") >> dashboard
            main_ui >> Edge(color="gray50") >> config_tab
            main_ui >> Edge(color="gray50") >> ui_factory

        with Cluster("CONTROLLER LAYER"):
            controller = Fluentd("App Controller\n(Mediator)")
            worker = Python("Processing Worker\n(QThread)")
            
            user >> Edge(label="Drop PDF", color="darkblue", style="bold") >> main_ui
            main_ui >> Edge(label="4. Submit", color="blue") >> controller
            controller >> Edge(label="5. Spawn", color="purple") >> worker

        with Cluster("CORE PROCESSING & INTELLIGENCE"):
            proc_service = Python("PDF Processor\n(Orchestrator)")
            
            with Cluster("Analysis Engine"):
                analysis = Python("Analysis Service\n(Classification)")
                ocr = Python("OCR Engine")
                roi = Python("ROI Manager")
                
            with Cluster("Output Engine"):
                splitter = Python("PDF Splitter\n(PyMuPDF)")
                archive = Storage("Archive Service\n(File System)")
            
            worker >> Edge(color="darkgreen") >> proc_service
            proc_service >> analysis
            analysis >> Edge(label="OCR", color="orange") >> ocr
            analysis >> Edge(color="gray") >> roi
            
            proc_service >> Edge(label="Split", color="darkblue") >> splitter
            splitter >> Edge(label="Save", color="darkblue") >> archive

        # Feedback flussi
        worker >> Edge(label="Logs/Signals", color="gray", style="dotted") >> main_ui

        # Dipendenze Esterne
        icon_id = os.path.abspath("assets/id.svg")
        tesseract_ext = Custom("Tesseract OCR\n(System Binary)", icon_id)
        ocr >> Edge(label="CLI Call", color="red", style="dashed") >> tesseract_ext

    print(f"Diagramma ottimizzato generato con successo in {output_dir}/architecture.png")
except Exception as e:
    print(f"Errore durante la generazione: {e}")
    sys.exit(1)
