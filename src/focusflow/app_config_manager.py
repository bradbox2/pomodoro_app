import json
import os
import tempfile
from pathlib import Path

from focusflow.app_paths import AppPaths

class AppConfigManager:
    CONFIG_FILE = "config.json"

    DEFAULT_PREFERENCES = {
        "work_minutes": 2,
        "short_break_minutes": 1,
        "long_break_minutes": 15,
        "long_break_interval": 4,
        "reset_long_break_on_restart": True,
        "feedback_interval": 3,
        "always_on_top": True,
        "focused_transparency": 0.8,
        "theme_mode": "dark",
        "enable_animations": True,
        "font_size_scale": 1.0,
    }
    
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

    def __init__(self, config_path=None):
        import uuid
        from focusflow.config_history_manager import ConfigHistoryManager
        
        if config_path is None:
            # Project root (this module lives at <root>/src/focusflow/) is the
            # source for one-time migration of legacy config.json / data/.
            install_dir = Path(__file__).resolve().parents[2]
            paths = AppPaths.from_environment(install_dir)
            paths.ensure_ready()
            config_path = paths.config_path

        path = Path(config_path)
        if path.name != self.CONFIG_FILE:
            path = path / self.CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path = str(path)
        self.base_dir = str(path.parent)
             
        self.config = self.load_config()
        
        # Change Detection Phase
        self.history_manager = ConfigHistoryManager(self.base_dir)
        self.history_manager.update_history(self.config)

    def load_config(self):
        """Loads configuration from JSON file. Creates default if missing."""
        if not os.path.exists(self.config_path):
            config = dict(self.DEFAULT_CONFIG)
            config["preferences"] = dict(self.DEFAULT_PREFERENCES)
            self.save_config(config)
            return config
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # AUTO-MIGRATION: Ensure all items have IDs
            if not isinstance(data, dict):
                raise ValueError("config root must be an object")
            modified = self._ensure_ids(data)
            preferences = self._normalize_preferences(data.get("preferences"), strict=False)
            if data.get("preferences") != preferences:
                data["preferences"] = preferences
                modified = True
            if modified:
                self.save_config(data)
                
            return data
        except (json.JSONDecodeError, IOError, ValueError) as e:
            print(f"Error loading config: {e}. Using default.")
            fallback = dict(self.DEFAULT_CONFIG)
            fallback["preferences"] = dict(self.DEFAULT_PREFERENCES)
            self.save_config(fallback)
            return fallback

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
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.base_dir,
                prefix=".config-", suffix=".tmp", delete=False,
            ) as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
                temp_path = f.name
            os.replace(temp_path, self.config_path)
        except IOError as e:
            print(f"Error saving config: {e}")
            if temp_path:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass

    @classmethod
    def _normalize_preferences(cls, raw_preferences, *, strict: bool) -> dict:
        preferences = dict(cls.DEFAULT_PREFERENCES)
        if raw_preferences is None:
            return preferences
        if not isinstance(raw_preferences, dict):
            if strict:
                raise ValueError("preferences must be an object")
            return preferences

        unknown = set(raw_preferences) - set(cls.DEFAULT_PREFERENCES)
        if unknown and strict:
            raise ValueError(f"Unknown preferences: {', '.join(sorted(unknown))}")

        for key, value in raw_preferences.items():
            if key not in preferences:
                continue
            if key in {"work_minutes", "long_break_minutes"}:
                valid = isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 120
            elif key == "short_break_minutes":
                valid = isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 60
            elif key == "long_break_interval":
                valid = isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 12
            elif key == "feedback_interval":
                valid = isinstance(value, int) and not isinstance(value, bool) and 0 <= value <= 20
            elif key == "focused_transparency":
                valid = isinstance(value, (int, float)) and not isinstance(value, bool) and 0.5 <= value <= 1.0
            elif key == "font_size_scale":
                valid = isinstance(value, (int, float)) and not isinstance(value, bool) and 0.8 <= value <= 1.5
            elif key == "theme_mode":
                valid = value in {"dark", "light"}
            else:
                valid = isinstance(value, bool)
            if not valid:
                if strict:
                    raise ValueError(f"Invalid preference: {key}")
                continue
            preferences[key] = value
        return preferences

    def get_preferences(self) -> dict:
        return dict(self.config.get("preferences", self.DEFAULT_PREFERENCES))

    def update_preferences(self, updates: dict) -> dict:
        if not isinstance(updates, dict):
            raise ValueError("preferences update must be an object")
        current = self.get_preferences()
        current.update(updates)
        preferences = self._normalize_preferences(current, strict=True)
        self.config["preferences"] = preferences
        self.save_config(self.config)
        return dict(preferences)

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
