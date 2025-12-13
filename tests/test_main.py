import unittest
from unittest.mock import patch, MagicMock, ANY
import tkinter as tk
import main
import queue
import os
import sys

# Helper to mock tkinter variables since we have no root
class MockVar:
    def __init__(self, value=None):
        self._value = value
        self._trace_cb = None
    def set(self, value):
        self._value = value
        if self._trace_cb:
            self._trace_cb()
    def get(self):
        return self._value
    def trace(self, mode, callback):
        self._trace_cb = callback # Simplified logic

class TestMainLogic(unittest.TestCase):

    def setUp(self):
        # Start patches
        self.patchers = [
            patch("main.TkinterDnD.Tk"),
            patch("tkinter.StringVar", side_effect=MockVar),
            patch("tkinter.IntVar", side_effect=MockVar),
            patch("tkinter.BooleanVar", side_effect=MockVar),
            patch("tkinter.ttk.Notebook"),
            patch("tkinter.ttk.Frame"),
            patch("tkinter.ttk.LabelFrame"),
            patch("tkinter.ttk.Label"),
            patch("tkinter.ttk.Entry"),
            patch("tkinter.ttk.Button"),
            patch("tkinter.scrolledtext.ScrolledText"),
            patch("tkinter.ttk.Treeview"),
            patch("tkinter.ttk.Scrollbar"),
            patch("tkinter.Text"),
            patch("tkinter.ttk.Separator"),
            patch("main.license_validator.get_license_info", return_value={}),
            patch("os.path.exists", return_value=False),
            patch("license_validator.verify_license", return_value=(True, "OK")),
            patch("main.MainApp.load_settings"),
            patch("main.UnknownFilesReviewDialog")
        ]

        for p in self.patchers:
            p.start()

        # Create a Mock root
        self.mock_root = MagicMock()

        self.app = main.MainApp(self.mock_root)
        if not hasattr(self.app, 'odc_var'):
             self.app.odc_var = MockVar("5400")

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()

    def test_odc_validation(self):
        self.app.odc_var.set("ABC1234")
        with patch("tkinter.messagebox.showerror") as mock_error:
            self.app.pdf_files = ["test.pdf"]
            with patch("threading.Thread") as mock_thread:
                self.app.start_processing()
                mock_error.assert_not_called()
                mock_thread.assert_called_once()

    def test_odc_validation_empty(self):
        self.app.odc_var.set("")
        with patch("tkinter.messagebox.showerror") as mock_error:
            self.app.pdf_files = ["test.pdf"]
            self.app.start_processing()
            mock_error.assert_called_once()

    def test_no_pdf_selected(self):
        self.app.odc_var.set("5400")
        self.app.pdf_files = []
        with patch("tkinter.messagebox.showerror") as mock_error:
            self.app.start_processing()
            mock_error.assert_called()

    def test_add_log_message_progress(self):
        self.app.log_area = MagicMock()
        self.app.log_area.get.return_value = "Elaborazione pagina 1/5..."
        self.app.add_log_message("Elaborazione pagina 2/5...", "PROGRESS")
        self.app.log_area.delete.assert_called_with(ANY, "end-1c")
        self.app.log_area.insert.assert_called_with(tk.END, "Elaborazione pagina 2/5...\n", "PROGRESS")

    def test_on_drop_single_file(self):
        event = MagicMock()
        event.data = "path/to/file.pdf"
        with patch("os.path.exists", return_value=True), patch("os.path.isdir", return_value=False):
             with patch.object(self.app, 'start_processing') as mock_start:
                 self.app.on_drop(event)
                 self.assertEqual(len(self.app.pdf_files), 1)
                 mock_start.assert_called_once()

    def test_check_for_updates_signal(self):
        with patch("os.path.exists", return_value=True), patch("os.remove") as mock_remove:
            with patch.object(self.app, 'load_settings') as mock_load:
                 self.app.check_for_updates()
                 mock_remove.assert_called_with(main.SIGNAL_FILE)
                 mock_load.assert_called_once()

    def test_process_log_queue_dialog(self):
        self.app.log_queue.put({'action': 'show_unknown_dialog', 'files': ['a.pdf'], 'odc': '123'})
        with patch.object(self.app, 'show_unknown_dialog') as mock_show:
            self.app.process_log_queue()
            mock_show.assert_called_once()

    def test_processing_worker(self):
        files = ["test.pdf"]
        odc = "123"
        config = {}
        with patch("pdf_processor.process_pdf") as mock_process:
            mock_process.return_value = (True, "OK", [{'category': 'sconosciuto', 'path': 'out.pdf'}], 'orig/test.pdf')
            self.app.processing_worker(files, odc, config)
            item = self.app.log_queue.get()
            self.assertIsInstance(item, tuple)
            while not self.app.log_queue.empty():
                item = self.app.log_queue.get()
                if isinstance(item, dict) and item.get('action') == 'show_unknown_dialog':
                    # Verify structure of review tasks
                    self.assertEqual(len(item['files']), 1)
                    task = item['files'][0]
                    self.assertEqual(task['unknown_path'], 'out.pdf')
                    self.assertEqual(task['source_path'], 'orig/test.pdf')
                    return
            self.fail("Did not find show_unknown_dialog action in queue")

    def test_main_app_no_dnd(self):
        mock_root = MagicMock()
        del mock_root.drop_target_register
        app = main.MainApp(mock_root)
        with self.assertRaises(AttributeError):
             mock_root.drop_target_register(ANY)

    # --- New Tests for UnknownFilesReviewDialog Logic ---

    def test_unknown_dialog_empty_files(self):
        with patch("main.UnknownFilesReviewDialog") as mock_dialog_class:
            self.app.show_unknown_dialog([], "ODC")
            mock_dialog_class.assert_not_called()

if __name__ == "__main__":
    unittest.main()
