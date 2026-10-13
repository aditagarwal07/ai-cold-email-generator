import json
import io
from contextlib import redirect_stdout
import unittest
from unittest.mock import MagicMock, patch
from google.genai import errors
from diagnostics.gemini_probe import main, run_diagnostics
from services.settings import Settings, load_settings
from fixtures import batch_data


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        factory_patch = patch('services.gemini_service.genai.Client')
        self.factory = factory_patch.start()
        self.addCleanup(factory_patch.stop)
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.settings = Settings('PRIVATE_TEST_KEY', 'configured-model')

    def test_compares_three_single_attempt_synthetic_requests(self):
        self.client.models.generate_content.side_effect = [
            MagicMock(text='PITCHCRAFT_OK'), MagicMock(text='{"status":"ok"}'),
            MagicMock(text=json.dumps(batch_data())),
        ]
        results = run_diagnostics(self.settings)
        self.assertTrue(all(result.success for result in results))
        calls = self.client.models.generate_content.call_args_list
        self.assertEqual(len(calls), 3)
        self.assertIsNone(calls[0].kwargs['config'].response_json_schema)
        self.assertIn('status', calls[1].kwargs['config'].response_json_schema['properties'])
        self.assertIn('drafts', calls[2].kwargs['config'].response_json_schema['properties'])
        self.assertEqual({call.kwargs['model'] for call in calls}, {'configured-model'})
        self.assertIn('Example Studio', calls[2].kwargs['contents'])
        self.assertNotIn('PRIVATE_TEST_KEY', repr(results))
        self.assertNotIn('Example Studio', repr(results))

    def test_structured_failure_is_distinguished_from_minimal_success(self):
        self.client.models.generate_content.side_effect = [
            MagicMock(text='PITCHCRAFT_OK'), MagicMock(text='{"status":"ok"}'),
            errors.ServerError(503, {'error': {'status': 'UNAVAILABLE', 'message': 'PRIVATE_TEST_KEY'}}),
        ]
        with patch('services.gemini_service.time.sleep') as sleep, self.assertLogs('services.gemini_service', level='WARNING') as logs:
            results = run_diagnostics(self.settings)
        self.assertEqual([result.success for result in results], [True, True, False])
        self.assertEqual(results[2].provider_status_code, 503)
        self.assertEqual(results[2].category, 'temporary_service')
        sleep.assert_not_called()
        self.assertNotIn('PRIVATE_TEST_KEY', '\n'.join(logs.output))

    def test_all_service_failures_do_not_trigger_retries_or_model_switch(self):
        self.client.models.generate_content.side_effect = errors.ServerError(503, {'error': {'status': 'UNAVAILABLE'}})
        with patch('services.gemini_service.time.sleep') as sleep:
            results = run_diagnostics(self.settings)
        self.assertEqual(self.client.models.generate_content.call_count, 3)
        self.assertTrue(all(result.provider_status_code == 503 for result in results))
        sleep.assert_not_called()

    def test_invalid_json_is_reported_without_response_content(self):
        self.client.models.generate_content.side_effect = [MagicMock(text='ok'), MagicMock(text='PRIVATE_RESPONSE_TEXT'), MagicMock(text='PRIVATE_RESPONSE_TEXT')]
        results = run_diagnostics(self.settings)
        self.assertEqual([result.category for result in results], ['success', 'invalid_response', 'invalid_response'])
        self.assertNotIn('PRIVATE_RESPONSE_TEXT', repr(results))

    def test_optional_alternate_and_diagnostics_settings_are_opt_in(self):
        with patch.dict('os.environ', {}, clear=True):
            default = load_settings({})
            self.assertEqual(default.fallback_model, '')
            self.assertFalse(default.diagnostics_enabled)
            configured = load_settings({'GEMINI_FALLBACK_MODEL': 'verified-alternate', 'ENABLE_GEMINI_DIAGNOSTICS': True})
            self.assertEqual(configured.fallback_model, 'verified-alternate')
            self.assertTrue(configured.diagnostics_enabled)
            self.assertTrue(load_settings({'ENABLE_GEMINI_DIAGNOSTICS': 'true'}).diagnostics_enabled)

    def test_cli_missing_key_returns_safe_error_without_requests(self):
        output = io.StringIO()
        with patch('sys.argv', ['gemini_probe']), patch('diagnostics.gemini_probe.load_settings', return_value=Settings()), redirect_stdout(output):
            self.assertEqual(main(), 2)
        self.assertEqual(json.loads(output.getvalue()), {'error': 'missing_api_key'})
        self.factory.assert_not_called()
