import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QFile, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QMessageBox, QPushButton, QTableView

from FileSearchQt import FileSearchWindow, ResultsModel


class DeleteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.window = FileSearchWindow.__new__(FileSearchWindow)
        QMainWindow.__init__(self.window)
        w = self.window
        w.language = 'zh'
        w.is_searching = False
        w.search_generation = 1
        w._live_timer = QTimer(w)
        w.results_model = ResultsModel(w)
        w.table = QTableView(w)
        w.table.setModel(w.results_model)
        w.result_label = QLabel(w)
        w.status_label = QLabel(w)
        w.search_button = QPushButton(w)
        self.addCleanup(w.deleteLater)

    def populate(self, paths):
        self.window.results_model.append_rows([
            (p.name, str(p.parent), str(p), '', 0, '', p.is_dir()) for p in paths
        ])

    def run_delete(self, paths, fail=(), answer=QMessageBox.Yes):
        # Simulate the native trash operation inside the temporary test directory.
        trash = self.root / '.test-trash'
        trash.mkdir(exist_ok=True)

        def move(item):
            path = Path(item.fileName())
            if path in fail:
                return False
            path.rename(trash / path.name)
            return True

        class TestFile(QFile):
            def moveToTrash(self):
                return move(self)

        with patch.object(self.window, '_selected_paths', return_value=list(map(str, paths))), \
                patch.object(QMessageBox, 'exec', return_value=answer), \
                patch('FileSearchQt.QFile', side_effect=TestFile) as operation:
            self.window.delete_selected_items()
            return operation.call_count

    def remaining(self):
        return [Path(row[2]) for row in self.window.results_model.rows]

    def test_cancel_keeps_file(self):
        file = self.root / 'keep.txt'
        file.touch()
        self.populate([file])
        self.assertEqual(self.run_delete([file], answer=QMessageBox.No), 0)
        self.assertTrue(file.exists())
        self.assertEqual(self.remaining(), [file])

    def test_partial_failure_keeps_failed_result(self):
        good, bad = self.root / 'good.txt', self.root / 'bad.txt'
        good.touch()
        bad.touch()
        self.populate([good, bad])
        self.run_delete([good, bad], fail=[bad])
        self.assertFalse(good.exists())
        self.assertTrue(bad.exists())
        self.assertEqual(self.remaining(), [bad])
        self.assertIn('失败：1', self.window.status_label.text())

    def test_folder_removes_descendants_but_keeps_similar_names(self):
        parent = self.root / 'folder'
        parent.mkdir()
        child = parent / 'child.txt'
        child.touch()
        other = self.root / 'folder-other.txt'
        other.touch()
        self.populate([child, other, parent])
        self.assertEqual(self.run_delete([child, parent]), 1)
        self.assertEqual(self.remaining(), [other])
        self.assertTrue(other.exists())

    def test_symbolic_link_keeps_target(self):
        target = self.root / 'target'
        target.mkdir()
        child = target / 'child.txt'
        child.touch()
        link = self.root / 'link'
        link.symlink_to(target, target_is_directory=True)
        self.populate([link, child])
        self.run_delete([link])
        self.assertTrue(child.exists())
        self.assertEqual(self.remaining(), [child])

    def test_queued_search_batch_is_ignored(self):
        file = self.root / 'found.txt'
        file.touch()
        self.populate([file])
        w = self.window
        w.is_searching = True
        old_generation = w.search_generation
        old_rows = list(w.results_model.rows)
        self.run_delete([file])
        w._add_batch(old_generation, old_rows)
        self.assertFalse(w.is_searching)
        self.assertEqual(self.remaining(), [])


if __name__ == '__main__':
    unittest.main()
