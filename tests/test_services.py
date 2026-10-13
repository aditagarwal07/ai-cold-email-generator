import json
import os
import unittest
from unittest.mock import MagicMock, patch
import httpx
from google.genai import errors
from services.settings import Settings, DEFAULT_MODEL, load_settings
from services.gemini_service import GenerationError, generate_drafts, generate_follow_up
from fixtures import campaign, batch_data


class MissingSecrets:
    def get(self, name):
        raise FileNotFoundError('No local configuration')


class SettingsTests(unittest.TestCase):
    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-environment-key'}, clear=True)
    def test_environment_fallback_without_secrets_file(self):
        settings = load_settings(MissingSecrets())
        self.assertEqual(settings.api_key, 'test-environment-key')
        self.assertEqual(settings.model, DEFAULT_MODEL)
        self.assertNotIn('test-environment-key', repr(settings))

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_key_and_empty_model(self):
        self.assertFalse(load_settings({}).api_key)
        self.assertEqual(load_settings({'GEMINI_MODEL': ''}).model, DEFAULT_MODEL)

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'environment'}, clear=True)
    def test_secrets_take_precedence(self):
        self.assertEqual(load_settings({'GEMINI_API_KEY': 'secret', 'GEMINI_MODEL': 'custom'}), Settings('secret', 'custom'))

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-environment-key'}, clear=True)
    def test_cloud_model_and_whitespace_configuration(self):
        settings = load_settings({'GEMINI_API_KEY': '  ', 'GEMINI_MODEL': ' gemini-flash-latest '})
        self.assertEqual(settings, Settings('test-environment-key', DEFAULT_MODEL))
        self.assertEqual(load_settings({'GEMINI_MODEL': None}).model, DEFAULT_MODEL)


class GeminiTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch('services.gemini_service.genai.Client')
        self.factory = self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.client.models.generate_content.return_value.text = json.dumps(batch_data())
        self.settings = Settings('test-key', 'configured-model')

    def test_structured_request_and_client_close(self):
        output = generate_drafts(self.settings, campaign())
        self.assertEqual(len(output.drafts), 3)
        kwargs = self.client.models.generate_content.call_args.kwargs
        self.assertEqual(kwargs['model'], 'configured-model')
        self.assertEqual(kwargs['config'].response_mime_type, 'application/json')
        self.assertIn('drafts', kwargs['config'].response_json_schema['properties'])
        self.assertEqual(self.factory.call_args.kwargs['http_options'].timeout, 45000)
        self.assertEqual(self.factory.call_args.kwargs['http_options'].retry_options.attempts, 1)
        self.factory.return_value.__exit__.assert_called_once()

    def test_missing_key_does_not_call_api(self):
        with self.assertRaisesRegex(GenerationError, 'not configured'):
            generate_drafts(Settings(), campaign())
        self.factory.assert_not_called()

    def test_real_sdk_serializes_schema_with_mock_http_transport(self):
        from google.genai.client import Client
        from google.genai import types

        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={'candidates': [{
                'content': {'role': 'model', 'parts': [{'text': json.dumps(batch_data())}]},
                'finishReason': 'STOP',
            }]})

        def factory(**kwargs):
            kwargs['http_options'] = types.HttpOptions(
                timeout=45000,
                retry_options=types.HttpRetryOptions(attempts=1),
                client_args={'transport': httpx.MockTransport(respond), 'trust_env': False},
            )
            return Client(**kwargs)

        self.factory.side_effect = factory
        result = generate_drafts(self.settings, campaign())
        self.assertEqual(len(result.drafts), 3)
        self.assertEqual(len(requests), 1)
        payload = json.loads(requests[0].content)
        self.assertEqual(payload['generationConfig']['responseMimeType'], 'application/json')
        self.assertIn('drafts', payload['generationConfig']['responseJsonSchema']['properties'])
        self.assertIn('configured-model:generateContent', str(requests[0].url))

    def test_empty_malformed_and_repetitive_output(self):
        repeated = batch_data()
        repeated['drafts'][1]['body'] = repeated['drafts'][0]['body']
        for text in [None, '', '   ', 'not json', '{"drafts": []}', json.dumps(repeated)]:
            self.client.models.generate_content.return_value.text = text
            with self.subTest(text=str(text)[:20]), self.assertRaises(GenerationError):
                generate_drafts(self.settings, campaign())

    def test_length_and_cta_mismatch(self):
        data = batch_data()
        data['drafts'][0]['body'] += ' extra' * 101
        self.client.models.generate_content.return_value.text = json.dumps(data)
        with self.assertRaisesRegex(GenerationError, 'length'):
            generate_drafts(self.settings, campaign())
        data = batch_data()
        data['drafts'][0]['call_to_action'] = 'A different action'
        self.client.models.generate_content.return_value.text = json.dumps(data)
        with self.assertRaisesRegex(GenerationError, 'call to action'):
            generate_drafts(self.settings, campaign())

    def test_provider_errors_are_sanitized(self):
        cases = [(400, 'rejected'), (401, 'authenticate'), (403, 'denied'), (404, 'model'), (429, 'quota or rate limit'), (503, 'temporary service'), (504, 'too long')]
        for code, message in cases:
            self.client.models.generate_content.side_effect = errors.ClientError(code, {'error': {'message': 'SENSITIVE_API_KEY_AND_URL'}})
            with self.subTest(code=code), self.assertRaises(GenerationError) as caught:
                generate_drafts(self.settings, campaign())
            self.assertIn(message, str(caught.exception))
            self.assertNotIn('SENSITIVE', str(caught.exception))
            self.assertIsNone(caught.exception.__cause__)

    def test_structured_provider_reason_categories(self):
        cases = [
            (400, 'API_KEY_INVALID', 'invalid_api_key', 'invalid or expired'),
            (400, 'API_KEY_EXPIRED', 'invalid_api_key', 'invalid or expired'),
            (403, 'API_KEY_INVALID', 'invalid_api_key', 'invalid or expired'),
            (401, None, 'authentication', 'authenticate'),
            (403, 'API_KEY_SERVICE_BLOCKED', 'access_denied', 'restrictions'),
            (400, 'MODEL_NOT_SUPPORTED', 'model_unavailable', 'model'),
            (404, None, 'model_unavailable', 'model'),
            (429, 'QUOTA_EXCEEDED', 'quota', 'exhausted'),
            (429, 'RATE_LIMIT_EXCEEDED', 'rate_limit', 'rate limit'),
            (429, None, 'quota_or_rate_limit', 'quota or rate limit'),
            (500, None, 'temporary_service', 'temporary service'),
            (502, None, 'temporary_service', 'temporary service'),
            (503, None, 'temporary_service', 'temporary service'),
            (504, None, 'timeout', 'too long'),
        ]
        for code, reason, category, message in cases:
            details = [{'@type': 'type.googleapis.com/google.rpc.ErrorInfo', 'reason': reason}] if reason else []
            self.client.models.generate_content.side_effect = errors.ClientError(code, {'error': {'details': details}})
            with self.subTest(code=code, reason=reason), self.assertLogs('services.gemini_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError) as caught:
                    generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)
            self.assertIn(message, str(caught.exception))
            self.assertIn(f'category={category}', logs.output[0])
            self.assertIn(f'provider_status_code={code}', logs.output[0])
            self.assertIn(caught.exception.reference_id, logs.output[0])

    def test_legacy_key_and_model_error_messages_are_classified_not_exposed(self):
        for message, category in [
            ('API key not valid. Please pass a valid API key. SENSITIVE', 'invalid_api_key'),
            ('API key expired. SENSITIVE', 'invalid_api_key'),
            ('models/example is not found for API version v1beta. SENSITIVE', 'model_unavailable'),
            ('Model is not supported for generateContent. SENSITIVE', 'model_unavailable'),
        ]:
            self.client.models.generate_content.side_effect = errors.ClientError(400, {'error': {'message': message}})
            with self.subTest(message=message), self.assertLogs('services.gemini_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError) as caught:
                    generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)
            self.assertNotIn('SENSITIVE', str(caught.exception))
            self.assertNotIn('SENSITIVE', '\n'.join(logs.output))

    def test_logs_exclude_provider_payload_key_url_and_campaign(self):
        sensitive = 'PRIVATE_TEST_KEY PRIVATE_CAMPAIGN_INPUT https://sensitive.invalid/key'
        self.client.models.generate_content.side_effect = errors.ServerError(503, {'error': {
            'status': 'UNAVAILABLE', 'message': sensitive,
            'details': [{'reason': sensitive, 'metadata': {'api_key': sensitive}}],
        }})
        with self.assertLogs('services.gemini_service', level='WARNING') as logs:
            with self.assertRaises(GenerationError) as caught:
                generate_drafts(Settings('PRIVATE_TEST_KEY'), campaign(product='PRIVATE_CAMPAIGN_INPUT'))
        record = logs.records[0]
        output = logs.output[0]
        for forbidden in ['PRIVATE_TEST_KEY', 'PRIVATE_CAMPAIGN_INPUT', 'sensitive.invalid', 'Traceback']:
            self.assertNotIn(forbidden, output)
            self.assertNotIn(forbidden, str(caught.exception))
        self.assertIn('exception_type=ServerError', output)
        self.assertIn('provider_status_code=503', output)
        self.assertIn('provider_status=UNAVAILABLE', output)
        self.assertIn('category=temporary_service', output)
        self.assertIsNone(record.exc_info)

    def test_untrusted_status_and_unexpected_exception_are_not_logged_raw(self):
        for exc, expected in [
            (errors.ClientError(400, {'error': {'status': 'PRIVATE_TEST_KEY', 'message': 'PRIVATE_TEST_KEY'}}), 'provider_status=UNKNOWN'),
            (RuntimeError('PRIVATE_TEST_KEY PRIVATE_CAMPAIGN_INPUT'), 'category=unexpected'),
            (httpx.ReadTimeout('PRIVATE_TEST_KEY'), 'category=timeout'),
        ]:
            self.client.models.generate_content.side_effect = exc
            with self.assertLogs('services.gemini_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError):
                    generate_drafts(self.settings, campaign())
            self.assertIn(expected, logs.output[0])
            self.assertNotIn('PRIVATE_TEST_KEY', logs.output[0])
            self.assertNotIn('PRIVATE_CAMPAIGN_INPUT', logs.output[0])

    def test_invalid_and_empty_outputs_log_safe_categories(self):
        for text, category in [('PRIVATE_CAMPAIGN_INPUT', 'invalid_response'), ('', 'empty_response')]:
            self.client.models.generate_content.return_value.text = text
            with self.assertLogs('services.gemini_service', level='WARNING') as logs:
                with self.assertRaises(GenerationError) as caught:
                    generate_drafts(self.settings, campaign())
            self.assertEqual(caught.exception.category, category)
            self.assertNotIn('PRIVATE_CAMPAIGN_INPUT', logs.output[0])
            self.assertIn('provider_status_code=None', logs.output[0])

    def test_timeout_network_and_unknown_error(self):
        for exc, message in [(httpx.ReadTimeout('secret'), 'too long'), (httpx.ConnectError('secret'), 'reach'), (RuntimeError('secret'), 'could not')]:
            self.client.models.generate_content.side_effect = exc
            with self.assertRaises(GenerationError) as caught:
                generate_drafts(self.settings, campaign())
            self.assertIn(message, str(caught.exception))
            self.assertNotIn('secret', str(caught.exception))

    def test_followup_uses_selected_edited_text(self):
        self.client.models.generate_content.return_value.text = json.dumps({'subject': 'A quick follow-up', 'body': 'Would you like a short example of our landing page design?'})
        result = generate_follow_up(self.settings, campaign(), 'Edited subject', 'Edited email with enough content.')
        self.assertIn('example', result.body)
        prompt = self.client.models.generate_content.call_args.kwargs['contents']
        self.assertIn('Edited subject', prompt)
        self.assertIn('Edited email', prompt)

    def test_engagement_claim_followup_is_rejected(self):
        self.client.models.generate_content.return_value.text = json.dumps({'subject': 'Checking in', 'body': 'I know you read my earlier email, so can we meet?'})
        with self.assertRaises(GenerationError):
            generate_follow_up(self.settings, campaign(), 'Subject', 'Original message with enough text.')
