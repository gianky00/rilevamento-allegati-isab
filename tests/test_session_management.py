import json
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import main


class TestSessionManagement(unittest.TestCase):
    def setUp(self):
        """Prepara un ambiente di test pulito."""
        self.dummy_tasks = [
            {"unknown_path": "C:/temp/file1_.pdf", "source_path": "C:/temp/source1.pdf", "siblings": []},
            {"unknown_path": "C:/temp/file2_.pdf", "source_path": "C:/temp/source2.pdf", "siblings": []},
        ]
        self.dummy_session_content = json.dumps(self.dummy_tasks)

    def _get_mock_app(self):
        """Crea un'istanza 'vuota' di MainApp con gli attributi UI necessari mockati."""
        app = main.MainApp.__new__(main.MainApp)
        app.restore_btn = MagicMock()
        app.odc_entry = MagicMock()
        app.controller = MagicMock()
        return app

    def test_restore_session_calls_controller(self):
        """Testa che _restore_session carichi i dati dal controller e aggiorni la UI."""
        app = self._get_mock_app()
        dummy_data = (self.dummy_tasks, "ODC123")
        app.controller.restore_session.return_value = dummy_data
        
        with patch.object(app, "on_unknown_files_found") as mock_on_unknown:
            app._restore_session()
            app.controller.restore_session.assert_called_once()
            app.odc_entry.setText.assert_called_with("ODC123")
            mock_on_unknown.assert_called_with(self.dummy_tasks, "ODC123")

    def test_button_disabled_if_no_session_file(self):
        """Testa che il bottone di ripristino sia disabilitato se non c'è un file."""
        app = self._get_mock_app()
        app._update_restore_button_state(False)
        app.restore_btn.setEnabled.assert_called_with(False)

    def test_button_enabled_if_session_file_exists(self):
        """Testa che il bottone di ripristino sia abilitato se c'è un file."""
        app = self._get_mock_app()
        app._update_restore_button_state(True)
        app.restore_btn.setEnabled.assert_called_with(True)


if __name__ == "__main__":
    unittest.main()
