import hashlib
import json
from pathlib import Path
import unittest
from memminning.progress import COMPANIONS


class CharacterAssetsTests(unittest.TestCase):
    def test_all_characters_have_unchanged_source_artwork(self):
        assets = Path(__file__).resolve().parents[1] / 'assets'
        sources = json.loads((assets / 'characters/sources.json').read_text())
        expected = {'steve', 'alex', 'jonesy', 'peely', 'jett', 'sage', 'phoenix', 'reyna'}
        self.assertEqual({c[0] for c in COMPANIONS}, expected)
        self.assertEqual({s['id'] for s in sources}, expected)
        for entry in sources:
            with self.subTest(character=entry['id']):
                path = assets / entry['file']
                self.assertRegex(entry['sha256'], r'^[0-9a-f]{64}$')
                if path.exists():
                    raw = path.read_bytes()
                    self.assertTrue(raw.startswith(b'\x89PNG'))
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])
                self.assertTrue(entry['url'].startswith('https://'))
                self.assertTrue(entry['publisher'])
