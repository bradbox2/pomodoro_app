import json
import os

class AppConfigManager:
    CONFIG_FILE = "config.json"
    
    DEFAULT_CONFIG = {
        "interruptions": {
            "External": [
                {"name": "Colleague/Family", "id": "default-ext-1"}, 
                {"name": "Phone/Message", "id": "default-ext-2"}, 
                {"name": "Noise", "id": "default-ext-3"}
            ],
            "Internal": [
                {"name": "Distraction", "id": "default-int-1"}, 
                {"name": "Fatigue", "id": "default-int-2"}, 
                {"name": "Urgent Matter", "id": "default-int-3"}
            ]
        },
        "feedback": {
            "moods": [
                {"name": "Excited", "score": 9, "id": "default-mood-1"},
                {"name": "Calm", "score": 7, "id": "default-mood-2"},
                {"name": "Neutral", "score": 5, "id": "default-mood-3"},
                {"name": "Anxious", "score": 3, "id": "default-mood-4"},
                {"name": "Tired", "score": 2, "id": "default-mood-5"}
            ]
        }
    }

    def __init__(self, base_dir=None):
        import uuid
        from config_history_manager import ConfigHistoryManager
        
        if base_dir:
             self.config_path = os.path.join(base_dir, self.CONFIG_FILE)
             self.base_dir = base_dir
        else:
             self.config_path = self.CONFIG_FILE
             self.base_dir = "."
             
        self.config = self.load_config()
        
        # Change Detection Phase
        self.history_manager = ConfigHistoryManager(self.base_dir)
        self.history_manager.update_history(self.config)

    def load_config(self):
        """Loads configuration from JSON file. Creates default if missing."""
        if not os.path.exists(self.config_path):
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # AUTO-MIGRATION: Ensure all items have IDs
            modified = self._ensure_ids(data)
            if modified:
                self.save_config(data)
                
            return data
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading config: {e}. Using default.")
            return self.DEFAULT_CONFIG

    def _ensure_ids(self, config_data):
        """Injects UUIDs into config items if missing. Returns True if modified."""
        modified = False
        import uuid
        
        # 1. Interruptions
        if 'interruptions' in config_data:
            for category, items in config_data['interruptions'].items():
                for i, item in enumerate(items):
                    # Handle legacy string format "Name" -> {"name": "Name", "id": "..."}
                    if isinstance(item, str):
                        items[i] = {"name": item, "id": str(uuid.uuid4())}
                        modified = True
                    elif isinstance(item, dict):
                        if 'id' not in item:
                            item['id'] = str(uuid.uuid4())
                            modified = True
                        # Ensure name key exists? Assume yes if dict.

        # 2. Moods
        if 'feedback' in config_data and 'moods' in config_data['feedback']:
             for i, mood in enumerate(config_data['feedback']['moods']):
                 # Handle legacy strings too, though we just updated them to dicts recently
                 if isinstance(mood, str):
                     config_data['feedback']['moods'][i] = {"name": mood, "score": 5, "id": str(uuid.uuid4())}
                     modified = True
                 elif isinstance(mood, dict):
                     if 'id' not in mood:
                         mood['id'] = str(uuid.uuid4())
                         modified = True
        return modified

    def save_config(self, config_data):
        """Saves configuration to JSON file."""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving config: {e}")

    def get_interruption_reasons(self):
        """Returns the hierarchical dictionary of interruption reasons."""
        return self.config.get("interruptions", self.DEFAULT_CONFIG["interruptions"])

    def get_feedback_moods(self):
        """Returns the list of mood options."""
        return self.config.get("feedback", self.DEFAULT_CONFIG["feedback"]).get("moods", self.DEFAULT_CONFIG["feedback"]["moods"])

    def get_aliases_for_name(self, name):
        """Bridge to history manager"""
        if hasattr(self, 'history_manager'):
            return self.history_manager.get_aliases(name)
        return []
