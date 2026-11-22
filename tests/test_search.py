import os
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from FileSearchQt import FileSearchWindow, NameSearchSnapshot


class SearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)

    def test_name_snapshot_continues_from_cancelled_query(self):
        for i in range(10):
            (self.root / f'file{i}.txt').touch()
        snapshot = NameSearchSnapshot((str(self.root), True))
        cancel = threading.Event()
        original_scandir = os.scandir
        with patch('FileSearchQt.os.scandir', wraps=original_scandir) as scandir:
            with closing(snapshot.entries(cancel.is_set)) as entries:
                partial = [next(entries)[0].name for _ in range(3)]
                cancel.set()
                self.assertEqual(list(entries), [])
            complete = [entry.name for entry, _ in snapshot.entries(lambda: False)]
            self.assertEqual(complete[:3], partial)
            self.assertEqual(len(set(complete)), 10)
            self.assertEqual(len(list(snapshot.entries(lambda: False))), 10)
            self.assertEqual(scandir.call_count, 1)

    def test_content_word_boundaries_at_both_edges_and_eof(self):
        file = self.root / 'boundary.txt'
        patterns = FileSearchWindow.search_patterns(['ab'], True)
        for data, expected in [
            ('xxxab abcdef', False),
            ('xxx abcz', False),
            ('xxxxx ab', True),
            ('xxxx ab', True),
            ('xx ab!', True),
            ('xxxxx abcde ab', True),
        ]:
            with self.subTest(data=data):
                file.write_text(data)
                excerpt, reason = FileSearchWindow.scan_content(
                    file, patterns, 'all', 3, True, lambda: False, chunk_size=6)
                self.assertIsNone(reason)
                self.assertEqual(bool(excerpt), expected)

    def test_content_utf16_multi_term_and_excerpt_offsets(self):
        file = self.root / 'encoded.txt'
        file.write_text('İ 开头 <关键词>\n' + '后'*20 + ' 尾部', encoding='utf-16')
        patterns = FileSearchWindow.search_patterns(['关键词', '尾部'], False)
        excerpt, reason = FileSearchWindow.scan_content(
            file, patterns, 'all', 12, False, lambda: False, chunk_size=14)
        self.assertIsNone(reason)
        self.assertIn('İ 开头 <关键词>', excerpt)

    def test_content_cancelled_during_first_read_discards_match(self):
        file = self.root / 'cancelled.txt'
        file.write_text('needle and more text')
        cancellation_checks = iter([False, False, True])
        self.assertEqual(FileSearchWindow.scan_content(
            file, ['needle'], 'any', 7, False, lambda: next(cancellation_checks),
            chunk_size=10), (None, None))

    def test_window_live_filter_clear_refresh_and_content_summary(self):
        (self.root / 'report.PDF').touch()
        (self.root / 'report.log').write_text('before <needle> after')
        (self.root / 'report-dir').mkdir()
        (self.root / 'blob.data').write_bytes(b'\0binary')
        with (self.root / 'large.log').open('wb') as large:
            large.truncate(100 * 1024 * 1024 + 1)
        config_dir = tempfile.TemporaryDirectory()
        self.addCleanup(config_dir.cleanup)
        with patch.object(FileSearchWindow, 'CONFIG_FILE', str(Path(config_dir.name) / 'config.json')):
            window = FileSearchWindow()
            self.addCleanup(window.deleteLater)
            with patch.object(window, '_start_update_check'):
                window.folder_combo.setCurrentText(str(self.root))
                window.search_combo.setCurrentText('report')
                window.extension_edit.setText('*.pdf, .DOCX')
                self.wait_for_search(window)
                snapshot = window._name_snapshot
                self.assertEqual(self.results(window), {'report.PDF'})
                (self.root / 'report-new.pdf').touch()
                window.extension_edit.clear()
                self.wait_for_search(window)
                self.assertIs(window._name_snapshot, snapshot)
                self.assertEqual(self.results(window), {'report.PDF', 'report.log', 'report-dir'})
                QTest.keyClick(window.search_combo.lineEdit(), Qt.Key_Return)
                self.wait_for_search(window)
                self.assertIn('report-new.pdf', self.results(window))

                window.content_radio.setChecked(True)
                window.search_combo.setCurrentText('missing')
                QTest.keyClick(window.search_combo.lineEdit(), Qt.Key_Return)
                self.wait_for_search(window)
                self.assertEqual(self.results(window), set())
                self.assertIn('跳过 4 个文件', window.skipped_label.text())
                self.assertIn('不支持的格式 2', window.skipped_label.text())
                self.assertIn('超过 100 MiB 1', window.skipped_label.text())
                self.assertIn('二进制文件 1', window.skipped_label.text())

                window.search_combo.setCurrentText('needle')
                window.extension_edit.setText('log')
                QTest.keyClick(window.search_combo.lineEdit(), Qt.Key_Return)
                self.wait_for_search(window)
                self.assertEqual(self.results(window), {'report.log'})
                window.table.selectRow(0)
                self.assertIn('before <needle> after', window.excerpt_label.text())
                window.set_language('en')
                self.assertIn('Match excerpt', window.excerpt_label.text())
                self.assertIn('over 100 MiB 1', window.skipped_label.text())

    def wait_for_search(self, window):
        deadline = time.monotonic() + 3
        while window.is_searching or window._live_timer.isActive() or window._search_pending:
            self.assertLess(time.monotonic(), deadline, window.status_label.text())
            QTest.qWait(10)

    @staticmethod
    def results(window):
        return {Path(row[2]).name for row in window.results_model.rows}
