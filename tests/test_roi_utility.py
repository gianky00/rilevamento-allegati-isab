import unittest
from unittest.mock import patch, MagicMock, ANY
import tkinter as tk
import roi_utility

class MockVar:
    def __init__(self, value=None):
        self._value = value
    def set(self, value):
        self._value = value
    def get(self):
        return self._value

class TestROIUtility(unittest.TestCase):

    def setUp(self):
        # Patch Tkinter and dependencies
        self.patches = {}
        patch_list = [
            "tkinter.Tk",
            "tkinter.Toplevel",
            "tkinter.Canvas",
            "tkinter.ttk.Frame",
            "tkinter.ttk.Button",
            "tkinter.ttk.Label",
            "tkinter.ttk.Checkbutton",
            "tkinter.ttk.Scrollbar",
            "tkinter.ttk.Combobox",
            "roi_utility.config_manager.load_config",
            "roi_utility.config_manager.save_config",
            "roi_utility.fitz" # Patch whole module
        ]

        self.patchers = []
        for target in patch_list:
            p = patch(target)
            self.patchers.append(p)
            self.patches[target] = p.start()

        # Side effect mocks separately
        self.patchers.append(patch("tkinter.BooleanVar", side_effect=MockVar))
        self.patchers[-1].start()
        self.patchers.append(patch("tkinter.StringVar", side_effect=MockVar))
        self.patchers[-1].start()

        self.patches["roi_utility.config_manager.load_config"].return_value = {"classification_rules": []}

        self.mock_root = MagicMock()
        self.app = roi_utility.ROIDrawingApp(self.mock_root)

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_init(self):
        self.assertIsNotNone(self.app)
        self.assertEqual(self.app.root.title.call_args[0][0], "Utility di Gestione ROI")

    def test_draw_existing_rois(self):
        config = {
            "classification_rules": [
                {
                    "category_name": "TestCat",
                    "color": "red",
                    "rois": [[10, 10, 100, 100]]
                }
            ]
        }
        with patch("roi_utility.config_manager.load_config", return_value=config):
            self.app.draw_existing_rois()
            self.app.canvas.create_rectangle.assert_called()
            self.app.canvas.create_text.assert_called()

    def test_save_and_refresh(self):
        with patch("builtins.open", new_callable=MagicMock) as mock_open:
            self.app.save_and_refresh()
            self.patches["roi_utility.config_manager.save_config"].assert_called_with(self.app.config)
            mock_open.assert_called_with(roi_utility.SIGNAL_FILE, "w")

    def test_prev_next_page(self):
        self.app.pdf_doc = MagicMock()
        self.app.pdf_doc.page_count = 5
        self.app.current_page_index = 2

        with patch.object(self.app, 'render_page') as mock_render:
            self.app.prev_page()
            mock_render.assert_called_with(1)

            self.app.next_page()
            mock_render.assert_called_with(3)

    def test_prompt_and_save_roi(self):
        self.app.prompt_and_save_roi([0,0,10,10])
        self.patches['tkinter.Toplevel'].assert_called()

if __name__ == "__main__":
    unittest.main()
