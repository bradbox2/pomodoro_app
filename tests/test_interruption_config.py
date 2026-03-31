"""
Test script to verify AppConfigManager functionality.
"""
import sys
import os
import json
import unittest

# Ensure we can import modules from the current directory
sys.path.insert(0, os.getcwd())

from app_config_manager import AppConfigManager

class TestAppConfig(unittest.TestCase):
    def setUp(self):
        # We will use the real config file for testing, but backup existing one
        self.real_config = "config.json"
        self.backup_config = "config.json.bak"
        self.files_renamed = False
        
        if os.path.exists(self.real_config):
            # Clean up any previous backup that might have been left over
            if os.path.exists(self.backup_config):
                os.remove(self.backup_config)
            os.rename(self.real_config, self.backup_config)
            self.files_renamed = True

    def tearDown(self):
        # Cleanup: remove test config and restore original
        if os.path.exists(self.real_config):
            os.remove(self.real_config)
            
        if self.files_renamed and os.path.exists(self.backup_config):
            os.rename(self.backup_config, self.real_config)

    def test_default_creation(self):
        """Verify that a default config file is created if it doesn't exist."""
        manager = AppConfigManager()
        self.assertTrue(os.path.exists(self.real_config), "Config file was not created")
        
        interruptions = manager.get_interruption_reasons()
        self.assertIn("External", interruptions)
        self.assertIn("Internal", interruptions)
        
        moods = manager.get_feedback_moods()
        self.assertIn("Excited", moods)

    def test_custom_value(self):
        """Verify loading custom values."""
        custom_data = {
            "interruptions": {
                "External": ["Aliens"],
                "Internal": ["Hunger"]
            },
            "feedback": {
                "moods": ["Sleepy"]
            }
        }
        with open(self.real_config, 'w', encoding='utf-8') as f:
            json.dump(custom_data, f)
            
        manager = AppConfigManager()
        
        # Test Interruptions
        reasons = manager.get_interruption_reasons()
        self.assertIn("Aliens", reasons["External"])
        self.assertNotIn("Colleague/Family", reasons["External"])
        
        # Test Moods
        moods = manager.get_feedback_moods()
        self.assertIn("Sleepy", moods)
        self.assertNotIn("Excited", moods)

if __name__ == "__main__":
    unittest.main()
