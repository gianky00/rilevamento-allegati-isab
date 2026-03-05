import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

import main


@pytest.fixture
def mock_dependencies():
    patchers = [
        patch("core.app_controller.license_validator.get_license_info", return_value={}),
        patch("core.app_controller.license_validator.get_hardware_id", return_value="HWID"),
        patch("core.app_controller.license_validator.verify_license", return_value=(True, "OK")),
        patch("core.app_controller.config_manager.load_config", return_value={"classification_rules": []}),
        patch("core.app_controller.config_manager.save_config"),
        patch("core.app_controller.app_updater"),
        patch("core.app_controller.SessionManager.has_session", return_value=False),
        patch("core.notification_manager.NotificationManager"),
        patch("pathlib.Path.exists", return_value=False),
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
    if hasattr(app, "controller") and hasattr(app.controller, "_log_timer"):
        app.controller._log_timer.stop()
    app._update_timer.stop()
    app._progress_timer.stop()
    app._spinner_timer.stop()
    app._clock_timer.stop()


def test_odc_validation(main_app):
    main_app.odc_entry.setText("ABC1234")
    with patch("main.QMessageBox.warning") as mock_warn:
        main_app.controller.pdf_files = ["test.pdf"]
        with patch.object(main_app.controller, "start_processing") as mock_start:
            main_app._start_processing()
            mock_warn.assert_not_called()
            mock_start.assert_called_once()


def test_odc_validation_empty(main_app):
    main_app.odc_entry.setText("")
    with patch("main.QMessageBox.warning") as mock_warn:
        main_app.pdf_files = ["test.pdf"]
        main_app._start_processing()
        mock_warn.assert_called_once()


def test_no_pdf_selected(main_app):
    main_app.odc_entry.setText("5400")
    main_app.pdf_files = []
    with patch("main.QMessageBox.warning") as mock_warn:
        main_app._start_processing()
        mock_warn.assert_called_once()


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
        with patch("core.file_service.Path.exists", return_value=True):
            with patch("core.file_service.Path.is_file", return_value=True):
                main_app._on_drop(["path/to/file.pdf"])
                assert len(main_app.controller.pdf_files) == 1
                mock_start.assert_called_once()


def test_check_for_updates_signal(main_app):
    # Usiamo Path.exists e Path.unlink nel controller
    with patch("core.app_controller.Path.exists", return_value=True), \
         patch("core.app_controller.Path.unlink") as mock_unlink, \
         patch.object(main_app.controller, 'load_settings') as mock_load:
         
         main_app._check_for_updates()
         mock_unlink.assert_called_once()
         mock_load.assert_called_once()


def test_unknown_files_signal(main_app):
    with patch.object(main_app, "_show_unknown_dialog") as mock_dialog:
        main_app.controller.unknown_files_found.emit(["a.pdf"], "123")
        mock_dialog.assert_called_once_with(["a.pdf"], "123")


def test_unknown_dialog_empty_files(main_app):
    with patch("main.UnknownFilesReviewDialog") as mock_dialog_class:
        main_app._show_unknown_dialog([], "ODC")
        mock_dialog_class.assert_not_called()
