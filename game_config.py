# game_config.py
import os
import json

CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "game_settings.json")

DEFAULT_CONFIG = {
    # Screen & UI
    "SCREEN_WIDTH": 1000,
    "SCREEN_HEIGHT": 900,
    "UI_TOOLBAR_HEIGHT": 40,
    "UI_PHYSICS_PANEL_WIDTH": 320,
    "UI_PHYSICS_PANEL_CONTENT_HEIGHT": 400, # Default height for the scrollable parameter area
    "UI_PHYSICS_PANEL_MIN_WIDTH": 200,      # Minimum draggable width for the panel
    "UI_PHYSICS_PANEL_MAX_WIDTH": 800,      # Maximum draggable width
    "UI_PHYSICS_PANEL_MIN_CONTENT_HEIGHT": 100, # Minimum draggable height for parameter area
    "UI_PHYSICS_PANEL_MAX_CONTENT_HEIGHT": 1000, # Maximum draggable height for parameter area
    "UI_GROUND_CACHE_MARGIN": 100,
    "PHYSICS_PANEL_POS": [50, 50],
    "UI_PHYSICS_PANEL_TITLE_BAR_HEIGHT": 30,
    "UI_PHYSICS_PANEL_TITLE_COLOR": [60, 60, 80],
    "UI_PHYSICS_PANEL_BORDER_COLOR": [100, 100, 120],
    "UI_PHYSICS_PANEL_CLOSE_BTN_SIZE": 20,
    "UI_PHYSICS_PANEL_CLOSE_BTN_COLOR": [90, 90, 110],
    "UI_PHYSICS_PANEL_CLOSE_BTN_HOVER_COLOR": [120, 120, 140],
    "UI_PANEL_RESIZE_HANDLE_SIZE": 15,
    "UI_SCROLLBAR_WIDTH": 12,
    "UI_SCROLLBAR_COLOR": [70, 70, 90],
    "UI_SCROLLBAR_HANDLE_COLOR": [110, 110, 140],
    "UI_SCROLLBAR_HANDLE_HOVER_COLOR": [140, 140, 170],


    # Visuals
    "VOXEL_SIZE": 10,
    "GROUND_RANGE": 60,
    "CULLING_THRESHOLD": 0.05,
    "PLAYER_SCALE": 1.0,

    # Physics - Movement (ensure all your physics params are here)
    "BASE_ACCEL_RATE": 12.0,
    "FAST_ACCEL_RATE": 16.0,
    "BASE_MAX_SPEED_UPS": 30.0,
    "FAST_MAX_SPEED_UPS": 50.0,
    "DAMPING_FACTOR": 6.0,
    "MASS": 1.0,
    "STICTION_THRESHOLD": 0.3,
    "EXTRA_FRICTION": 0.05,
    "BASE_SPEED_MULTIPLIER": 1.5,

    # Physics - Jump & Vertical
    "GRAVITY_ACCEL": -25.0,
    "INITIAL_JUMP_VELOCITY_UPS": 12.0,
    "JUMP_CHARGE_BOOST_ACCEL_RATE": 22.0,
    "MAX_JUMP_CHARGE_DURATION": 0.8,
    "COEFFICIENT_OF_RESTITUTION": 0.6,
    "BOUNCE_THRESHOLD": 3.0,
    "BOUNCE_ON_LAND_VELOCITY_UPS": 0.5,

    # Physics - Ground Interaction
    "GROUND_CONTACT_THRESHOLD": 0.1,
    "REST_VELOCITY_THRESHOLD": 0.5,

    # Physics - Squish
    "elasticity": 8.0,
    "SQUISH_ON_JUMP_START": 0.85,
    "SQUISH_ON_LANDING": 0.7, # This was the old one, maybe rename/remove if MIN/MAX_SQUISH_ON_LANDING is used
    "MAX_SQUISH_FROM_CHARGE": 0.5,
    "SQUISH_DAMPING": 10.0,
    "IMPACT_VELOCITY_THRESHOLD": 3.0,
    "MAX_IMPACT_VELOCITY": 25.0,
    "MIN_SQUISH_ON_LANDING": 0.95,
    "MAX_SQUISH_ON_LANDING": 0.6,
    "BOUNCE_SOUND_THRESHOLD": 8.0,
}

config = {}

def load_config():
    global config
    current_defaults = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE_PATH):
        try:
            with open(CONFIG_FILE_PATH, 'r') as f:
                loaded_from_file = json.load(f)
                current_defaults.update(loaded_from_file)
        except json.JSONDecodeError:
            print(f"Warning: Error decoding {CONFIG_FILE_PATH}. Using defaults and attempting to overwrite.")
        except Exception as e:
            print(f"Warning: Error loading config: {e}. Using defaults.")
    config = current_defaults
    if not os.path.exists(CONFIG_FILE_PATH) or "json.JSONDecodeError" in locals() or "Exception" in locals():
        save_config() # Save if file didn't exist or was corrupt, to ensure it's valid for next time
    return config

def save_config():
    try:
        with open(CONFIG_FILE_PATH, 'w') as f:
            json.dump(config, f, indent=4, sort_keys=True)
    except Exception as e:
        print(f"Error saving config: {e}")

def get(key, default_override=None):
    if default_override is not None:
        return config.get(key, default_override)
    return config.get(key, DEFAULT_CONFIG.get(key)) # Fallback to DEFAULT_CONFIG if key somehow missing

def set_param(key, value):
    config[key] = value
    save_config()

def update_multiple(updates_dict):
    config.update(updates_dict)
    save_config()

load_config()