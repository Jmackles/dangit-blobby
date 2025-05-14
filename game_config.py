import os
import json

# Default config path
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_settings.json")

# Default values for all parameters
DEFAULT_CONFIG = {
    # Physics Constants
    "BASE_ACCEL_RATE": 15.0,
    "FAST_ACCEL_RATE": 20.0,
    "BASE_MAX_SPEED_UPS": 35.0,
    "FAST_MAX_SPEED_UPS": 60.0,
    "DAMPING_FACTOR": 6.0,
    "MASS": 4.0,
    "GRAVITY_ACCEL": -40.0,
    "COEFFICIENT_OF_RESTITUTION": 0.75,
    "INITIAL_JUMP_VELOCITY_UPS": 10.0,
    "JUMP_CHARGE_BOOST_ACCEL_RATE": 20.0,
    "MAX_JUMP_CHARGE_DURATION": 0.8,
    "BOUNCE_ON_LAND_VELOCITY_UPS": 0.5,
    "BOUNCE_THRESHOLD": 5.0,
    "GROUND_CONTACT_THRESHOLD": 0.1,
    "REST_VELOCITY_THRESHOLD": 0.5,
    "elasticity": 6.0,
    "SQUISH_ON_JUMP_START": 0.8,
    "SQUISH_ON_LANDING": 0.95,
    "MAX_SQUISH_FROM_CHARGE": 0.4,
    "SQUISH_DAMPING": 8.0,
    "IMPACT_VELOCITY_THRESHOLD": 3.0,
    "MAX_IMPACT_VELOCITY": 25.0,
    "MIN_SQUISH_ON_LANDING": 0.95,
    "MAX_SQUISH_ON_LANDING": 0.7,
    "BOUNCE_SOUND_THRESHOLD": 8.0,
    # New physics parameters for better movement feel
    "STICTION_THRESHOLD": 0.3,              # Below this speed, set XY velocity to zero
    "EXTRA_FRICTION": 0.05,                 # Additional friction applied when near stopping
    "BASE_SPEED_MULTIPLIER": 1.5,           # Multiplier to increase overall starting speed

    # Visual Settings
    "VOXEL_SIZE": 10,
    "GROUND_RANGE": 60,
    "CULLING_THRESHOLD": 0.05,

    # UI Settings
    "UI_TOOLBAR_HEIGHT": 40,
    "UI_PHYSICS_PANEL_WIDTH": 280,
    "UI_GROUND_CACHE_MARGIN": 100,

    # Player Settings
    "PLAYER_SCALE": 1.0,

    # Video Settings
    "SCREEN_WIDTH": 1000,
    "SCREEN_HEIGHT": 900,
}

# Global variable to store the loaded configuration
config = {}

def load_config():
    """Load configuration from file or create with defaults if it doesn't exist."""
    global config
    
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r') as f:
                loaded_config = json.load(f)
                
                # Merge with defaults to ensure all keys exist
                config = DEFAULT_CONFIG.copy()
                config.update(loaded_config)
        else:
            config = DEFAULT_CONFIG.copy()
            save_config()  # Create the file with default values
            
    except Exception as e:
        print(f"Error loading config: {e}")
        config = DEFAULT_CONFIG.copy()
    
    return config

def save_config():
    """Save the current configuration to file."""
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=4)
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False

def get(key, default=None):
    """Get a configuration value."""
    return config.get(key, default)

def set(key, value):
    """Set a configuration value and save."""
    config[key] = value
    save_config()

def update_multiple(updates_dict):
    """Update multiple configuration values at once and save."""
    config.update(updates_dict)
    save_config()

# Load config when module is imported
load_config()
