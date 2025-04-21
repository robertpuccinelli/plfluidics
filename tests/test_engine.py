import unittest
import json
from server.engine import app_server

class TestServerEngine(unittest.TestCase):
    def setUp(self):
        self.app = app_server.test_client()
        self.app.testing = True

    def test_status_get(self):
        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)

    def test_control_fail_not_json(self):
        data = {'key': 'value'}
        header = {'Content-Type': 'application/json'}
        response = self.app.post('/control', data=json.dumps(data), headers=header)

        self.assertEqual(response.status_code, 415)