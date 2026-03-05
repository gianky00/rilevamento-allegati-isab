import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import roi_utility


@pytest.fixture
def mock_dependencies():
    patchers = [
        patch("core.roi_manager.config_manager.load_config", return_value={"classification_rules": []}),
        patch("core.roi_manager.config_manager.save_config"),
        patch("core.pdf_manager.fitz"),
        patch("roi_utility.QMessageBox"),
        patch("roi_utility.QFileDialog"),
    ]
    for p in patchers:
        p.start()
    yield
    for p in reversed(patchers):
        p.stop()


@pytest.fixture
def roi_app(qtbot, mock_dependencies):
    app = roi_utility.ROIDrawingApp(parent=None)
    qtbot.addWidget(app)
    yield app


def test_init(roi_app):
    assert roi_app is not None
    assert roi_app.windowTitle() == "🎯 Intelleo - Utility Gestione ROI"


def test_has_no_initial_pdf(roi_app):
    assert roi_app.controller.pdf_manager.doc is None


def test_prev_next_page(roi_app):
    roi_app.controller.pdf_manager.doc = MagicMock()
    roi_app.controller.pdf_manager.doc.__len__.return_value = 5
    roi_app.controller.current_page_index = 2

    with patch.object(roi_app.controller, "render_current_page") as mock_render:
        roi_app.prev_page()
        assert roi_app.controller.current_page_index == 1
        mock_render.assert_called_once()

        mock_render.reset_mock()
        roi_app.next_page()
        assert roi_app.controller.current_page_index == 2 # 1+1
        mock_render.assert_called_once()


def test_save_and_refresh(roi_app):
    with patch("core.roi_controller.Path.write_text") as mock_write:
        roi_app.save_and_refresh()
        from core.roi_manager import config_manager

        config_manager.save_config.assert_called()
        mock_write.assert_called_with("update", encoding="utf-8")
