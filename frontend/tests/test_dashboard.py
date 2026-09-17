"""Contract-shaped UI tests; values below are synthetic test data, not claims."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import requests
import streamlit as st
from streamlit.testing.v1 import AppTest

FRONTEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(FRONTEND))
from services import api_client


class DashboardTests(unittest.TestCase):
    def setUp(self):
        st.cache_data.clear()
        self.summary = dict(total_gpu_hours=100, total_cost_usd=250,
                            completed_percent=0, price_per_gpu_hour=2.5,
                            price_book_version="test-only", outcomes=[], scope_caveat="Test data")
        self.item = dict(id="idle-interactive", title="Test opportunity", savings_usd_low=0,
                         savings_usd_high=25, gpu_hours_low=0, gpu_hours_high=10,
                         capacity_percent_low=0, capacity_percent_high=10, confidence=None)
        self.detail = dict(id="idle-interactive", jobs=[123, 124], method="Test method",
                           basis="Test basis", caveats=["Synthetic"],
                           cost_if_wrong=dict(usd_low=None, usd_high=5, description="Test downside", mitigation="Test mitigation"))

    def app(self):
        return AppTest.from_file(str(FRONTEND / "app.py"), default_timeout=15)

    def test_tiles_integer_job_drilldown_and_copilot(self):
        with patch.object(api_client, 'get_summary', return_value=self.summary), \
             patch.object(api_client, 'get_opportunities', return_value={'opportunities': [self.item]}), \
             patch.object(api_client, 'get_opportunity', return_value=self.detail), \
             patch.object(api_client, 'get_job', side_effect=lambda job_id: dict(job_id=job_id, cost_usd=0, findings=[{'id': 'test-finding'}])) as get_job:
            app = self.app().run()
            self.assertFalse(app.exception)
            values = {m.label: m.value for m in app.metric}
            self.assertEqual(values['Estimated allocation cost'], '$250.00')
            self.assertEqual(values['Completed capacity'], '0.00%')
            self.assertEqual(values['Potential savings range'], '$0.00 – $25.00')
            self.assertEqual(values['Estimated downside range'], '— – $5.00')
            get_job.assert_called_with(123)
            app.selectbox(key='evidence_job_idle-interactive').select(124).run()
            get_job.assert_called_with(124)
            app.button(key='open_copilot').click().run()
            self.assertTrue(app.session_state['copilot_is_open'])
            app.button(key='close_copilot').click().run()
            self.assertFalse(app.exception)

    def test_backend_unavailable_keeps_dashboard_and_chat(self):
        with patch.object(api_client, 'get_summary', side_effect=requests.ConnectionError()), \
             patch.object(api_client, 'get_opportunities', side_effect=requests.Timeout()):
            app = self.app().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 2)
            self.assertTrue(app.button(key='open_copilot'))

    def test_contract_mismatch_is_visible_without_guessing_ids(self):
        self.detail['jobs'] = [{'job_id': 123}]
        with patch.object(api_client, 'get_summary', return_value=self.summary), \
             patch.object(api_client, 'get_opportunities', return_value={'opportunities': [self.item]}), \
             patch.object(api_client, 'get_opportunity', return_value=self.detail), \
             patch.object(api_client, 'get_job') as get_job:
            app = self.app().run()
            self.assertFalse(app.exception)
            self.assertIn('integer job IDs', app.error[0].value)
            get_job.assert_not_called()

    def test_empty_opportunities_and_null_values(self):
        with patch.object(api_client, 'get_summary', return_value={'total_cost_usd': None}), \
             patch.object(api_client, 'get_opportunities', return_value={'opportunities': []}):
            app = self.app().run()
            self.assertFalse(app.exception)
            self.assertTrue(all(m.value == '—' for m in app.metric))


if __name__ == '__main__':
    unittest.main()
