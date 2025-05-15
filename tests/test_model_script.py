import unittest
import queue
from plfluidics.server.models import ModelScript

class TestModelScript(unittest.TestCase):
    def setUp(self):
        self.userQ = queue.Queue()
        self.scriptQ = queue.Queue()
        self.valve_list = ['waste']
        self.model = ModelScript(self.userQ, self.scriptQ, self.valve_list)

    def test_processScript_valid(self):
        script = "open waste\r\nwait 1 s\r\nclose waste\r\nwait 1 m"
        processed, approx_time = self.model.processScript(script)
        self.assertEqual(processed[0], ['open', 'waste'])
        self.assertEqual(processed[1], ['wait', 1])
        self.assertEqual(processed[2], ['close', 'waste'])
        self.assertEqual(processed[3], ['wait', 60])
        self.assertEqual(approx_time, 61)

    def test_processScript_invalid_operation(self):
        script = "foo waste"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)

    def test_processScript_missing_valve(self):
        script = "open"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)

    def test_processScript_invalid_valve(self):
        script = "open notavalve"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)

    def test_processScript_invalid_wait(self):
        script = "wait x s"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)
        script = "wait 1 y"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)
        script = "wait 1"
        with self.assertRaises(SyntaxError):
            self.model.processScript(script)

    def test_processScript_comment_and_blank(self):
        script = "# comment\r\n\r\nopen waste"
        processed, _ = self.model.processScript(script)
        self.assertEqual(processed[0], ['open', 'waste'])

    def test_processScript_pump(self):
        script = "pump 10 hz"
        processed, _ = self.model.processScript(script)
        self.assertEqual(processed[0], ['pump', '10'])

if __name__ == '__main__':
    unittest.main()
