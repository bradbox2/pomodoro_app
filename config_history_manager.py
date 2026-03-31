
import json
import os
import uuid
import logging
from typing import Dict, List, Any

# Ensure we have logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ConfigHistoryManager:
    HISTORY_FILE = "config_history.json"
    
    def __init__(self, base_dir=None):
        if base_dir:
            self.history_path = os.path.join(base_dir, self.HISTORY_FILE)
        else:
            self.history_path = self.HISTORY_FILE
            
        self.history = self.load_history()

    def load_history(self) -> Dict[str, Any]:
        if not os.path.exists(self.history_path):
            return {"aliases": {}, "snapshot": {}}
        try:
            with open(self.history_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Error loading config history: {e}")
            return {"aliases": {}, "snapshot": {}}

    def save_history(self):
        try:
            with open(self.history_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving config history: {e}")

    def get_aliases(self, current_name: str) -> List[str]:
        """
        Returns a list of historical aliases for the given current_name.
        This performs a reverse lookup: find IDs where 'name' is current_name,
        then get aliases for those IDs.
        Note: This simplifies things by aggregating aliases for ALL IDs that happen to have this name.
        If we want Strict Identity, we'd need the ID to query. 
        But AnalysisManager often starts with just the Name from the DB or Config.
        """
        # 1. Find the ID(s) associated with this current name in the snapshot
        target_ids = []
        for uid, info in self.history['snapshot'].items():
            if info.get('name') == current_name:
                target_ids.append(uid)
        
        # 2. Collect aliases for these IDs
        aliases = set()
        for uid in target_ids:
            if uid in self.history['aliases']:
                aliases.update(self.history['aliases'][uid])
                
        return list(aliases)

    def update_history(self, current_config: Dict[str, Any]):
        """
        Compares current_config with snapshot and updates aliases.
        Strategy:
        - Match by ID.
        - If ID matches:
            - If (Index Same OR Category Same) AND (Name Diff) -> RENAME (Add Alias).
            - If (Index Diff AND Category Diff) -> MOVE (Stop Comparison / Reset Aliases?).
              User Rule: "Location changes... stop comparison".
              Implementation: If strictly moved, we DO NOT add the old name as alias.
              In fact, should we remove old aliases? 
              A "Move" implies the current state is a NEW SERIES. 
              So yes, for this ID, we effective start fresh.
        """
        snapshot = self.history.get('snapshot', {})
        new_snapshot = {}
        affected_ids = set()

        # Helper to flatten config into list of items with metadata
        current_items = []
        
        # Parse Interruptions
        if 'interruptions' in current_config:
            for category, items in current_config['interruptions'].items():
                for idx, item in enumerate(items):
                    # Handle both string (legacy) and dict (new)
                    if isinstance(item, dict):
                        item_id = item.get('id')
                        name = item.get('name')
                        # We only care about items with IDs for history tracking
                        if item_id:
                            current_items.append({
                                'id': item_id,
                                'name': name,
                                'category': category,
                                'index': idx,
                                'type': 'interruption'
                            })

        # Parse Moods
        if 'feedback' in current_config and 'moods' in current_config['feedback']:
            for idx, mood in enumerate(current_config['feedback']['moods']):
                 if isinstance(mood, dict):
                    mood_id = mood.get('id')
                    name = mood.get('name')
                    if mood_id:
                        current_items.append({
                            'id': mood_id,
                            'name': name,
                            'category': 'moods',
                            'index': idx,
                            'type': 'mood'
                        })

        # Process Changes
        for item in current_items:
            uid = item['id']
            name = item['name']
            category = item['category']
            index = item['index']
            
            # Add to new snapshot
            new_snapshot[uid] = {
                'name': name,
                'category': category,
                'index': index,
                'type': item['type']
            }

            if uid in snapshot:
                old = snapshot[uid]
                old_name = old.get('name')
                old_cat = old.get('category')
                old_idx = old.get('index')
                
                # Check 1: Location Changed?
                # User Rule: "Location changes (storage path or identifier position)... stop comparison"
                # We define "Location" as (Category, Index).
                location_changed = (old_cat != category) or (old_idx != index)
                
                if location_changed:
                    # STOP Comparison -> Clear history for this ID? 
                    # Or just don't link the OLD name.
                    # If we clear history, we lose previous aliases. 
                    # Prompt says "stop comparison against old data".
                    # So essentially, treat as fresh.
                    if uid in self.history['aliases']:
                        logging.info(f"Location change detected for {name} (was {old_name} at {old_cat}:{old_idx}). Clearing history.")
                        del self.history['aliases'][uid]
                        
                elif name != old_name:
                    # Location SAME, Name CHANGED -> Continue Comparison (Rename)
                    if uid not in self.history['aliases']:
                        self.history['aliases'][uid] = []
                    
                    if old_name not in self.history['aliases'][uid]:
                         self.history['aliases'][uid].append(old_name)
                         logging.info(f"Rename detected: {old_name} -> {name}. Added alias.")

        # Save
        self.history['snapshot'] = new_snapshot
        self.save_history()
