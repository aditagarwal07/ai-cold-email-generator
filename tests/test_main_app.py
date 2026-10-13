from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from pitchcraft import Configuration, PitchCraftError
from main_examples import campaign, drafts

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class MainAppTests(unittest.TestCase):
    def setUp(self):
        self.config_patch = patch('pitchcraft.configuration', return_value=Configuration('offline-main-test-key'))
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        generate_patch = patch('pitchcraft.generate', return_value=drafts())
        self.generate = generate_patch.start()
        self.addCleanup(generate_patch.stop)
        self.app = AppTest.from_file(APP).run(timeout=30)
        self.assertFalse(self.app.exception)

    def submit(self):
        next(button for button in self.app.button if button.label == 'Generate 3 drafts').click().run(timeout=30)
        self.assertFalse(self.app.exception)

    def fill(self):
        for name, value in campaign().items():
            if name in ('offer', 'difference', 'pain', 'facts'):
                self.app.text_area(name).set_value(value)
            elif name not in ('tone', 'length'):
                self.app.text_input(name).set_value(value)
        self.submit()

    def test_missing_key_startup_keeps_form_usable(self):
        with patch('pitchcraft.configuration', return_value=Configuration()):
            app = AppTest.from_file(APP).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(next(button for button in app.button if button.label == 'Generate 3 drafts').disabled)
        self.assertTrue(app.text_input('sender'))

    def test_validation_prevents_generation(self):
        self.submit()
        self.generate.assert_not_called()
        self.assertTrue(self.app.error)

    def test_generation_review_edit_copy_and_export_text(self):
        self.fill()
        self.generate.assert_called_once()
        self.assertEqual(len(self.app.session_state['drafts']), 3)
        revision = self.app.session_state['revision']
        self.app.text_input(f'subject_{revision}_0').set_value('Edited subject').run()
        self.app.text_area(f'body_{revision}_0').set_value('Edited body with an honest offer and next step.').run()
        self.assertIn('Edited subject', self.app.code[0].value)
        self.assertIn('Edited body', self.app.code[0].value)

    def test_failed_replacement_blocks_older_export(self):
        self.fill()
        self.generate.side_effect = PitchCraftError('AI service is temporarily unavailable.', category='outage', reference='abc123')
        self.submit()
        self.assertTrue(self.app.session_state['outdated'])
        self.assertEqual(len(self.app.code), 0)
        self.assertTrue(any('older drafts' in error.value for error in self.app.error))
        self.assertTrue(any('abc123' in caption.value for caption in self.app.caption))

    def test_invalid_replacement_and_recovery(self):
        self.fill()
        self.app.text_input('sender').set_value(' ')
        self.submit()
        self.assertTrue(self.app.session_state['outdated'])
        self.assertEqual(self.generate.call_count, 1)
        self.app.text_input('sender').set_value('Alex')
        self.submit()
        self.assertFalse(self.app.session_state['outdated'])
        self.assertEqual(len(self.app.code), 1)

    def test_start_over_and_no_send_button(self):
        self.fill()
        self.assertFalse(any('send' in button.label.casefold() for button in self.app.button))
        next(button for button in self.app.button if button.label == 'Start over').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input('sender').value, '')
        self.assertNotIn('drafts', self.app.session_state)
