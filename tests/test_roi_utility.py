import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))
import roi_utility


@pytest.fixture
def mock_dependencies():
    patchers = [
        patch("roi_utility.config_manager.load_config", return_value={"classification_rules": []}),
        patch("roi_utility.config_manager.save_config"),
        patch("roi_utility.fitz"),
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
    assert roi_app.pdf_doc is None


def test_prev_next_page(roi_app):
    roi_app.pdf_doc = MagicMock()
    roi_app.pdf_doc.page_count = 5
    roi_app.current_page_index = 2

    with patch.object(roi_app, "render_page") as mock_render:
        roi_app.prev_page()
        mock_render.assert_called_once_with(1)

        mock_render.reset_mock()
        roi_app.next_page()
        mock_render.assert_called_once_with(3)


def test_save_and_refresh(roi_app):
    with patch("builtins.open", new_callable=MagicMock) as mock_open:
        roi_app.save_and_refresh()
        from roi_utility import config_manager

        config_manager.save_config.assert_called_with(roi_app.config)
        mock_open.assert_called_with(roi_utility.SIGNAL_FILE, "w")
