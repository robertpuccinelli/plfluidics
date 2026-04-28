import unittest
from unittest.mock import Mock, patch
from plfluidics.server.models import ModelValves
from plfluidics.valves.valve_controller import ValveControllerRGS

class TestModelValves(unittest.TestCase):

    def setUp(self):
        """Set up an instance of the ModelValves before each test."""
        self.model = ModelValves()

    def test_reset(self):
        """Test the reset method initializes data structures correctly."""
        self.model.reset()
        expected_server_status = {'status': 'no_config', 'valve_states': {}}
        expected_config_status = {'config_name': 'none', 'driver': 'none', 'device': 'none', 'valves': []}
        self.assertEqual(self.model.data['server'], expected_server_status)
        self.assertEqual(self.model.data['config'], expected_config_status)
        self.assertEqual(self.model.data['controller'], [])

    def test_optionsGet(self):
        """Test the optionsGet method returns the correct options dictionary."""
        options = self.model.optionsGet()
        self.assertEqual(options, self.model.options)  # Compare to the class attribute

    def test_statusGet(self):
        """Test the statusGet method returns the current server status."""
        status = self.model.statusGet()
        self.assertEqual(status, self.model.data['server'])

    def test_configGet(self):
        """Test the configGet method returns the current configuration."""
        config = self.model.configGet()
        self.assertEqual(config, self.model.data['config'])

    def test_configSet(self):
        """Test the configSet method updates the configuration and server status."""

        new_config = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'rgs',
            'valves': [
                {'valve_alias': 'v1', 'solenoid_number': 1, 'default_state_closed': True, 'inv_polarity': False},
                {'valve_alias': 'v2', 'solenoid_number': 2, 'default_state_closed': False, 'inv_polarity': True},
            ]
        }
        self.model.configSet(new_config)

        # Check if the config is set correctly
        expected_config = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'rgs',
            'valves': [
                {'valve_alias': 'v1', 'solenoid_number': 1, 'default_state_closed': True, 'inv_polarity': False},
                {'valve_alias': 'v2', 'solenoid_number': 2, 'default_state_closed': False, 'inv_polarity': True},
            ]
        }
        self.assertEqual(self.model.data['config'], expected_config)
        # Check if the server status is updated.
        self.assertEqual(self.model.data['server']['status'], 'driver_not_initialized')

    def test_configSet_missing_keys(self):
        """Test configSet raises KeyError if keys are missing."""
        incomplete_config = {
            'config_name': 'test_config',
            'device': 'test_device',
            # 'driver' key is missing
            'valves': []
        }
        with self.assertRaises(KeyError):
            self.model.configSet(incomplete_config)

    def test_configSet_extra_keys(self):
        """Test configSet ignores extra keys (should not raise error, but extra keys are not kept)."""
        config = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'none',
            'valves': [],
            'extra_key': 123
        }
        # Should not raise, but extra_key should not be present after set
        self.model.configSet(config)
        self.assertNotIn('extra_key', self.model.data['config'])

    @patch('plfluidics.server.models.ValveControllerRGS', autospec=True)
    def test_driverSet_rgs(self, MockValveControllerRGS):
        """Test the driverSet method with 'rgs' driver."""
        #  Prevent the actual ValveControllerRGS.__init__ from being called.
        MockValveControllerRGS.return_value = Mock(spec=ValveControllerRGS)

        self.model.data['config'] = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'rgs',
            'valves': [
                {'valve_alias': 'v1', 'solenoid_number': 1, 'default_state_closed': True, 'inv_polarity': False},
                {'valve_alias': 'v2', 'solenoid_number': 2, 'default_state_closed': False, 'inv_polarity': True},
            ]
        }
        self.model.driverSet()

        expected_valve_states = {'v1': 'open', 'v2': 'closed'}
        self.assertEqual(self.model.data['server']['valve_states'], expected_valve_states)

    def test_driverSet_none(self):
        """Test the driverSet method with 'none' driver."""
        config = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'none',
            'valves': []
        }
        self.model.data['config'] = config # Directly set the config
        self.model.driverSet()

        self.assertEqual(self.model.data['controller'], [])
        self.assertEqual(self.model.data['server']['valve_states'], {})

    def test_driverSet_unknown_driver(self):
        """Test driverSet with an unknown driver type."""
        self.model.data['config'] = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'unknown_driver',
            'valves': []
        }
        # Should not raise, but controller and valve_states should be reset
        self.model.driverSet()
        self.assertEqual(self.model.data['controller'], [])
        self.assertEqual(self.model.data['server']['valve_states'], {})

    def test_driverSet_malformed_valves(self):
        """Test driverSet with malformed valve list (missing required fields)."""
        self.model.data['config'] = {
            'config_name': 'test_config',
            'device': 'test_device',
            'driver': 'rgs',
            'valves': [
                {'valve_alias': 'v1'}  # Missing other required fields
            ]
        }
        # Should raise KeyError when accessing missing fields
        with self.assertRaises(KeyError):
            self.model.driverSet()

    @patch('plfluidics.server.models.ValveControllerRGS', autospec=True)
    def test_openValve(self, MockValveControllerRGS):
        """Test the openValve method calls the controller and updates state."""
        # Create a mock instance of ValveControllerRGS
        mock_controller = Mock()
        self.model.data['controller'] = mock_controller
        self.model.data['server']['valve_states'] = {'v1': 'closed', 'v2': 'closed'}

        self.model.openValve('v1')

        mock_controller.setValveOpen.assert_called_once_with('v1')
        self.assertEqual(self.model.data['server']['valve_states']['v1'], 'open')

    @patch('plfluidics.valves.valve_controller.ValveControllerRGS', autospec=True)
    def test_closeValve(self, MockValveControllerRGS):
        """Test the closeValve method calls the controller and updates state."""
        # Create a mock instance of ValveControllerRGS
        mock_controller = Mock()
        self.model.data['controller'] = mock_controller
        self.model.data['server']['valve_states'] = {'v1': 'open', 'v2': 'open'}

        self.model.closeValve('v2')

        mock_controller.setValveClose.assert_called_once_with('v2')
        self.assertEqual(self.model.data['server']['valve_states']['v2'], 'close')

    def test_openValve_nonexistent(self):
        """Test openValve with a valve that does not exist in valve_states."""
        mock_controller = Mock()
        self.model.data['controller'] = mock_controller
        self.model.data['server']['valve_states'] = {'v1': 'closed'}
        # Should add the new valve to valve_states as 'open'
        self.model.openValve('v_nonexistent')
        mock_controller.setValveOpen.assert_called_once_with('v_nonexistent')
        self.assertEqual(self.model.data['server']['valve_states']['v_nonexistent'], 'open')

    def test_closeValve_nonexistent(self):
        """Test closeValve with a valve that does not exist in valve_states."""
        mock_controller = Mock()
        self.model.data['controller'] = mock_controller
        self.model.data['server']['valve_states'] = {'v1': 'open'}
        # Should add the new valve to valve_states as 'close'
        self.model.closeValve('v_nonexistent')
        mock_controller.setValveClose.assert_called_once_with('v_nonexistent')
        self.assertEqual(self.model.data['server']['valve_states']['v_nonexistent'], 'close')


if __name__ == '__main__':
    unittest.main()
