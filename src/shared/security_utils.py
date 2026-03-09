"""
Intelleo PDF Splitter - Security Utilities (SyncroJob V9.0)
Funzioni di sanitizzazione e sicurezza condivise.
"""

import re


def sanitize_html(html_string: str) -> str:
    """
    Rimuove tag pericolosi (script, iframe, on*) per prevenire Injection (Pillar 4).
    Implementa un filtro Regex per blindare l'output HTML.
    """
    if not html_string:
        return ""

    # 1. Rimuove blocchi <script>...</script>
    s = re.sub(r"<script.*?>.*?</script>", "", html_string, flags=re.DOTALL | re.IGNORECASE)

    # 2. Rimuove blocchi <iframe>...</iframe>
    s = re.sub(r"<iframe.*?>.*?</iframe>", "", s, flags=re.DOTALL | re.IGNORECASE)

    # 3. Rimuove attributi on* (es. onclick, onload, onmouseover, etc.)
    # Gestisce sia apici doppi che singoli
    s = re.sub(r"\son\w+\s*=\s*\".*?\"", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\son\w+\s*=\s*'.*?'", "", s, flags=re.IGNORECASE)

    # 4. Rimuove tag <script> isolati (se presenti senza chiusura corretta)
    s = re.sub(r"<script.*?>", "", s, flags=re.IGNORECASE)

    return s
