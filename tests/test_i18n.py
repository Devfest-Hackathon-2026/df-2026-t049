"""Translation completeness checks without adding a JS runtime dependency."""
import json
import re
import unittest
from pathlib import Path
from html.parser import HTMLParser

WEB = Path(__file__).resolve().parents[1] / 'web'


class LocaleAttributes(HTMLParser):
    def __init__(self):
        super().__init__()
        self.keys = set()
    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name == 'data-i18n' or name.startswith('data-i18n-'):
                self.keys.add(value)


class TranslationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = (WEB / 'i18n.js').read_text(encoding='utf-8').split(';\n', 1)[0]
        cls.messages = json.loads(data[len('const messages = '):])

    def test_all_languages_have_identical_keys_and_placeholders(self):
        self.assertEqual(set(self.messages), {'zh', 'ja', 'en'})
        baseline = self.messages['zh']
        for lang, strings in self.messages.items():
            self.assertEqual(set(strings), set(baseline), lang)
            for key, message in strings.items():
                self.assertTrue(message.strip(), (lang, key))
                self.assertEqual(set(re.findall(r'\{(\w+)\}', message)),
                                 set(re.findall(r'\{(\w+)\}', baseline[key])), (lang, key))

    def test_static_and_dynamic_translation_references_exist(self):
        parser = LocaleAttributes()
        parser.feed((WEB / 'index.html').read_text(encoding='utf-8'))
        source = (WEB / 'app.js').read_text(encoding='utf-8')
        keys = parser.keys | set(re.findall(r"\bt\('([^']+)'", source))
        keys |= {'S1', 'S2', 'S3', 'nearest', 'urgency', 'idle', 'delivering', 'returning', 'blocked', 'C', 'T', 'F', 'E'}
        engine = (WEB.parent / 'reliefroute' / 'engine.py').read_text(encoding='utf-8')
        keys |= set(re.findall(r'reason = "([a-z_]+)"', engine))
        for lang, strings in self.messages.items():
            self.assertFalse(keys - strings.keys(), (lang, keys - strings.keys()))

    def test_dynamic_ui_has_no_hardcoded_chinese_text(self):
        self.assertIsNone(re.search(r'[\u3400-\u9fff]', (WEB / 'app.js').read_text(encoding='utf-8')))
        for key in ('roadTurnsOne', 'unitsOne', 'vehicleTurnsOne', 'entriesOne', 'overdueOne'):
            self.assertIn('{count}', self.messages['en'][key])


if __name__ == '__main__':
    unittest.main()
