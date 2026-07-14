import json
import os
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path

from focusflow.app_paths import AppPaths

class AppConfigManager:
    CONFIG_FILE = "config.json"

    DEFAULT_PREFERENCES = {
        "work_minutes": 25,
        "short_break_minutes": 5,
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
            config = deepcopy(self.DEFAULT_CONFIG)
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
            fallback = deepcopy(self.DEFAULT_CONFIG)
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
        return deepcopy(self.config.get("interruptions", self.DEFAULT_CONFIG["interruptions"]))

    @staticmethod
    def _require_name(name: str, label: str) -> str:
        cleaned = str(name or "").strip()
        if not cleaned:
            raise ValueError(f"{label} cannot be empty")
        return cleaned

    def _save_interruption_changes(self) -> None:
        self.save_config(self.config)
        self.history_manager.update_history(self.config)

    def add_interruption_category(self, category_name: str) -> str:
        category_name = self._require_name(category_name, "Category name")
        interruptions = self.config.setdefault("interruptions", {})
        if category_name in interruptions:
            raise ValueError("Category already exists")
        interruptions[category_name] = []
        self._save_interruption_changes()
        return category_name

    def rename_interruption_category(self, old_name: str, new_name: str) -> str:
        new_name = self._require_name(new_name, "Category name")
        interruptions = self.config.setdefault("interruptions", {})
        if old_name not in interruptions:
            raise ValueError("Category not found")
        if new_name != old_name and new_name in interruptions:
            raise ValueError("Category already exists")
        items = interruptions.pop(old_name)
        interruptions[new_name] = items
        self._save_interruption_changes()
        return new_name

    def delete_interruption_category(self, category_name: str) -> None:
        interruptions = self.config.setdefault("interruptions", {})
        if category_name not in interruptions:
            raise ValueError("Category not found")
        del interruptions[category_name]
        self._save_interruption_changes()

    def add_interruption_reason(self, category_name: str, reason_name: str) -> dict:
        reason_name = self._require_name(reason_name, "Interruption reason")
        interruptions = self.config.setdefault("interruptions", {})
        if category_name not in interruptions:
            raise ValueError("Category not found")
        reasons = interruptions[category_name]
        if any(str(item.get("name", "")).strip() == reason_name for item in reasons if isinstance(item, dict)):
            raise ValueError("Interruption reason already exists")
        reason = {"name": reason_name, "id": str(uuid.uuid4())}
        reasons.append(reason)
        self._save_interruption_changes()
        return dict(reason)

    def rename_interruption_reason(self, category_name: str, reason_id: str, new_name: str) -> dict:
        new_name = self._require_name(new_name, "Interruption reason")
        interruptions = self.config.setdefault("interruptions", {})
        if category_name not in interruptions:
            raise ValueError("Category not found")
        reasons = interruptions[category_name]
        if any(
            str(item.get("name", "")).strip() == new_name and item.get("id") != reason_id
            for item in reasons if isinstance(item, dict)
        ):
            raise ValueError("Interruption reason already exists")
        for item in reasons:
            if isinstance(item, dict) and item.get("id") == reason_id:
                item["name"] = new_name
                self._save_interruption_changes()
                return dict(item)
        raise ValueError("Interruption reason not found")

    def delete_interruption_reason(self, category_name: str, reason_id: str) -> None:
        interruptions = self.config.setdefault("interruptions", {})
        if category_name not in interruptions:
            raise ValueError("Category not found")
        reasons = interruptions[category_name]
        for index, item in enumerate(reasons):
            if isinstance(item, dict) and item.get("id") == reason_id:
                del reasons[index]
                self._save_interruption_changes()
                return
        raise ValueError("Interruption reason not found")

    def get_feedback_moods(self):
        """Returns the list of mood options."""
        return deepcopy(self.config.get("feedback", self.DEFAULT_CONFIG["feedback"]).get(
            "moods", self.DEFAULT_CONFIG["feedback"]["moods"]
        ))

    @staticmethod
    def _require_feedback_score(score: int) -> int:
        if isinstance(score, bool):
            raise ValueError("Feedback score must be an integer between 1 and 10")
        try:
            score = int(score)
        except (TypeError, ValueError):
            raise ValueError("Feedback score must be an integer between 1 and 10") from None
        if not 1 <= score <= 10:
            raise ValueError("Feedback score must be an integer between 1 and 10")
        return score

    def _save_feedback_changes(self) -> None:
        self.save_config(self.config)
        self.history_manager.update_history(self.config)

    def add_feedback_mood(self, name: str, score: int) -> dict:
        name = self._require_name(name, "Feedback mood")
        score = self._require_feedback_score(score)
        moods = self.config.setdefault("feedback", {}).setdefault("moods", [])
        if any(str(item.get("name", "")).strip().casefold() == name.casefold()
               for item in moods if isinstance(item, dict)):
            raise ValueError("Feedback mood already exists")
        mood = {"name": name, "score": score, "id": str(uuid.uuid4())}
        moods.append(mood)
        self._save_feedback_changes()
        return dict(mood)

    def update_feedback_mood(self, mood_id: str, name: str, score: int) -> dict:
        name = self._require_name(name, "Feedback mood")
        score = self._require_feedback_score(score)
        moods = self.config.setdefault("feedback", {}).setdefault("moods", [])
        if any(str(item.get("name", "")).strip().casefold() == name.casefold()
               and item.get("id") != mood_id for item in moods if isinstance(item, dict)):
            raise ValueError("Feedback mood already exists")
        for mood in moods:
            if isinstance(mood, dict) and mood.get("id") == mood_id:
                mood.update({"name": name, "score": score})
                self._save_feedback_changes()
                return dict(mood)
        raise ValueError("Feedback mood not found")

    def delete_feedback_mood(self, mood_id: str) -> None:
        moods = self.config.setdefault("feedback", {}).setdefault("moods", [])
        if len(moods) <= 1:
            raise ValueError("At least one feedback mood is required")
        for index, mood in enumerate(moods):
            if isinstance(mood, dict) and mood.get("id") == mood_id:
                del moods[index]
                self._save_feedback_changes()
                return
        raise ValueError("Feedback mood not found")

    def get_aliases_for_name(self, name):
        """Bridge to history manager"""
        if hasattr(self, 'history_manager'):
            return self.history_manager.get_aliases(name)
        return []
