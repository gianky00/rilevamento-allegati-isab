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
        app.controller = MagicMock()
        app._is_initial_session_check = False
        return app

    # Patch the correct PySide6 method
    @patch("main.QMessageBox.question")
    def test_check_for_restore_when_user_accepts(self, mock_question):
        """Testa che _update_restore_button_state chiami il ripristino se l'utente accetta."""
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.Yes
        app = self._get_mock_app()
        app._is_initial_session_check = True

        with patch.object(app, "_restore_session") as mock_restore:
            app._update_restore_button_state(True)
            app.restore_btn.setEnabled.assert_called_with(True)
            mock_question.assert_called_once()
            mock_restore.assert_called_once()

    @patch("main.QMessageBox.question")
    def test_check_for_restore_when_user_declines(self, mock_question):
        """Testa che il ripristino non avvenga se l'utente risponde 'No'."""
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.No
        app = self._get_mock_app()
        app._is_initial_session_check = True

        with patch.object(app, "_restore_session") as mock_restore_local:
            app._update_restore_button_state(True)
            app.restore_btn.setEnabled.assert_called_with(True)
            mock_question.assert_called_once()
            mock_restore_local.assert_not_called()

    def test_clear_session_deletes_file(self):
        """Testa che _clear_session chiami il controller."""
        app = self._get_mock_app()
        app._clear_session()
        app.controller.clear_session.assert_called_once()

    def test_button_disabled_if_no_session_file(self):
        """Testa che il bottone di ripristino sia disabilitato se non c'è un file."""
        app = self._get_mock_app()
        app._update_restore_button_state(False)
        app.restore_btn.setEnabled.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
