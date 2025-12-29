import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
import sys

# Aggiungi il percorso src per permettere l'import di main
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
import main

class TestSessionManagement(unittest.TestCase):

    def setUp(self):
        """Prepara un ambiente di test pulito."""
        self.dummy_tasks = [
            {'unknown_path': 'C:/temp/file1_.pdf', 'source_path': 'C:/temp/source1.pdf', 'siblings': []},
            {'unknown_path': 'C:/temp/file2_.pdf', 'source_path': 'C:/temp/source2.pdf', 'siblings': []}
        ]
        self.dummy_session_content = json.dumps(self.dummy_tasks)

    def _get_mock_app(self):
        """Crea un'istanza 'vuota' di MainApp con gli attributi UI necessari mockati."""
        app = main.MainApp.__new__(main.MainApp)
        app.root = MagicMock()
        app.restore_btn = MagicMock()
        return app

    @patch('main.UnknownFilesReviewDialog')
    @patch('main.messagebox.askyesno', return_value=True)
    def test_check_for_restore_when_user_accepts(self, mock_askyesno, mock_review_dialog):
        """
        Testa che _check_for_restore chiami il popup e poi il dialogo di ripristino se l'utente accetta.
        """
        app = self._get_mock_app()
        
        # Simula un file di sessione valido
        with patch('main.os.path.exists', return_value=True), \
             patch('main.os.path.getsize', return_value=128), \
             patch('builtins.open', mock_open(read_data=self.dummy_session_content)):
            
            # Azione: esegui il controllo
            app._check_for_restore()

            # Asserzioni
            app.restore_btn.config.assert_called_with(state='normal')
            mock_askyesno.assert_called_once()
            mock_review_dialog.assert_called_once()

    @patch('main.UnknownFilesReviewDialog')
    @patch('main.messagebox.askyesno', return_value=False)
    def test_check_for_restore_when_user_declines(self, mock_askyesno, mock_review_dialog):
        """
        Testa che il ripristino non avvenga se l'utente risponde 'No'.
        """
        app = self._get_mock_app()
        
        with patch('main.os.path.exists', return_value=True), \
             patch('main.os.path.getsize', return_value=128):
            
            app._check_for_restore()

            app.restore_btn.config.assert_called_with(state='normal')
            mock_askyesno.assert_called_once()
            mock_review_dialog.assert_not_called()

    @patch('main.os.remove')
    def test_clear_session_deletes_file(self, mock_remove):
        """
        Testa che _clear_session chiami os.remove e aggiorni correttamente lo stato del bottone.
        """
        app = self._get_mock_app()
        
        # Simula che os.path.exists restituisca True la prima volta, e False la seconda
        # (dopo la presunta cancellazione).
        with patch('main.os.path.exists', side_effect=[True, False]), \
             patch('main.os.path.getsize'): # getsize non verrà chiamato sulla seconda verifica
            
            app._clear_session()
            
            mock_remove.assert_called_once_with(main.SESSION_FILE)
            # L'update DEVE essere chiamato dopo la rimozione
            app.restore_btn.config.assert_called_with(state='disabled')

    def test_button_disabled_if_no_session_file(self):
        """
        Testa che il bottone di ripristino sia disabilitato se non c'è un file di sessione.
        """
        app = self._get_mock_app()
        
        with patch('main.os.path.exists', return_value=False):
            app._update_restore_button_state()
            app.restore_btn.config.assert_called_with(state='disabled')

if __name__ == "__main__":
    unittest.main()
