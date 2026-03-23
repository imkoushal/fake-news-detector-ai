"""
Model Versioning System
Track and manage different model versions for the fake news detector
"""

import json
import os
from datetime import datetime
from pathlib import Path

class ModelVersionManager:
    """Manages model versions and their metadata"""
    
    def __init__(self, versions_file: str = "models/versions.json"):
        self.versions_file = versions_file
        self.versions = self._load_versions()
    
    def _load_versions(self) -> dict:
        """Load versions from file"""
        if os.path.exists(self.versions_file):
            with open(self.versions_file, 'r') as f:
                return json.load(f)
        return {
            "current": None,
            "models": {},
            "history": []
        }
    
    def _save_versions(self):
        """Save versions to file"""
        os.makedirs(os.path.dirname(self.versions_file), exist_ok=True)
        with open(self.versions_file, 'w') as f:
            json.dump(self.versions, f, indent=2)
    
    def register_model(self, version: str, model_path: str, metadata: dict = None):
        """Register a new model version"""
        model_info = {
            "version": version,
            "model_path": model_path,
            "registered_date": datetime.now().isoformat(),
            "status": "registered",
            "metadata": metadata or {}
        }
        
        self.versions["models"][version] = model_info
        self.versions["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "registered",
            "version": version
        })
        
        self._save_versions()
        return model_info
    
    def set_active_model(self, version: str):
        """Set a model version as active/production"""
        if version not in self.versions["models"]:
            raise ValueError(f"Model version {version} not registered")
        
        self.versions["current"] = version
        self.versions["models"][version]["status"] = "active"
        
        self.versions["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "activated",
            "version": version
        })
        
        self._save_versions()
    
    def get_active_model(self) -> dict:
        """Get current active model"""
        if self.versions["current"]:
            return self.versions["models"][self.versions["current"]]
        return None
    
    def get_model_info(self, version: str) -> dict:
        """Get info for specific model version"""
        return self.versions["models"].get(version)
    
    def list_models(self) -> dict:
        """List all registered models"""
        return self.versions["models"]
    
    def get_history(self, limit: int = 10) -> list:
        """Get version history"""
        return self.versions["history"][-limit:]
    
    def deprecate_model(self, version: str):
        """Mark a model as deprecated"""
        if version not in self.versions["models"]:
            raise ValueError(f"Model version {version} not registered")
        
        self.versions["models"][version]["status"] = "deprecated"
        
        self.versions["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "deprecated",
            "version": version
        })
        
        self._save_versions()


# Initialize global manager
_manager = None

def get_model_manager():
    """Get model version manager instance"""
    global _manager
    if _manager is None:
        _manager = ModelVersionManager()
    return _manager


if __name__ == "__main__":
    # Example usage
    manager = get_model_manager()
    
    # Register a new model
    manager.register_model(
        version="2.0_advanced",
        model_path="models/pipeline.joblib",
        metadata={
            "accuracy": 0.9646,
            "precision": 0.9584,
            "recall": 0.9714,
            "training_date": "2025-11-XX",
            "trainer": "GridSearchCV"
        }
    )
    
    # Set as active
    manager.set_active_model("2.0_advanced")
    
    # Get active model
    active = manager.get_active_model()
    print(f"Active model: {active}")
    
    # List all models
    print("\nAll models:")
    for version, info in manager.list_models().items():
        print(f"  {version}: {info['status']}")
    
    # Show history
    print("\nHistory:")
    for entry in manager.get_history():
        print(f"  {entry['timestamp']}: {entry['action']} - {entry['version']}")
