from pathlib import Path
import unittest
from unittest.mock import patch
from streamlit.testing.v1 import AppTest
from core.models import FollowUp
from services.settings import Settings
from services.gemini_service import GenerationError
from fixtures import batch

APP = str(Path(__file__).resolve().parents[1] / 'app.py')


class AppTests(unittest.TestCase):
    def setUp(self):
        self.settings_patch = patch('services.settings.load_settings', return_value=Settings('offline-test-key'))
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.generate_patch = patch('services.gemini_service.generate_drafts', return_value=batch())
        self.generate = self.generate_patch.start()
        self.addCleanup(self.generate_patch.stop)
        self.app = AppTest.from_file(APP).run(timeout=30)
        self.assertFalse(self.app.exception)

    def fill_campaign(self):
        for key, value in {
            'input_sender_name': 'Aditi', 'input_sender_company': 'Design Studio',
            'input_product': 'Landing page design', 'input_usp': 'Collaborative design with clear milestones',
            'input_audience': 'Independent online retailers', 'input_pain_point': 'Visitors may struggle to find product details',
            'input_objective': 'Ask permission to share a sample',
        }.items():
            self.app.text_input(key).set_value(value) if key not in ('input_product', 'input_usp', 'input_pain_point') else self.app.text_area(key).set_value(value)
        self.app.button('generate').click().run(timeout=30)
        self.assertFalse(self.app.exception)

    def test_missing_key_ui_is_usable_without_generation(self):
        with patch('services.settings.load_settings', return_value=Settings()):
            app = AppTest.from_file(APP).run(timeout=30)
        self.assertFalse(app.exception)
        self.assertTrue(app.button('generate').disabled)
        self.assertTrue(any('GEMINI_API_KEY' in item.value for item in app.info))

    def test_validation_stops_api_request(self):
        self.app.button('generate').click().run()
        self.assertTrue(self.app.error)
        self.generate.assert_not_called()

    def test_generate_edit_and_export(self):
        self.fill_campaign()
        self.generate.assert_called_once()
        self.assertEqual(len(self.app.session_state['batch'].drafts), 3)
        self.assertEqual(len(self.app.code), 1)
        revision = self.app.session_state['revision']
        self.app.text_input(f'edit_subject_{revision}_0').set_value('Edited subject').run()
        self.assertIn('Edited subject', self.app.code[0].value)
        self.assertTrue(self.app.checkbox)
        self.app.checkbox[0].check().run()
        self.assertTrue(self.app.checkbox[0].value)
        self.app.text_area(f'edit_body_{revision}_0').set_value('A changed draft body with a clear next step.').run()
        self.assertFalse(self.app.checkbox[0].value, 'Editing must invalidate review confirmation')
        self.assertFalse(self.app.exception)

    def test_stale_campaign_blocks_export_and_followup(self):
        self.fill_campaign()
        self.app.text_input('input_objective').set_value('Book a call instead').run()
        self.assertTrue(any('older drafts' in warning.value for warning in self.app.warning))
        self.assertTrue(self.app.button('generate_followup').disabled)
        self.assertEqual(len(self.app.code), 0)
        self.app.text_input('input_objective').set_value('Ask permission to share a sample').run()
        self.assertEqual(len(self.app.code), 1)

    def test_failed_regeneration_and_cooldown(self):
        self.fill_campaign()
        self.app.button('generate').click().run()
        self.assertEqual(self.generate.call_count, 1)
        self.assertTrue(any('wait' in warning.value for warning in self.app.warning))
        self.app.session_state['last_request'] = 0
        self.generate.side_effect = GenerationError('Gemini usage limit reached.')
        self.app.button('generate').click().run()
        self.assertTrue(any('previous successful' in warning.value for warning in self.app.warning))
        self.assertTrue(any('usage limit' in error.value for error in self.app.error))
        self.assertFalse(self.app.exception)

    def test_followup_source_changes_invalidate_it(self):
        self.fill_campaign()
        self.app.session_state['last_request'] = 0
        with patch('services.gemini_service.generate_follow_up', return_value=FollowUp(subject='A short follow-up', body='Would a short design example be useful for your team?')) as generate:
            self.app.button('generate_followup').click().run()
        generate.assert_called_once()
        self.assertEqual(len(self.app.code), 2)
        revision = self.app.session_state['revision']
        self.app.text_input(f'edit_subject_{revision}_0').set_value('A revised subject').run()
        self.assertTrue(any('source email' in warning.value for warning in self.app.warning))
        self.assertEqual(len(self.app.code), 1)

    def test_clear_session_removes_campaign_and_drafts(self):
        self.fill_campaign()
        next(button for button in self.app.button if button.label == 'Clear this session').click().run()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.text_input('input_sender_name').value, '')
        self.assertNotIn('batch', self.app.session_state)
        self.assertEqual(len(self.app.code), 0)

    def test_safe_service_message_and_support_reference_are_displayed(self):
        self.generate.side_effect = GenerationError(
            'Gemini reported a temporary service failure.',
            category='temporary_service', reference_id='abcd1234ef56',
        )
        self.fill_campaign()
        self.assertTrue(any('temporary service failure' in item.value for item in self.app.error))
        self.assertTrue(any('Support reference: abcd1234ef56' in item.value for item in self.app.caption))
        self.assertFalse(self.app.exception)
