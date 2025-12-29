"""Auto-Response Rule Management Module (Simplified)."""

import json
import os
import re
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path


@dataclass
class AutoResponseRule:
    """Represents an auto-response rule."""
    trigger: str
    response: str
    match_type: str = "contains"  # exact, contains, startswith, regex
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def matches(self, message: str) -> bool:
        """Check if the message matches this rule's trigger."""
        if not self.enabled:
            return False
            
        if self.match_type == "exact":
            return message == self.trigger
        elif self.match_type == "contains":
            return self.trigger in message
        elif self.match_type == "startswith":
            return message.startswith(self.trigger)
        elif self.match_type == "regex":
            try:
                return bool(re.search(self.trigger, message))
            except re.error:
                return False
        return False


class AutoResponseManager:
    """Manages auto-response rules with JSON file persistence."""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize the manager with optional config file path."""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "auto_responses.json"
            )
        self.config_path = Path(config_path)
        self.rules: list[AutoResponseRule] = []
        self._load_rules()
    
    def _load_rules(self) -> None:
        """Load rules from JSON file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.rules = [
                        AutoResponseRule(**rule) 
                        for rule in data.get("rules", [])
                    ]
            except (json.JSONDecodeError, TypeError):
                self.rules = []
        else:
            self.rules = []
    
    def _save_rules(self) -> None:
        """Save rules to JSON file."""
        data = {"rules": [asdict(rule) for rule in self.rules]}
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def add_rule(
        self,
        trigger: str,
        response: str,
        match_type: str = "contains"
    ) -> AutoResponseRule:
        """Add a new auto-response rule."""
        rule = AutoResponseRule(
            trigger=trigger,
            response=response,
            match_type=match_type
        )
        self.rules.append(rule)
        self._save_rules()
        return rule
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by its ID."""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self._save_rules()
                return True
        return False
    
    def get_rules(self) -> list[AutoResponseRule]:
        """Get all rules."""
        return self.rules.copy()
    
    def find_matching_response(self, message: str) -> Optional[str]:
        """Find a matching response for the given message."""
        for rule in self.rules:
            if rule.matches(message):
                return rule.response
        return None
    
    def toggle_rule(self, rule_id: str) -> Optional[bool]:
        """Toggle a rule's enabled status. Returns new status or None if not found."""
        for rule in self.rules:
            if rule.id == rule_id:
                rule.enabled = not rule.enabled
                self._save_rules()
                return rule.enabled
        return None
    
    def clear_all_rules(self) -> int:
        """Clear all rules. Returns the number of rules removed."""
        count = len(self.rules)
        self.rules = []
        self._save_rules()
        return count
