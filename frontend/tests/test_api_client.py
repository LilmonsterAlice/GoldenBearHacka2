import os
import unittest
from unittest.mock import patch

from frontend.services import api_client


class APIClientTests(unittest.TestCase):
    def test_all_routes_use_environment_or_default(self):
        cases = [({}, 'http://localhost:8001'),
                 ({'API_BASE_URL': 'http://backend:8001'}, 'http://backend:8001'),
                 ({'API_BASE_URL': 'http://backend:8001/'}, 'http://backend:8001')]
        for env, base in cases:
            with self.subTest(env=env), patch.dict(os.environ, env, clear=True), patch.object(api_client.requests, 'request') as request:
                request.return_value.json.return_value = {'value': None}
                calls = [(api_client.get_summary, (), 'GET', '/api/summary'),
                         (api_client.get_opportunities, (), 'GET', '/api/opportunities'),
                         (api_client.get_opportunity, ('idle-interactive',), 'GET', '/api/opportunities/idle-interactive'),
                         (api_client.get_job, (123,), 'GET', '/api/jobs/123'),
                         (api_client.query_copilot, ('Why?', 'idle-interactive', 123), 'POST', '/api/chat')]
                for fn, args, method, path in calls:
                    self.assertEqual(fn(*args), {'value': None})
                    self.assertEqual(request.call_args.args, (method, base + path))
                    self.assertEqual(request.call_args.kwargs['timeout'], (5, 30))
                self.assertEqual(request.call_args.kwargs['json'], {
                    'question': 'Why?', 'opportunity_id': 'idle-interactive', 'job_id': 123})

    def test_http_errors_are_not_silently_converted_to_data(self):
        with patch.object(api_client.requests, 'request') as request:
            request.return_value.raise_for_status.side_effect = api_client.requests.HTTPError('Unavailable')
            with self.assertRaises(api_client.requests.HTTPError):
                api_client.get_summary()
            request.return_value.json.assert_not_called()


if __name__ == '__main__':
    unittest.main()
