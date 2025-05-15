import unittest
from unittest.mock import Mock
from plfluidics.server.models import ModelConfig

class TestModelConfig(unittest.TestCase):
    def setUp(self):
        config_fields = ['config_name','author','date', 'device','driver','valves']
        driver_options = ['rgs', 'none']
        valve_fields = ['valve_alias','solenoid_number', 'default_state_closed','inv_polarity']
        valve_commands = ['open', 'close']
        options = { 'config_fields': config_fields, 
                    'driver_options': driver_options, 
                    'valve_fields': valve_fields, 
                    'valve_commands': valve_commands}
        self.model = ModelConfig(options)

    def test_processConfig_valid(self):
        config = {
            "config_name": "example_phage_ip_rev_d",
            "author": "rrp",
            "date": "20250429",
            "device": "phage_ip_rev_d",
            "driver": "rgs",
            "valves": {}
        }
        result = self.model.processConfig(config)
        self.assertEqual(result['config_name'], "example_phage_ip_rev_d")
        self.assertEqual(result['driver'], "rgs")
        self.assertIn('valves', result)

    def test_processConfig_missing_key(self):
        config = {
            "config_name": "example_phage_ip_rev_d",
            "author": "rrp",
            "date": "20250429",
            "device": "phage_ip_rev_d",
            # missing 'driver'
            "valves": {}
        }
        with self.assertRaises(KeyError):
            self.model.processConfig(config)

    def test_processConfig_extra_key(self):
        config = {
            "config_name": "example_phage_ip_rev_d",
            "author": "rrp",
            "date": "20250429",
            "device": "phage_ip_rev_d",
            "driver": "rgs",
            "valves": {},
            "extra": 123
        }
        with self.assertRaises(KeyError):
            self.model.processConfig(config)

    def test_processConfig_invalid_driver(self):
        config = {
            "config_name": "example_phage_ip_rev_d",
            "author": "rrp",
            "date": "20250429",
            "device": "phage_ip_rev_d",
            "driver": "invalid_driver",
            "valves": {}
        }
        with self.assertRaises(ValueError):
            self.model.processConfig(config)

    def test_configLinearize_valid(self):
        # Dict of dicts to list of dicts
        data = {
            'valves': {
                'bsa': {
                    'inv_polarity': False,
                    'default_state_closed': False,
                    'solenoid_number': 3
                },
                'p1': {
                    'inv_polarity': False,
                    'default_state_closed': False,
                    'solenoid_number': 16
                }
            }
        }
        result = self.model.configLinearize(data.copy())
        self.assertIsInstance(result['valves'], list)
        self.assertEqual(result['valves'][0]['valve_alias'], 'bsa')
        self.assertEqual(result['valves'][1]['solenoid_number'], 16)

    def test_configLinearize_missing_field(self):
        data = {
            'valves': {
                'bsa': {
                    # missing 'solenoid_number'
                    'inv_polarity': False,
                    'default_state_closed': False
                }
            }
        }
        with self.assertRaises(KeyError):
            self.model.configLinearize(data)

    def test_lowercaseDict(self):
        data = {
            "Config_Name": "EXAMPLE",
            "Author": "RRP",
            "Valves": {
                "BSA": {"Inv_Polarity": False, "Default_State_Closed": False, "Solenoid_Number": 3}
            }
        }
        result = self.model.lowercaseDict(data)
        self.assertIn('config_name', result)
        self.assertIn('valves', result)
        self.assertIn('bsa', result['valves'])
        self.assertFalse(result['valves']['bsa']['inv_polarity'])

if __name__ == '__main__':
    unittest.main()
