import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock
from memminning.artwork import fetch_artwork

PNG = b'\x89PNG\r\n\x1a\nfixture-bytes-for-downloader-test'
URL = 'https://fortnite-api.com/test.png'


class Response(io.BytesIO):
    def geturl(self):
        return URL


class ArtworkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.assets = Path(self.temp.name)
        (self.assets / 'characters').mkdir()
        self.record = {'id': 'test', 'file': 'characters/test.png', 'url': URL,
                       'sha256': hashlib.sha256(PNG).hexdigest()}
        self.manifest = self.assets / 'characters/sources.json'
        self.save_manifest()

    def tearDown(self):
        self.temp.cleanup()

    def save_manifest(self):
        self.manifest.write_text(json.dumps([self.record]))

    def test_download_is_checked_and_existing_valid_file_avoids_network(self):
        opener = Mock(return_value=Response(PNG))
        paths = fetch_artwork(self.assets, opener)
        self.assertEqual(paths[0].read_bytes(), PNG)
        self.assertEqual(opener.call_count, 1)
        fetch_artwork(self.assets, opener)
        self.assertEqual(opener.call_count, 1)

    def test_wrong_checksum_preserves_existing_file(self):
        target = self.assets / self.record['file']
        target.write_bytes(b'previous-local-image')
        with self.assertRaises(ValueError):
            fetch_artwork(self.assets, Mock(return_value=Response(PNG + b'changed')))
        self.assertEqual(target.read_bytes(), b'previous-local-image')

    def test_non_png_is_rejected(self):
        data = b'not-an-image'
        self.record['sha256'] = hashlib.sha256(data).hexdigest()
        self.save_manifest()
        with self.assertRaises(ValueError):
            fetch_artwork(self.assets, Mock(return_value=Response(data)))
        self.assertFalse((self.assets / self.record['file']).exists())

    def test_untrusted_host_and_path_are_rejected_before_network(self):
        for field, value in [('file', '../outside.png'), ('url', 'http://fortnite-api.com/test.png'),
                             ('url', 'https://example.com/test.png')]:
            with self.subTest(field=field, value=value):
                original = self.record[field]
                self.record[field] = value
                self.save_manifest()
                opener = Mock()
                with self.assertRaises(ValueError):
                    fetch_artwork(self.assets, opener)
                opener.assert_not_called()
                self.record[field] = original

    def test_external_redirect_is_rejected(self):
        response = Response(PNG)
        response.geturl = lambda: 'https://example.com/other.png'
        with self.assertRaises(ValueError):
            fetch_artwork(self.assets, Mock(return_value=response))
