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
        return app

    # Patch the correct PySide6 method
    @patch("main.QMessageBox.question")
    @patch("main.MainApp._restore_session")
    def test_check_for_restore_when_user_accepts(self, mock_restore, mock_question):
        """Testa che _check_for_restore chiami il ripristino se l'utente accetta."""
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.Yes
        app = self._get_mock_app()

        with patch("main.os.path.exists", return_value=True):
            app._check_for_restore()
            app.restore_btn.setEnabled.assert_called_with(True)
            mock_question.assert_called_once()
            mock_restore.assert_called_once()

    @patch("main.QMessageBox.question")
    @patch("main.MainApp._restore_session")
    def test_check_for_restore_when_user_declines(self, mock_restore, mock_question):
        """Testa che il ripristino non avvenga se l'utente risponde 'No'."""
        from PySide6.QtWidgets import QMessageBox

        mock_question.return_value = QMessageBox.StandardButton.No
        app = self._get_mock_app()

        with patch("main.os.path.exists", return_value=True):
            app._check_for_restore()
            app.restore_btn.setEnabled.assert_called_with(True)
            mock_question.assert_called_once()
            mock_restore.assert_not_called()

    @patch("main.os.remove")
    def test_clear_session_deletes_file(self, mock_remove):
        """Testa che _clear_session chiami os.remove e aggiorni lo stato del bottone."""
        app = self._get_mock_app()

        with patch("main.os.path.exists", side_effect=[True, False]):
            app._clear_session()
            mock_remove.assert_called_once_with(main.SESSION_FILE)
            app.restore_btn.setEnabled.assert_called_with(False)

    def test_button_disabled_if_no_session_file(self):
        """Testa che il bottone di ripristino sia disabilitato se non c'è un file."""
        app = self._get_mock_app()
        with patch("main.os.path.exists", return_value=False):
            app._update_restore_button_state()
            app.restore_btn.setEnabled.assert_called_with(False)


if __name__ == "__main__":
    unittest.main()
