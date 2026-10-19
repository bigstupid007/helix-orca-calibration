"""Owner-private deployment-file validation; synthetic temporary files only."""
from pathlib import Path
import os
import tempfile
import unittest
from unittest.mock import patch

from integration.v1_contract import ContractError
from integration.v1_private_file import private_file


class PrivateFileTests(unittest.TestCase):
    def test_relative_missing_and_directory_refused(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for value in ('relative.json', root/'missing', root, root/'..'/'unknown', None, b'/tmp/bytes'):
                with self.subTest(value=type(value).__name__):
                    with self.assertRaises(ContractError): private_file(value)

    @unittest.skipIf(os.name == 'nt', 'POSIX mode/UID fixture')
    def test_owner_only_regular_file_and_shared_modes(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/'synthetic record with spaces.json'
            path.write_text('{}'); path.chmod(0o600)
            self.assertEqual(private_file(path), path)
            for mode in (0o640, 0o604, 0o620, 0o601, 0o660, 0o644):
                path.chmod(mode)
                with self.subTest(mode=oct(mode)):
                    with self.assertRaises(ContractError): private_file(path)
            path.chmod(0o600)
            with patch('integration.v1_private_file.os.getuid', return_value=os.getuid()+1):
                with self.assertRaises(ContractError): private_file(path)

    @unittest.skipIf(os.name == 'nt', 'POSIX symlink fixture; Windows reparse is separately qualified')
    def test_file_and_ancestor_symlink_and_fifo_refused_without_change(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); private = root/'private'; private.mkdir()
            path = private/'synthetic.json'; path.write_text('{}'); path.chmod(0o600)
            linked_file = root/'linked.json'; linked_file.symlink_to(path)
            linked_parent = root/'linked-parent'; linked_parent.symlink_to(private, target_is_directory=True)
            fifo = root/'pipe'; os.mkfifo(fifo, 0o600)
            for value in (linked_file, linked_parent/'synthetic.json', fifo):
                with self.assertRaises(ContractError): private_file(value)
            self.assertEqual(path.read_text(), '{}'); self.assertTrue(linked_file.is_symlink())

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows token/DACL test requires Windows')
    def test_windows_nonordinary_paths_refused_without_access(self):
        for value in ('\\\\server\\share\\file.json', '\\\\?\\C:\\file.json', 'C:relative.json', 'C:\\folder\\file.json:stream', 'C:\\folder\\file.json '):
            with self.subTest(value=value):
                with self.assertRaises(ContractError): private_file(value)
