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

        def test_processScript_pause(self):
            script = "pause"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['pause'])
            self.assertEqual(approx_time, 0)

        def test_processScript_multiple_operations(self):
            script = "open waste\nwait 2 s\npause\nclose waste\nwait 1 h"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['open', 'waste'])
            self.assertEqual(processed[1], ['wait', 2])
            self.assertEqual(processed[2], ['pause'])
            self.assertEqual(processed[3], ['close', 'waste'])
            self.assertEqual(processed[4], ['wait', 3600])
            self.assertEqual(approx_time, 2 + 3600)

        def test_processScript_leading_trailing_spaces(self):
            script = "   open waste   \n   wait 1 s   "
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['open', 'waste'])
            self.assertEqual(processed[1], ['wait', 1])
            self.assertEqual(approx_time, 1)

        def test_processScript_case_insensitivity(self):
            script = "OPEN waste\nWait 3 S\nClose waste"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['open', 'waste'])
            self.assertEqual(processed[1], ['wait', 3])
            self.assertEqual(processed[2], ['close', 'waste'])
            self.assertEqual(approx_time, 3)

        def test_processScript_inline_comment(self):
            script = "open waste # this is a comment\nwait 1 s"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['open', 'waste'])
            self.assertEqual(processed[1], ['wait', 1])
            self.assertEqual(approx_time, 1)

        def test_processScript_empty_script(self):
            script = ""
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed, [])
            self.assertEqual(approx_time, 0)

        def test_processScript_only_comments_and_blanks(self):
            script = "# comment\n\n# another comment\n"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed, [])
            self.assertEqual(approx_time, 0)

        def test_processScript_invalid_pump(self):
            script = "pump x hz"
            with self.assertRaises(SyntaxError):
                self.model.processScript(script)
            script = "pump 10 khz"
            with self.assertRaises(SyntaxError):
                self.model.processScript(script)
            script = "pump"
            with self.assertRaises(SyntaxError):
                self.model.processScript(script)

        def test_processScript_wait_minutes(self):
            script = "wait 2 m"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['wait', 120])
            self.assertEqual(approx_time, 120)

        def test_processScript_wait_hours(self):
            script = "wait 1 h"
            processed, approx_time = self.model.processScript(script)
            self.assertEqual(processed[0], ['wait', 3600])
            self.assertEqual(approx_time, 3600)
unittest.main()
