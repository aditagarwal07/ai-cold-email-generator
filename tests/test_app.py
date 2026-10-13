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
        # Existing Gemini regression cases explicitly select Gemini; the default is Groq.
        self.app.selectbox('ai_provider').select('Gemini').run()

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
        self.assertTrue(any('GROQ_API_KEY' in item.value for item in app.info))
        with patch('services.settings.load_settings', return_value=Settings()):
            app.selectbox('ai_provider').select('Gemini').run()
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

    def test_alternate_model_is_explicit_and_invalidates_old_drafts(self):
        with patch('services.settings.load_settings', return_value=Settings('offline-test-key', fallback_model='gemini-flash-lite-latest')):
            self.app.run()
            self.fill_campaign()
            self.assertEqual(self.generate.call_args.args[0].model, 'gemini-flash-latest')
            self.app.session_state['last_request'] = 0
            self.generate.side_effect = GenerationError('Temporary service failure.')
            self.app.button('generate').click().run()
            self.assertEqual(self.app.selectbox('model_choice').value, 'primary')
            self.app.selectbox('model_choice').select('alternate').run()
            self.assertTrue(self.app.button('generate_followup').disabled)
            self.assertEqual(len(self.app.code), 0)
            self.generate.side_effect = None
            self.app.session_state['last_request'] = 0
            self.app.button('generate').click().run()
            self.assertEqual(self.generate.call_args.args[0].model, 'gemini-flash-lite-latest')
            self.assertEqual(len(self.app.code), 1)
            self.assertFalse(self.app.exception)

    def test_synthetic_diagnostics_are_opt_in_and_separate_from_campaign(self):
        from diagnostics.gemini_probe import ProbeResult
        self.assertFalse(any(button.label == 'Run synthetic diagnostics' for button in self.app.button))
        results = [ProbeResult('minimal_text', True, 200, 'success'),
                   ProbeResult('minimal_json', True, 200, 'success'),
                   ProbeResult('three_draft_schema', False, 503, 'temporary_service', 'abcd1234ef56')]
        with patch('services.settings.load_settings', return_value=Settings('offline-test-key', diagnostics_enabled=True)), \
             patch('diagnostics.gemini_probe.run_diagnostics', return_value=results) as diagnostic:
            self.app.run()
            next(button for button in self.app.button if button.label == 'Run synthetic diagnostics').click().run()
            diagnostic.assert_called_once()
            self.generate.assert_not_called()
            self.assertEqual(len(self.app.table), 1)
            self.assertFalse(self.app.exception)

    def test_groq_is_default_and_routes_drafts_and_followups(self):
        configured = Settings(groq_api_key='offline-groq-test-key')
        with patch('services.settings.load_settings', return_value=configured), \
             patch('services.groq_service.generate_drafts', return_value=batch()) as generate, \
             patch('services.groq_service.generate_follow_up', return_value=FollowUp(
                 subject='A quick follow-up', body='Would a short example be useful for your team?')) as followup:
            self.app = AppTest.from_file(APP).run(timeout=30)
            self.assertEqual(self.app.selectbox('ai_provider').value, 'Groq')
            self.assertFalse(self.app.button('generate').disabled)
            self.fill_campaign()
            generate.assert_called_once()
            self.generate.assert_not_called()
            self.assertEqual(self.app.session_state['generated_provider'], 'Groq')
            self.app.session_state['last_request'] = 0
            self.app.button('generate_followup').click().run()
            followup.assert_called_once()
            self.assertEqual(len(self.app.code), 2)
            self.assertFalse(self.app.exception)

    def test_provider_changes_block_stale_exports_and_preserve_origin(self):
        configured = Settings('offline-gemini-key', groq_api_key='offline-groq-key')
        with patch('services.settings.load_settings', return_value=configured), \
             patch('services.groq_service.generate_drafts', return_value=batch()):
            self.app = AppTest.from_file(APP).run(timeout=30)
            self.fill_campaign()
            self.app.selectbox('ai_provider').select('Gemini').run()
            self.assertTrue(self.app.button('generate_followup').disabled)
            self.assertEqual(len(self.app.code), 0)
            self.assertTrue(any('Drafts generated with Groq' in caption.value for caption in self.app.caption))
            self.app.selectbox('ai_provider').select('Groq').run()
            self.assertEqual(len(self.app.code), 1)
            self.assertFalse(self.app.exception)

    def test_groq_failure_does_not_switch_to_gemini(self):
        configured = Settings('offline-gemini-key', groq_api_key='offline-groq-key')
        with patch('services.settings.load_settings', return_value=configured), \
             patch('services.groq_service.generate_drafts', side_effect=GenerationError('Groq rate limit reached.')):
            self.app = AppTest.from_file(APP).run(timeout=30)
            self.fill_campaign()
            self.assertEqual(self.app.selectbox('ai_provider').value, 'Groq')
            self.generate.assert_not_called()
            self.assertTrue(any('Groq rate limit' in item.value for item in self.app.error))
