import io
import json
import os
from contextlib import redirect_stdout
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import groq
import httpx
from diagnostics import groq_probe
from services.errors import GenerationError
from services.groq_service import generate_drafts, generate_follow_up
from services.settings import Settings, DEFAULT_GROQ_MODEL, load_settings
from fixtures import campaign, batch_data


def response(text, reason='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(finish_reason=reason, message=SimpleNamespace(content=text))])


def api_error(code, body=None, retry_after=None):
    http_response = httpx.Response(code, request=httpx.Request('POST', 'https://api.groq.com/openai/v1/chat/completions'),
                                  headers={'Retry-After': retry_after} if retry_after is not None else {})
    return groq.APIStatusError('PRIVATE_TEST_KEY PRIVATE_CAMPAIGN', response=http_response,
                              body=body or {'error': {'message': 'PRIVATE_TEST_KEY'}})


class GroqSettingsTests(unittest.TestCase):
    @patch.dict(os.environ, {'GROQ_API_KEY': 'test-groq-key', 'GROQ_MODEL': 'custom-model'}, clear=True)
    def test_environment_and_secret_precedence_and_hidden_repr(self):
        self.assertEqual(load_settings({}).groq_api_key, 'test-groq-key')
        self.assertEqual(load_settings({}).groq_model, 'custom-model')
        settings = load_settings({'GROQ_API_KEY': 'test-secret-key', 'GROQ_MODEL': ' llama-3.3-70b-versatile '})
        self.assertEqual(settings.groq_api_key, 'test-secret-key')
        self.assertEqual(settings.groq_model, DEFAULT_GROQ_MODEL)
        self.assertNotIn('test-secret-key', repr(settings))

    @patch.dict(os.environ, {}, clear=True)
    def test_default_model_and_missing_secrets_file(self):
        class Missing:
            def get(self, name):
                raise FileNotFoundError()
        settings = load_settings(Missing())
        self.assertFalse(settings.groq_api_key)
        self.assertEqual(settings.groq_model, 'llama-3.3-70b-versatile')


class GroqTests(unittest.TestCase):
    def setUp(self):
        factory_patch = patch('services.groq_service.groq.Groq')
        self.factory = factory_patch.start()
        self.addCleanup(factory_patch.stop)
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.client.chat.completions.create.return_value = response(json.dumps(batch_data()))
        self.settings = Settings(groq_api_key='offline-groq-test-key')
        sleep_patch = patch('services.groq_service.time.sleep')
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)

    def test_three_drafts_use_json_mode_and_factual_system_rules(self):
        result = generate_drafts(self.settings, campaign())
        self.assertEqual(len(result.drafts), 3)
        kwargs = self.client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs['model'], DEFAULT_GROQ_MODEL)
        self.assertEqual(kwargs['response_format'], {'type': 'json_object'})
        self.assertIn('Never invent', kwargs['messages'][0]['content'])
        self.assertIn('drafts', kwargs['messages'][0]['content'])
        self.assertEqual(self.factory.call_args.kwargs['max_retries'], 0)
        self.factory.return_value.__exit__.assert_called_once()

    def test_missing_key_never_calls_sdk(self):
        with self.assertRaisesRegex(GenerationError, 'GROQ_API_KEY'):
            generate_drafts(Settings(), campaign())
        self.factory.assert_not_called()

    def test_empty_malformed_wrong_count_and_repetitive_output(self):
        duplicate = batch_data()
        duplicate['drafts'][1]['body'] = duplicate['drafts'][0]['body']
        for text in [None, '', 'PRIVATE_BAD_JSON', '{"drafts":[]}', json.dumps(duplicate)]:
            self.client.chat.completions.create.return_value = response(text)
            self.client.chat.completions.create.reset_mock()
            with self.subTest(text=str(text)[:15]), self.assertLogs('services.groq_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError):
                    generate_drafts(self.settings, campaign())
            self.assertNotIn('PRIVATE_BAD_JSON', '\n'.join(logs.output))
            self.assertEqual(self.client.chat.completions.create.call_count, 1)

    def test_output_length_cta_and_truncation(self):
        for mode in ['length', 'cta', 'truncation']:
            data = batch_data()
            if mode == 'length':
                data['drafts'][0]['body'] += ' extra' * 101
            if mode == 'cta':
                data['drafts'][0]['call_to_action'] = 'Not included in the body'
            self.client.chat.completions.create.return_value = response(json.dumps(data), 'length' if mode == 'truncation' else 'stop')
            with self.subTest(mode=mode), self.assertRaises(GenerationError):
                generate_drafts(self.settings, campaign())

    def test_authentication_rate_limits_models_and_server_errors_are_safe(self):
        cases = [(401, 'authentication'), (403, 'access_denied'), (404, 'model_unavailable'),
                 (429, 'quota_or_rate_limit'), (503, 'temporary_service'), (400, 'invalid_request')]
        for code, category in cases:
            self.client.chat.completions.create.side_effect = api_error(code)
            with self.subTest(code=code), self.assertLogs('services.groq_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError) as caught:
                    generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)
            self.assertEqual(caught.exception.status_code, code)
            self.assertIn(f'provider_status_code={code}', logs.output[0])
            self.assertNotIn('PRIVATE_TEST_KEY', '\n'.join(logs.output))
            self.assertNotIn('PRIVATE_CAMPAIGN', '\n'.join(logs.output))
            self.assertNotIn('PRIVATE_TEST_KEY', str(caught.exception))

    def test_model_decommissioned_and_json_validation_failure(self):
        for reason, category in [('model_decommissioned', 'model_unavailable'), ('json_validate_failed', 'invalid_response')]:
            self.client.chat.completions.create.side_effect = api_error(400, {'error': {'code': reason, 'failed_generation': 'PRIVATE_CAMPAIGN'}})
            with self.assertRaises(GenerationError) as caught:
                generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)

    def test_timeout_connection_and_unknown_errors(self):
        request = httpx.Request('POST', 'https://api.groq.com/')
        for exc, category in [(groq.APITimeoutError(request=request), 'timeout'),
                              (groq.APIConnectionError(request=request), 'network'),
                              (RuntimeError('PRIVATE_TEST_KEY'), 'unexpected')]:
            self.client.chat.completions.create.side_effect = exc
            with self.assertRaises(GenerationError) as caught:
                generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)
            self.assertNotIn('PRIVATE_TEST_KEY', str(caught.exception))

    def test_recovery_exhaustion_and_retry_after(self):
        good = response(json.dumps(batch_data()))
        self.client.chat.completions.create.side_effect = [api_error(503, retry_after='2'), good]
        self.assertEqual(len(generate_drafts(self.settings, campaign()).drafts), 3)
        self.sleep.assert_called_once_with(2.0)
        self.client.chat.completions.create.reset_mock()
        self.client.chat.completions.create.side_effect = api_error(503)
        with self.assertRaises(GenerationError):
            generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.chat.completions.create.call_count, 3)
        self.sleep.reset_mock()
        self.client.chat.completions.create.reset_mock()
        self.client.chat.completions.create.side_effect = api_error(429, retry_after='60')
        with self.assertRaises(GenerationError):
            generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.chat.completions.create.call_count, 1)
        self.sleep.assert_not_called()

    def test_followup_uses_selected_edits_and_rejects_engagement_claims(self):
        self.client.chat.completions.create.return_value = response('{"subject":"A quick follow-up","body":"Would a short design sample be useful for your team?"}')
        followup = generate_follow_up(self.settings, campaign(), 'Edited subject', 'An edited email body with a useful offer.')
        self.assertIn('sample', followup.body)
        self.assertIn('Edited subject', self.client.chat.completions.create.call_args.kwargs['messages'][1]['content'])
        self.client.chat.completions.create.return_value = response('{"subject":"Checking in","body":"Since you opened my email, shall we talk?"}')
        with self.assertRaises(GenerationError):
            generate_follow_up(self.settings, campaign(), 'Subject', 'Original email body with enough text.')

    def test_real_sdk_wire_format_and_recovery_with_mock_http_transport(self):
        from groq._client import Groq
        requests = []
        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(503, headers={'Retry-After': '2'}, json={'error': {'message': 'PRIVATE_TEST_KEY'}})
            return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 0,
                'model': DEFAULT_GROQ_MODEL, 'choices': [{'index': 0, 'finish_reason': 'stop',
                'message': {'role': 'assistant', 'content': json.dumps(batch_data())}}]})
        self.factory.side_effect = lambda **kwargs: Groq(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(respond), trust_env=False))
        self.assertEqual(len(generate_drafts(self.settings, campaign()).drafts), 3)
        self.assertEqual(len(requests), 2, 'The SDK must not add hidden retries')
        self.sleep.assert_called_once_with(2.0)
        payload = json.loads(requests[0].content)
        self.assertEqual(payload['response_format'], {'type': 'json_object'})
        self.assertEqual(payload['model'], DEFAULT_GROQ_MODEL)
        self.assertTrue(str(requests[0].url).endswith('/openai/v1/chat/completions'))

    def test_owner_probe_checks_model_and_synthetic_json_without_printing_values(self):
        self.client.models.retrieve.return_value = SimpleNamespace(id=DEFAULT_GROQ_MODEL, active=True)
        output = io.StringIO()
        with patch('diagnostics.groq_probe.load_settings', return_value=self.settings), redirect_stdout(output):
            self.assertEqual(groq_probe.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {'model_available': True, 'validated_three_draft_json': True})
        self.client.models.retrieve.assert_called_once_with(DEFAULT_GROQ_MODEL)
        self.assertNotIn('offline-groq-test-key', output.getvalue())
