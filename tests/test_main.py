import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import main


@pytest.fixture
def mock_dependencies():
    patchers = [
        patch("main.license_validator.get_license_info", return_value={}),
        patch("os.path.exists", return_value=False),
        patch("main.license_validator.verify_license", return_value=(True, "OK")),
        patch("main.config_manager.load_config", return_value={"classification_rules": []}),
        patch("main.app_updater"),
        patch("main.notification_manager.NotificationManager", side_effect=Exception("Mocked out")),
    ]
    for p in patchers:
        p.start()
    yield
    for p in reversed(patchers):
        p.stop()


@pytest.fixture
def main_app(qtbot, mock_dependencies):
    app = main.MainApp()
    yield app
    app._log_timer.stop()
    app._update_timer.stop()
    app._progress_timer.stop()
    app._spinner_timer.stop()
    app._clock_timer.stop()


def test_odc_validation(main_app):
    main_app.odc_entry.setText("ABC1234")
    with patch("main.QMessageBox.critical") as mock_error:
        main_app.pdf_files = ["test.pdf"]
        with patch("threading.Thread") as mock_thread:
            main_app._start_processing()
            mock_error.assert_not_called()
            mock_thread.assert_called_once()


def test_odc_validation_empty(main_app):
    main_app.odc_entry.setText("")
    with patch("main.QMessageBox.critical") as mock_error:
        main_app.pdf_files = ["test.pdf"]
        main_app._start_processing()
        mock_error.assert_called_once()


def test_no_pdf_selected(main_app):
    main_app.odc_entry.setText("5400")
    main_app.pdf_files = []
    with patch("main.QMessageBox.critical") as mock_error:
        main_app._start_processing()
        mock_error.assert_called_once()


def test_add_log_message_progress(main_app):
    with patch("main.datetime") as mock_datetime:
        mock_now = MagicMock()
        mock_now.strftime.return_value = "12:00:00"
        mock_datetime.now.return_value = mock_now

        main_app.log_area.clear()
        main_app._add_log_message("Elaborazione test", "PROGRESS")

        content = main_app.log_area.toHtml()
        assert "12:00:00" in content
        assert "Elaborazione test" in content


def test_on_drop_single_file(main_app):
    with patch.object(main_app, "_start_processing") as mock_start:
        main_app._on_drop(["path/to/file.pdf"])
        assert len(main_app.pdf_files) == 1
        mock_start.assert_called_once()


def test_check_for_updates_signal(main_app):
    with patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove, patch.object(main_app, 'load_settings') as mock_load:
         main_app._check_for_updates()
         mock_remove.assert_called_with(main.SIGNAL_FILE)
         mock_load.assert_called_once()


def test_process_log_queue_dialog(main_app):
    main_app.log_queue.put({"action": "show_unknown_dialog", "files": ["a.pdf"], "odc": "123"})
    main_app._process_log_queue()
    assert main_app._pending_completion_data is not None
    assert main_app._pending_completion_data["action"] == "show_unknown_dialog"


def test_unknown_dialog_empty_files(main_app):
    with patch("main.UnknownFilesReviewDialog") as mock_dialog_class:
        main_app._show_unknown_dialog([], "ODC")
        mock_dialog_class.assert_not_called()
