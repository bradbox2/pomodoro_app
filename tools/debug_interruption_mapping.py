from app_config_manager import AppConfigManager
from analysis_manager import AnalysisManager
import pandas as pd

def test_mapping():
    config_manager = AppConfigManager()
    reasons = config_manager.get_interruption_reasons()
    
    print("--- Configured Reasons ---")
    category_map = {}
    for category, items in reasons.items():
        print(f"Category: {category}")
        for item in items:
            name = item['name'] if isinstance(item, dict) else item
            print(f"  - {name}")
            category_map[name] = category
            
            # Check aliases
            aliases = config_manager.get_aliases_for_name(name)
            if aliases:
                print(f"    Aliases: {aliases}")
                for alias in aliases:
                    category_map[alias] = category

    print("\n--- Testing Mapping for DB Values ---")
    # Simulate DB values found in check_interruptions_db.py
    test_reasons = ["Task Switching", "Distraction", "Social:同事/朋友/会议", "Unknown Reason"]
    
    for r in test_reasons:
        cat = category_map.get(r, "NOT_FOUND")
        print(f"'{r}' -> {cat}")

if __name__ == "__main__":
    test_mapping()
