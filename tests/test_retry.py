import json
import unittest
from unittest.mock import MagicMock, patch
import httpx
from google.genai import errors
from services.gemini_service import GenerationError, generate_drafts
from services.retry import MAX_ATTEMPTS, retry_after_seconds
from services.settings import Settings
from fixtures import batch_data, campaign


def api_error(code, retry_after=None, details=None):
    response = httpx.Response(code, headers={'Retry-After': retry_after} if retry_after is not None else {})
    return errors.APIError(code, {'error': {'status': 'UNAVAILABLE' if code >= 500 else 'RESOURCE_EXHAUSTED',
                                         'message': 'PRIVATE_TEST_KEY PRIVATE_CAMPAIGN', 'details': details or []}}, response)


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.factory_patch = patch('services.gemini_service.genai.Client')
        self.factory = self.factory_patch.start()
        self.addCleanup(self.factory_patch.stop)
        self.client = MagicMock()
        self.factory.return_value.__enter__.return_value = self.client
        self.good_response = MagicMock(text=json.dumps(batch_data()))
        self.settings = Settings('offline-test-key')
        sleep_patch = patch('services.gemini_service.time.sleep')
        self.sleep = sleep_patch.start()
        self.addCleanup(sleep_patch.stop)
        jitter_patch = patch('services.retry.random.uniform', side_effect=lambda lower, upper: upper)
        jitter_patch.start()
        self.addCleanup(jitter_patch.stop)

    def test_transient_errors_recover_without_changing_model_or_schema(self):
        for code in [500, 502, 503, 429]:
            self.client.models.generate_content.reset_mock()
            self.sleep.reset_mock()
            self.client.models.generate_content.side_effect = [api_error(code), self.good_response]
            with self.subTest(code=code), self.assertLogs('services.gemini_service', level='WARNING') as logs:
                result = generate_drafts(self.settings, campaign())
            self.assertEqual(len(result.drafts), 3)
            self.assertEqual(self.client.models.generate_content.call_count, 2)
            self.sleep.assert_called_once_with(1.0)
            calls = self.client.models.generate_content.call_args_list
            self.assertEqual(calls[0].kwargs['model'], calls[1].kwargs['model'])
            self.assertEqual(calls[0].kwargs['config'].response_json_schema, calls[1].kwargs['config'].response_json_schema)
            self.assertIn('pitchcraft_gemini_recovered', logs.output[-1])
            self.assertNotIn('PRIVATE_TEST_KEY', '\n'.join(logs.output))
            self.assertNotIn('PRIVATE_CAMPAIGN', '\n'.join(logs.output))

    def test_exhausted_retries_are_bounded_and_exponential(self):
        self.client.models.generate_content.side_effect = api_error(503)
        with self.assertLogs('services.gemini_service', level='WARNING') as logs:
            with self.assertRaises(GenerationError) as caught:
                generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.models.generate_content.call_count, MAX_ATTEMPTS)
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [1.0, 2.0])
        self.assertIn('pitchcraft_gemini_failure', logs.output[-1])
        self.assertEqual(caught.exception.status_code, 503)
        for record in logs.output:
            self.assertIn(caught.exception.reference_id, record)

    def test_jitter_is_applied_inside_exponential_bounds(self):
        self.client.models.generate_content.side_effect = [api_error(503), api_error(503), self.good_response]
        with patch('services.retry.random.uniform', side_effect=[0.7, 1.3]) as jitter:
            generate_drafts(self.settings, campaign())
        self.assertEqual([call.args for call in jitter.call_args_list], [(0.5, 1.0), (1.0, 2.0)])
        self.assertEqual([call.args[0] for call in self.sleep.call_args_list], [0.7, 1.3])

    def test_non_transient_errors_and_invalid_output_are_not_retried(self):
        for code in [400, 401, 403, 404, 504]:
            self.client.models.generate_content.reset_mock()
            self.sleep.reset_mock()
            self.client.models.generate_content.side_effect = api_error(code)
            with self.subTest(code=code), self.assertRaises(GenerationError):
                generate_drafts(self.settings, campaign())
            self.assertEqual(self.client.models.generate_content.call_count, 1)
            self.sleep.assert_not_called()
        self.client.models.generate_content.reset_mock()
        self.client.models.generate_content.side_effect = None
        self.client.models.generate_content.return_value.text = 'invalid output'
        with self.assertRaises(GenerationError):
            generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.models.generate_content.call_count, 1)

    def test_retry_after_is_respected_and_long_waits_stop(self):
        self.client.models.generate_content.side_effect = [api_error(429, '3'), self.good_response]
        generate_drafts(self.settings, campaign())
        self.sleep.assert_called_once_with(3.0)
        self.sleep.reset_mock()
        self.client.models.generate_content.reset_mock()
        self.client.models.generate_content.side_effect = api_error(503, '60')
        with self.assertRaises(GenerationError):
            generate_drafts(self.settings, campaign())
        self.sleep.assert_not_called()
        self.assertEqual(self.client.models.generate_content.call_count, 1)

    def test_total_sleep_budget_is_not_exceeded(self):
        self.client.models.generate_content.side_effect = api_error(503, '4')
        with self.assertRaises(GenerationError):
            generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.models.generate_content.call_count, 2)
        self.sleep.assert_called_once_with(4.0)

    def test_elapsed_budget_stops_retries_and_timeout_uses_remaining_budget(self):
        clock = [0.0]
        def fail(**kwargs):
            clock[0] = 61.0
            raise api_error(503)
        self.client.models.generate_content.side_effect = fail
        with patch('services.gemini_service.time.monotonic', side_effect=lambda: clock[0]):
            with self.assertRaises(GenerationError):
                generate_drafts(self.settings, campaign())
        self.assertEqual(self.client.models.generate_content.call_count, 1)
        self.sleep.assert_not_called()
        self.client.models.generate_content.side_effect = [api_error(503), self.good_response]
        self.client.models.generate_content.reset_mock()
        clock[0] = 0.0
        def sleep(delay):
            clock[0] = 50.0
        self.sleep.side_effect = sleep
        with patch('services.gemini_service.time.monotonic', side_effect=lambda: clock[0]):
            generate_drafts(self.settings, campaign())
        calls = self.client.models.generate_content.call_args_list
        self.assertEqual(calls[0].kwargs['config'].http_options.timeout, 45000)
        self.assertEqual(calls[1].kwargs['config'].http_options.timeout, 10000)

    def test_google_retryinfo_and_date_header_parsing(self):
        info = [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '4.5s'}]
        self.assertEqual(retry_after_seconds(api_error(429, '2', info)), 4.5)
        with patch('services.retry.time.time', return_value=0):
            self.assertEqual(retry_after_seconds(api_error(503, 'Thu, 01 Jan 1970 00:00:05 GMT')), 5.0)
        for value in ['nonsense', 'NaN', 'Infinity', '-3']:
            self.assertIsNone(retry_after_seconds(api_error(503, value)))

    def test_real_sdk_recovers_with_one_application_retry(self):
        from google.genai.client import Client
        from google.genai import types
        requests = []
        def respond(request):
            requests.append(request)
            if len(requests) == 1:
                return httpx.Response(503, headers={'Retry-After': '1'}, json={'error': {'code': 503, 'status': 'UNAVAILABLE'}})
            return httpx.Response(200, json={'candidates': [{'content': {'role': 'model', 'parts': [{'text': json.dumps(batch_data())}]}, 'finishReason': 'STOP'}]})
        def factory(**kwargs):
            kwargs['http_options'] = types.HttpOptions(retry_options=types.HttpRetryOptions(attempts=1),
                client_args={'transport': httpx.MockTransport(respond), 'trust_env': False})
            return Client(**kwargs)
        self.factory.side_effect = factory
        self.assertEqual(len(generate_drafts(self.settings, campaign()).drafts), 3)
        self.assertEqual(len(requests), 2, 'SDK must not add hidden retries')
        self.sleep.assert_called_once_with(1.0)
