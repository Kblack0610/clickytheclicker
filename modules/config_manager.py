#!/usr/bin/env python3
"""
Configuration Manager Module

Handles loading, saving, and managing configuration files for the autoclicker.
"""

import os
import json
import glob
from typing import List, Dict, Any, Optional

class ConfigManager:
    """
    Manages configuration files for the autoclicker.
    """
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_dir: Directory for configuration files (default: <app_dir>/config)
        """
        if config_dir is None:
            # Get the application directory (directory where the module resides)
            app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # Default to <app_dir>/config/
            self.config_dir = os.path.join(app_dir, "config")
        else:
            self.config_dir = config_dir
        
        # Create config directory if it doesn't exist
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir, exist_ok=True)
    
    def list_configs(self) -> List[str]:
        """
        List all available configuration files.
        
        Returns:
            List of configuration filenames
        """
        config_files = []
        
        # Get all JSON files in the config directory
        json_pattern = os.path.join(self.config_dir, "*.json")
        config_files = [os.path.basename(f) for f in glob.glob(json_pattern)]
        
        return config_files
    
    def load_config(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a configuration file.
        
        Args:
            filename: Name of the configuration file
            
        Returns:
            Configuration dictionary or None if loading failed
        """
        # If filename doesn't have .json extension, add it
        if not filename.endswith('.json'):
            filename += '.json'
        
        # First, try with the path as provided
        filepath = filename
        
        # If that doesn't exist and the filename doesn't have a directory path,
        # try in the config directory
        if not os.path.exists(filepath) and not os.path.dirname(filename):
            filepath = os.path.join(self.config_dir, filename)
        
        if not os.path.exists(filepath):
            print(f"Configuration file not found: {filename}")
            print(f"Searched in: {filepath}")
            print(f"Config directory is: {self.config_dir}")
            return None
        
        try:
            with open(filepath, 'r') as f:
                config = json.load(f)
            return config
        except Exception as e:
            print(f"Error loading configuration: {e}")
            return None
    
    def save_config(self, config: Dict[str, Any], filename: str) -> bool:
        """
        Save a configuration file.
        
        Args:
            config: Configuration dictionary to save
            filename: Name of the configuration file
            
        Returns:
            Whether saving was successful
        """
        # If filename doesn't have .json extension, add it
        if not filename.endswith('.json'):
            filename += '.json'
        
        # If filename doesn't have path, add config directory
        if not os.path.dirname(filename):
            filepath = os.path.join(self.config_dir, filename)
        else:
            filepath = filename
        
        try:
            with open(filepath, 'w') as f:
                json.dump(config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False
    
    def delete_config(self, filename: str) -> bool:
        """
        Delete a configuration file.
        
        Args:
            filename: Name of the configuration file
            
        Returns:
            Whether deletion was successful
        """
        # If filename doesn't have .json extension, add it
        if not filename.endswith('.json'):
            filename += '.json'
        
        # If filename doesn't have path, add config directory
        if not os.path.dirname(filename):
            filepath = os.path.join(self.config_dir, filename)
        else:
            filepath = filename
        
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
                return True
            else:
                print(f"Configuration file not found: {filepath}")
                return False
        except Exception as e:
            print(f"Error deleting configuration: {e}")
            return False
