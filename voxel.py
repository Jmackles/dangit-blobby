import pygame
import math
import game_config as cfg

# --- Constants ---
# Load initial screen dimensions from config (these keys already exist)
SCREEN_WIDTH = cfg.get("SCREEN_WIDTH")
SCREEN_HEIGHT = cfg.get("SCREEN_HEIGHT")
# Load UI constants from config
TOOLBAR_HEIGHT = cfg.get("UI_TOOLBAR_HEIGHT") 
GAME_SCREEN_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT
# Add PLAYER_SCALE global
PLAYER_SCALE = cfg.get("PLAYER_SCALE")
BASE_RADIUS = 6  # Base player radius

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN_BASE = (34, 139, 34)
BROWN = (139, 69, 19)
TOOLBAR_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)

# Load constants from config
VOXEL_SIZE = cfg.get("VOXEL_SIZE")
ISO_TILE_WIDTH_HALF_BASE = VOXEL_SIZE * 0.866 # Base for zoom
ISO_TILE_HEIGHT_HALF_BASE = VOXEL_SIZE * 0.5   # Base for zoom
ISO_Z_FACTOR_BASE = VOXEL_SIZE                # Base for zoom

GROUND_RANGE = cfg.get("GROUND_RANGE")

# --- Global Variables ---
zoom = 1.0
light_direction = [-0.577, -0.577, 0.577] # Normalized default: up-left-ish

# --- Helper Functions (moved earlier for use in global constants) ---
def normalize_vector(v):
    mag = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if mag == 0:
        return (0, 0, 0) # Or raise an error, or return v
    return (v[0]/mag, v[1]/mag, v[2]/mag)

# --- Optimization: Pre-calculated relative corner offsets for voxel faces ---
# Relative to the voxel's origin (ix, iy, iz), assuming s=1
VOXEL_CORNER_OFFSETS = {
    "iso_top":    [(0,0,1), (0,1,1), (1,1,1), (1,0,1)],
    "iso_bottom": [(1,0,0), (1,1,0), (0,1,0), (0,0,0)], # Reversed for CCW from bottom
    "iso_left_side": [(0,0,0), (0,1,0), (0,1,1), (0,0,1)],
    "iso_right_side":[(1,0,1), (1,1,1), (1,1,0), (1,0,0)],
    "iso_front_side":[(0,1,1), (0,1,0), (1,1,0), (1,1,1)], # Assuming +Y is front
    "iso_back_side": [(0,0,1), (1,0,1), (1,0,0), (0,0,0)],  # Assuming -Y is back
}

# --- Optimization: View direction for back-face culling ---
# Approximates the direction the camera is looking from, towards the origin.
# Used to determine if a face normal is pointing towards the camera.
VIEW_DIRECTION_FOR_CULLING = normalize_vector((1, 1, 0.8)) # Tuned for typical isometric view
CULLING_THRESHOLD = cfg.get("CULLING_THRESHOLD") # Small positive threshold to avoid z-fighting or shimmering at edges

# Face normals (world space - assuming standard voxel orientation)
FACE_NORMALS = {
    "iso_top": (0, 0, 1),
    "iso_bottom": (0, 0, -1),
    "iso_left_side": (-1, 0, 0),
    "iso_right_side": (1, 0, 0),
    "iso_front_side": (0, 1, 0), # Assuming +Y is "front" or "away"
    "iso_back_side": (0, -1, 0),  # Assuming -Y is "back" or "towards camera"
}

# --- New Global Variables for True 3D Rotation & Physics ---
player_rotation = (1.0, 0.0, 0.0, 0.0)  # Quaternion (w, x, y, z) for full rotation (identity)

# --- New Global Variables for Light Placement & Rolling ---
light_mode = False         # When True, next click in game sets light source
light_source_pos = None    # World XY position for the light

# --- Updated Physics Constants (frame-rate independent) ---
# Load from config
BASE_ACCEL_RATE = cfg.get("BASE_ACCEL_RATE")
FAST_ACCEL_RATE = cfg.get("FAST_ACCEL_RATE")
BASE_MAX_SPEED_UPS = cfg.get("BASE_MAX_SPEED_UPS")
FAST_MAX_SPEED_UPS = cfg.get("FAST_MAX_SPEED_UPS")
DAMPING_FACTOR = cfg.get("DAMPING_FACTOR")
MASS = cfg.get("MASS")
GRAVITY_ACCEL = cfg.get("GRAVITY_ACCEL")
COEFFICIENT_OF_RESTITUTION = cfg.get("COEFFICIENT_OF_RESTITUTION")

INITIAL_JUMP_VELOCITY_UPS = cfg.get("INITIAL_JUMP_VELOCITY_UPS")
JUMP_CHARGE_BOOST_ACCEL_RATE = cfg.get("JUMP_CHARGE_BOOST_ACCEL_RATE")
MAX_JUMP_CHARGE_DURATION = cfg.get("MAX_JUMP_CHARGE_DURATION")
BOUNCE_ON_LAND_VELOCITY_UPS = cfg.get("BOUNCE_ON_LAND_VELOCITY_UPS")
BOUNCE_THRESHOLD = cfg.get("BOUNCE_THRESHOLD")

# --- Ground Contact Detection ---
GROUND_CONTACT_THRESHOLD = cfg.get("GROUND_CONTACT_THRESHOLD")
REST_VELOCITY_THRESHOLD = cfg.get("REST_VELOCITY_THRESHOLD")

# --- Updated Jump and Elasticity Variables ---
elasticity = cfg.get("elasticity")
SQUISH_ON_JUMP_START = cfg.get("SQUISH_ON_JUMP_START")
SQUISH_ON_LANDING = cfg.get("SQUISH_ON_LANDING")
MAX_SQUISH_FROM_CHARGE = cfg.get("MAX_SQUISH_FROM_CHARGE")
SQUISH_DAMPING = cfg.get("SQUISH_DAMPING")

# --- Impact Physics ---
IMPACT_VELOCITY_THRESHOLD = cfg.get("IMPACT_VELOCITY_THRESHOLD")
MAX_IMPACT_VELOCITY = cfg.get("MAX_IMPACT_VELOCITY")
MIN_SQUISH_ON_LANDING = cfg.get("MIN_SQUISH_ON_LANDING")
MAX_SQUISH_ON_LANDING = cfg.get("MAX_SQUISH_ON_LANDING")
BOUNCE_SOUND_THRESHOLD = cfg.get("BOUNCE_SOUND_THRESHOLD")

# Player state for jumping
is_charging_jump = False    # True while space is held after initial jump, for boost
jump_charge_start_time = None # Time when jump key was pressed
squish = 1.0                # 1.0 = normal shape; lower values mean squished
is_on_ground = False        # Track ground contact state
target_squish = 1.0         # Target squish value (for damping)
squish_velocity = 0.0       # Rate of change of squish (for damping)

# --- Physics Tuning Panel ---
show_physics_panel = False
PHYSICS_PANEL_WIDTH = cfg.get("UI_PHYSICS_PANEL_WIDTH") # Load from config
PHYSICS_PANEL_COLOR = (40, 40, 60, 230) # Added alpha for slight transparency
PHYSICS_PANEL_TEXT_COLOR = (220, 220, 220)
PHYSICS_SLIDER_TRACK_COLOR = (70, 70, 90)
PHYSICS_SLIDER_HANDLE_COLOR = (150, 150, 180)
PHYSICS_TEXT_INPUT_BG_COLOR = (20, 20, 30)
PHYSICS_TEXT_INPUT_BORDER_COLOR = (180, 180, 180)

active_text_input_param_key = None # Stores var_name of parameter being edited
text_input_string = ""
dragging_slider_param_key = None # Stores var_name of slider being dragged

# --- Draggable Physics Panel State ---
physics_panel_pos = [50, 50] # Initial position, can be adjusted
dragging_physics_panel = False
physics_panel_drag_start_offset = (0, 0)
PHYSICS_PANEL_TITLE_BAR_HEIGHT = 30
PHYSICS_PANEL_TITLE_COLOR = (60, 60, 80, 230)
PHYSICS_PANEL_BORDER_COLOR = (100, 100, 120)

# Define parameters to be tuned
# Each dict: {label, var_name, min_val, max_val, format_str}
# _value_rect, _slider_track_rect, _slider_handle_rect will be added dynamically
physics_params_config = [
    {"label": "Base Accel", "var_name": "BASE_ACCEL_RATE", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"label": "Fast Accel", "var_name": "FAST_ACCEL_RATE", "min_val": 1.0, "max_val": 150.0, "format_str": "{:.1f}"},
    {"label": "Base Max Speed", "var_name": "BASE_MAX_SPEED_UPS", "min_val": 5.0, "max_val": 200.0, "format_str": "{:.1f}"},
    {"label": "Fast Max Speed", "var_name": "FAST_MAX_SPEED_UPS", "min_val": 10.0, "max_val": 300.0, "format_str": "{:.1f}"},
    {"label": "Damping Factor", "var_name": "DAMPING_FACTOR", "min_val": 0.1, "max_val": 30.0, "format_str": "{:.1f}"},
    {"label": "Mass", "var_name": "MASS", "min_val": 0.1, "max_val": 50.0, "format_str": "{:.1f}"},
    {"label": "Gravity Accel", "var_name": "GRAVITY_ACCEL", "min_val": -1000.0, "max_val": -1.0, "format_str": "{:.1f}"},
    {"label": "Restitution Coeff", "var_name": "COEFFICIENT_OF_RESTITUTION", "min_val": 0.0, "max_val": 1.0, "format_str": "{:.2f}"},
    {"label": "Initial Jump Vel", "var_name": "INITIAL_JUMP_VELOCITY_UPS", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"label": "Jump Boost Accel", "var_name": "JUMP_CHARGE_BOOST_ACCEL_RATE", "min_val": 1.0, "max_val": 200.0, "format_str": "{:.1f}"},
    {"label": "Max Jump Charge (s)", "var_name": "MAX_JUMP_CHARGE_DURATION", "min_val": 0.1, "max_val": 5.0, "format_str": "{:.2f}"},
    {"label": "Elasticity", "var_name": "elasticity", "min_val": 1.0, "max_val": 50.0, "format_str": "{:.1f}"},
    {"label": "Squish Damping", "var_name": "SQUISH_DAMPING", "min_val": 1.0, "max_val": 50.0, "format_str": "{:.1f}"},
    {"label": "Squish Jump Start", "var_name": "SQUISH_ON_JUMP_START", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    {"label": "Squish Landing", "var_name": "SQUISH_ON_LANDING", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"}, # This is a target, actual squish depends on impact
    {"label": "Max Squish Charge", "var_name": "MAX_SQUISH_FROM_CHARGE", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    # Added new tunable parameters
    {"label": "Stiction Threshold", "var_name": "STICTION_THRESHOLD", "min_val": 0.0, "max_val": 5.0, "format_str": "{:.2f}"},
    {"label": "Extra Friction", "var_name": "EXTRA_FRICTION", "min_val": 0.0, "max_val": 0.99, "format_str": "{:.3f}"}, # Max < 1 to avoid multiplying by zero or negative
    {"label": "Base Speed Multi", "var_name": "BASE_SPEED_MULTIPLIER", "min_val": 0.1, "max_val": 10.0, "format_str": "{:.2f}"},
]

# --- Quaternion Helper Functions ---
def quat_from_axis_angle(axis, angle):
    # axis: (x, y, z), angle in radians
    ax, ay, az = axis
    half_angle = angle / 2.0
    sin_half = math.sin(half_angle)
    return (math.cos(half_angle), ax*sin_half, ay*sin_half, az*sin_half)

def quat_mult(q1, q2):
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return (w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2)

def quat_conjugate(q):
    w, x, y, z = q
    return (w, -x, -y, -z)

def quat_rotate_point(q, point):
    # Rotate point using quaternion: p' = q * p * q_conjugate, where p is a pure quaternion (0, x, y, z)
    p = (0.0, point[0], point[1], point[2])
    qc = quat_conjugate(q)
    p_rot = quat_mult(quat_mult(q, p), qc)
    return (p_rot[1], p_rot[2], p_rot[3])

# --- Helper Functions ---
# def normalize_vector(v): # Moved to earlier in the script
#     mag = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
#     if mag == 0:
#         return (0, 0, 0) # Or raise an error, or return v
#     return (v[0]/mag, v[1]/mag, v[2]/mag)

def project_iso(ix, iy, iz, current_zoom):
    """Converts 3D VOXEL INDICES (ix, iy, iz) to 2D isometric screen coordinates, applying zoom."""
    # Scale projection factors by zoom
    iso_tile_width_half = ISO_TILE_WIDTH_HALF_BASE * current_zoom
    iso_tile_height_half = ISO_TILE_HEIGHT_HALF_BASE * current_zoom
    iso_z_factor = ISO_Z_FACTOR_BASE * current_zoom
    screen_x = (ix - iy) * iso_tile_width_half
    screen_y = (ix + iy) * iso_tile_height_half - iz * iso_z_factor
    # Return as floats for precision, convert to int just before drawing
    return screen_x, screen_y

def get_voxel_face_points_from_indices(ix, iy, iz, face_key):
    """ Optimized: uses pre-calculated offsets. ix, iy, iz are the base coords (e.g., bottom-left-back corner)."""
    offsets = VOXEL_CORNER_OFFSETS[face_key]
    return [(ix + off[0], iy + off[1], iz + off[2]) for off in offsets]

def compute_face_color_with_normal(base_color, face_normal_world, light_dir_normalized):
    dot_product = (face_normal_world[0] * light_dir_normalized[0] +
                   face_normal_world[1] * light_dir_normalized[1] +
                   face_normal_world[2] * light_dir_normalized[2])
    ambient = 0.45 # Slightly more ambient
    diffuse_intensity = max(0, dot_product) # Light doesn't "pass through"
    brightness = ambient + (1.0 - ambient) * diffuse_intensity
    return (min(255, int(base_color[0] * brightness)),
            min(255, int(base_color[1] * brightness)),
            min(255, int(base_color[2] * brightness)))

# Add these global caching variables at the top (after other globals)
cached_ground_surface = None
cached_ground_zoom = -1
cached_camera_offset = (None, None)
GROUND_CACHE_MARGIN = cfg.get("UI_GROUND_CACHE_MARGIN")  # Load from config

def render_ground_surface(draw_origin_x, draw_origin_y, current_zoom, ground_level_z_val):
    global cached_ground_surface, cached_ground_zoom, cached_camera_offset
    surface_width = SCREEN_WIDTH + GROUND_CACHE_MARGIN # Use loaded GROUND_CACHE_MARGIN
    surface_height = GAME_SCREEN_HEIGHT + GROUND_CACHE_MARGIN # Use loaded GROUND_CACHE_MARGIN
    surf = pygame.Surface((surface_width, surface_height))
    # Compute a large ground polygon so that no background is exposed.
    R = int(GROUND_RANGE * 1.5)  # Extended range for full coverage
    corners = [
        (-R, -R, ground_level_z_val),
        (R, -R, ground_level_z_val),
        (R, R, ground_level_z_val),
        (-R, R, ground_level_z_val)
    ]
    proj_corners = [project_iso(cx, cy, cz, current_zoom) for (cx, cy, cz) in corners]
    shifted = [(int(pt[0] + draw_origin_x), int(pt[1] + draw_origin_y)) for pt in proj_corners]
    color = compute_face_color_with_normal(BROWN, FACE_NORMALS["iso_top"], light_direction)
    pygame.draw.polygon(surf, color, shifted)
    return surf

# --- Physics Panel Drawing Function ---
def draw_physics_panel(screen, font, panel_height):
    global physics_params_config, active_text_input_param_key, text_input_string, physics_panel_pos

    # Use global physics_panel_pos for the panel's top-left corner
    panel_x, panel_y = physics_panel_pos[0], physics_panel_pos[1]

    # Create a surface for the entire panel including title bar
    total_panel_height = panel_height + PHYSICS_PANEL_TITLE_BAR_HEIGHT
    panel_surface = pygame.Surface((PHYSICS_PANEL_WIDTH, total_panel_height), pygame.SRCALPHA)
    
    # Define padding earlier
    padding = 10

    # Draw main panel background (content area)
    panel_surface.fill(PHYSICS_PANEL_COLOR, (0, PHYSICS_PANEL_TITLE_BAR_HEIGHT, PHYSICS_PANEL_WIDTH, panel_height))
    
    # Draw Title Bar
    pygame.draw.rect(panel_surface, PHYSICS_PANEL_TITLE_COLOR, (0, 0, PHYSICS_PANEL_WIDTH, PHYSICS_PANEL_TITLE_BAR_HEIGHT))
    title_text_surf = font.render("Physics Controls (T)", True, PHYSICS_PANEL_TEXT_COLOR)
    panel_surface.blit(title_text_surf, (padding, (PHYSICS_PANEL_TITLE_BAR_HEIGHT - title_text_surf.get_height()) // 2))
    
    # Draw border around the whole panel
    pygame.draw.rect(panel_surface, PHYSICS_PANEL_BORDER_COLOR, (0, 0, PHYSICS_PANEL_WIDTH, total_panel_height), 2)


    item_y_offset_on_surface = PHYSICS_PANEL_TITLE_BAR_HEIGHT + 15  # Start content below title bar
    label_line_height = 28
    slider_track_thickness = 8
    ruler_markings_area_height = 30
    item_vertical_spacing = 8
    # padding = 10 # Moved earlier

    for param in physics_params_config:
        item_start_y_on_surface = item_y_offset_on_surface
        
        current_item_total_height = label_line_height + item_vertical_spacing + \
                                    slider_track_thickness + ruler_markings_area_height + \
                                    item_vertical_spacing
        if item_y_offset_on_surface + current_item_total_height > total_panel_height: # Check against total panel height
            break

        # Label
        label_surf = font.render(param["label"], True, PHYSICS_PANEL_TEXT_COLOR)
        panel_surface.blit(label_surf, (padding, item_y_offset_on_surface))

        # Value display / Text input
        current_value = globals().get(param["var_name"], 0.0)
        value_str = param["format_str"].format(current_value)
        
        value_text_width_approx = len(value_str) * font.size("0")[0] + 10 
        value_display_x_on_surface = PHYSICS_PANEL_WIDTH - value_text_width_approx - padding - 60 
        
        # Rects are now screen coordinates
        param["_value_rect"] = pygame.Rect(
            panel_x + value_display_x_on_surface,
            panel_y + item_y_offset_on_surface,
            value_text_width_approx + 50, 
            label_line_height
        )
        
        if active_text_input_param_key == param["var_name"]:
            pygame.draw.rect(panel_surface, PHYSICS_TEXT_INPUT_BG_COLOR, (value_display_x_on_surface, item_y_offset_on_surface, param["_value_rect"].width - 10 , label_line_height))
            pygame.draw.rect(panel_surface, PHYSICS_TEXT_INPUT_BORDER_COLOR, (value_display_x_on_surface, item_y_offset_on_surface, param["_value_rect"].width -10, label_line_height), 1)
            input_surf = font.render(text_input_string + "|", True, PHYSICS_PANEL_TEXT_COLOR)
            panel_surface.blit(input_surf, (value_display_x_on_surface + 3, item_y_offset_on_surface + (label_line_height - font.get_height()) // 2))
        else:
            value_surf = font.render(value_str, True, PHYSICS_PANEL_TEXT_COLOR)
            panel_surface.blit(value_surf, (value_display_x_on_surface + 3, item_y_offset_on_surface + (label_line_height - font.get_height()) // 2))

        item_y_offset_on_surface += label_line_height + item_vertical_spacing

        # Slider Track
        slider_x_on_panel_surface = padding + 50 
        slider_width = PHYSICS_PANEL_WIDTH - slider_x_on_panel_surface - padding - 5 
        
        param["_slider_track_rect"] = pygame.Rect(
            panel_x + slider_x_on_panel_surface, 
            panel_y + item_y_offset_on_surface,     
            slider_width,
            slider_track_thickness
        )
        pygame.draw.rect(panel_surface, PHYSICS_SLIDER_TRACK_COLOR, (slider_x_on_panel_surface, item_y_offset_on_surface, slider_width, slider_track_thickness))

        # Slider Handle
        val_ratio = (current_value - param["min_val"]) / (param["max_val"] - param["min_val"] + 1e-6) 
        val_ratio = max(0, min(1, val_ratio)) 
        handle_pos_x_on_panel_surface = slider_x_on_panel_surface + val_ratio * slider_width
        handle_width = 10 
        handle_height = slider_track_thickness + 6 
        
        param["_slider_handle_rect"] = pygame.Rect( 
            panel_x + handle_pos_x_on_panel_surface - handle_width // 2,
            panel_y + item_y_offset_on_surface - (handle_height - slider_track_thickness)//2 , 
            handle_width,
            handle_height
        )
        pygame.draw.rect(panel_surface, PHYSICS_SLIDER_HANDLE_COLOR, (handle_pos_x_on_panel_surface - handle_width // 2, item_y_offset_on_surface - (handle_height - slider_track_thickness)//2 , handle_width, handle_height))
        
        # --- Draw ruler ticks under the slider ---
        ruler_y_on_panel_surface = item_y_offset_on_surface + slider_track_thickness + 2 
        tick_length = 4
        for tick_value in [-1000, -750, -500, -250, 0, 250, 500, 750, 1000]:
            tick_ratio_on_slider = (tick_value + 1000.0) / 2000.0
            tick_x_on_panel_surface = slider_x_on_panel_surface + tick_ratio_on_slider * slider_width
            
            is_center_tick = (tick_value == 0)
            pygame.draw.line(panel_surface, (255, 255, 255) if is_center_tick else PHYSICS_TEXT_INPUT_BORDER_COLOR, 
                             (tick_x_on_panel_surface, ruler_y_on_panel_surface), 
                             (tick_x_on_panel_surface, ruler_y_on_panel_surface + tick_length + (2 if is_center_tick else 0)), 
                             2 if is_center_tick else 1)
        
        ruler_text_y_on_panel_surface = ruler_y_on_panel_surface + tick_length + 3
        zero_text = font.render("0", True, (255, 255, 255))
        panel_surface.blit(zero_text, (slider_x_on_panel_surface + slider_width//2 - zero_text.get_width()//2, ruler_text_y_on_panel_surface))
        
        left_text = font.render("-50%", True, PHYSICS_TEXT_INPUT_BORDER_COLOR)
        panel_surface.blit(left_text, (slider_x_on_panel_surface + slider_width//4 - left_text.get_width()//2, ruler_text_y_on_panel_surface))
        
        right_text = font.render("+50%", True, PHYSICS_TEXT_INPUT_BORDER_COLOR)
        panel_surface.blit(right_text, (slider_x_on_panel_surface + 3*slider_width//4 - right_text.get_width()//2, ruler_text_y_on_panel_surface))

        item_y_offset_on_surface += slider_track_thickness + ruler_markings_area_height

        param["_item_row_rect"] = pygame.Rect(
            panel_x, 
            panel_y + item_start_y_on_surface, 
            PHYSICS_PANEL_WIDTH,
            item_y_offset_on_surface - item_start_y_on_surface 
        )
        item_y_offset_on_surface += item_vertical_spacing

    screen.blit(panel_surface, (panel_x, panel_y))

# Helper function to save parameter changes to config
def save_param_to_config(param_name, value):
    # Update both the global variable and the config file
    globals()[param_name] = value
    cfg.set(param_name, value)

# --- Main Game Logic ---
def main():
    global SCREEN_WIDTH, SCREEN_HEIGHT, GAME_SCREEN_HEIGHT
    # Initialize single-frame squish event flags to avoid undefined variables
    jump_initiated_this_frame = False # Default state before loop
    just_landed_this_frame  = False   # Default state before loop
    landing_impact_velocity = 0.0     # Default state before loop
    global zoom, light_direction, player_rotation, light_mode, light_source_pos, \
           squish, jump_charge_start_time, is_charging_jump, is_on_ground, \
           target_squish, squish_velocity
    global cached_ground_surface, cached_ground_zoom, cached_camera_offset  # Added caching globals
    global show_physics_panel, active_text_input_param_key, text_input_string, dragging_slider_param_key, physics_params_config # Physics panel globals
    global physics_panel_pos, dragging_physics_panel, physics_panel_drag_start_offset # Draggable panel globals

    pygame.init()
    # Create a resizable window
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    game_surface = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT))
    toolbar_surface = pygame.Surface((SCREEN_WIDTH, TOOLBAR_HEIGHT))
    pygame.display.set_caption("Voxel Planetoid Controls - Phase 3")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    font_big = pygame.font.Font(None, 48)

    # Initialize physics_panel_pos based on initial screen size if not already set, or to ensure it's on screen
    physics_panel_pos[0] = SCREEN_WIDTH - PHYSICS_PANEL_WIDTH - 20 # Default to top-right-ish
    physics_panel_pos[1] = TOOLBAR_HEIGHT + 20

    # --- QoL/UX State ---
    show_help = False
    paused = False
    current_fps = 0 # For FPS display
    player_voxels_shape = [] # Stores (rel_ix, rel_iy, rel_iz_shape, base_color)
    radius = 6
    # sphere_vertical_offset was here, removed as unused
    for i in range(-radius, radius + 1):
        for j in range(-radius, radius + 1):
            for k in range(-radius, radius + 1): # k is relative to sphere's center
                vx, vy, vz = i + 0.5, j + 0.5, k + 0.5
                if vx**2 + vy**2 + vz**2 <= radius**2 * 1.05:
                    # Store relative to sphere's own (0,0,0) center for shape definition
                    player_voxels_shape.append((i, j, k, GREEN_BASE))

    # voxel_set_player_shape was here, removed as unused
    # Sort the shape definition once (drawing order will be dynamic based on player_pos_world)
    player_voxels_shape.sort(key=lambda v: (v[2], v[1], v[0]))
    # Sort the shape definition once (drawing order will be dynamic based on player_pos_world)
    player_voxels_shape.sort(key=lambda v: (v[2], v[1], v[0]))

    # --- Ground Generation ---
    ground_voxels_coords = [] # Store (gx, gy, gz)
    ground_level_z = -1 # Z-index for the top surface of the ground
    for x_g in range(-GROUND_RANGE, GROUND_RANGE + 1):
        for y_g in range(-GROUND_RANGE, GROUND_RANGE + 1):
            ground_voxels_coords.append((x_g, y_g, ground_level_z))
    # Sort ground for drawing (though only top faces, less critical but good practice)
    ground_voxels_coords.sort(key=lambda v: (v[2], v[1], v[0]))

    # --- Camera and Player Variables ---
    origin_x_base = SCREEN_WIDTH // 2
    origin_y_base = GAME_SCREEN_HEIGHT // 2 # Center game view more
    camera_offset_x, camera_offset_y = 0, 0
    dragging_left, drag_start_left = False, (0,0)

    # Player's center position in world voxel indices
    # Player center uses scaled radius
    current_radius = BASE_RADIUS * PLAYER_SCALE
    player_pos_world = [0.0, 0.0, float(current_radius)] # Start with bottom of sphere at z=0
    player_vel = [0.0, 0.0, 0.0] # Velocities in units/sec
    prev_player_xy = (player_pos_world[0], player_pos_world[1])
    # For rolling physics using true 3D rotation, we track the player_rotation quaternion.
    # It starts with identity and is updated based on horizontal movement.

    running = True
    while running:
        dt = clock.get_time() / 1000.0  # Delta time in seconds
        current_fps = clock.get_fps() # Get current FPS

        # Reset per-frame flags at the START of each frame
        jump_initiated_this_frame = False
        just_landed_this_frame = False
        # landing_impact_velocity is set when just_landed_this_frame becomes true,
        # so it doesn't need explicit resetting here if only used in that context.

        # Update effective player radius from PLAYER_SCALE each frame.
        current_radius = BASE_RADIUS * PLAYER_SCALE

        # Ensure camera dragging stops when right button is released
        if not pygame.mouse.get_pressed()[2]:
            dragging_left = False

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
            elif event.type == pygame.VIDEORESIZE:
                SCREEN_WIDTH = event.w
                SCREEN_HEIGHT = event.h
                GAME_SCREEN_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
                game_surface = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT))
                toolbar_surface = pygame.Surface((SCREEN_WIDTH, TOOLBAR_HEIGHT))
                origin_x_base = SCREEN_WIDTH // 2
                origin_y_base = GAME_SCREEN_HEIGHT // 2
                # Ensure panel stays on screen after resize
                physics_panel_pos[0] = max(0, min(physics_panel_pos[0], SCREEN_WIDTH - PHYSICS_PANEL_WIDTH))
                physics_panel_pos[1] = max(TOOLBAR_HEIGHT, min(physics_panel_pos[1], SCREEN_HEIGHT - (GAME_SCREEN_HEIGHT + PHYSICS_PANEL_TITLE_BAR_HEIGHT))) # Approximate height
                cached_ground_surface = None
                cfg.set("SCREEN_WIDTH", SCREEN_WIDTH)
                cfg.set("SCREEN_HEIGHT", SCREEN_HEIGHT)
            elif event.type == pygame.KEYDOWN:
                if active_text_input_param_key:
                    if event.key == pygame.K_RETURN: # Handle Enter key for text input
                        try:
                            new_val = float(text_input_string)
                            # Clamp value to parameter's defined min/max
                            for p_cfg in physics_params_config:
                                if p_cfg["var_name"] == active_text_input_param_key:
                                    new_val = max(p_cfg["min_val"], min(p_cfg["max_val"], new_val))
                                    break
                            # Save to config file as well as updating global variable
                            save_param_to_config(active_text_input_param_key, new_val)
                        except ValueError:
                            pass # Invalid input, ignore
                        active_text_input_param_key = None # Deactivate text input
                        text_input_string = ""
                    elif event.key == pygame.K_ESCAPE:
                        active_text_input_param_key = None
                        text_input_string = ""
                    elif event.key == pygame.K_BACKSPACE:
                        text_input_string = text_input_string[:-1]
                    else:
                        text_input_string += event.unicode
                else: # No active text input, process regular keys
                    if event.key == pygame.K_h:
                        show_help = not show_help
                    elif event.key == pygame.K_p:
                        paused = not paused
                    elif event.key == pygame.K_t: # Toggle physics panel
                        show_physics_panel = not show_physics_panel
                        if not show_physics_panel and active_text_input_param_key: # If panel closed with active input
                            active_text_input_param_key = None
                            text_input_string = ""
                    if event.key == pygame.K_SPACE:
                    # On press, if on ground and not already charging a jump, begin a jump.
                        if is_on_ground and not is_charging_jump:
                            player_vel[2] = INITIAL_JUMP_VELOCITY_UPS # Apply initial jump velocity
                            is_charging_jump = True
                            jump_charge_start_time = pygame.time.get_ticks() / 1000.0
                            target_squish = SQUISH_ON_JUMP_START   # Target squish on jump start
                            is_on_ground = False                   # No longer on ground
                            jump_initiated_this_frame = True       # Set the flag indicating a jump was initiated
                    elif event.key == pygame.K_j: light_direction[0] = max(-1, light_direction[0] - 0.1)
                    elif event.key == pygame.K_l: light_direction[0] = min(1, light_direction[0] + 0.1)
                    elif event.key == pygame.K_i: light_direction[1] = max(-1, light_direction[1] - 0.1)
                    elif event.key == pygame.K_k: light_direction[1] = min(1, light_direction[1] + 0.1)
                    elif event.key == pygame.K_u: light_direction[2] = max(-1, light_direction[2] - 0.1)
                    elif event.key == pygame.K_o: light_direction[2] = min(1, light_direction[2] + 0.1)
                    light_direction = normalize_vector(light_direction) # Keep it normalized
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3:  # Right click
                    dragging_left = True
                    drag_start_left = event.pos
                mouse_pos = event.pos

                # Physics Panel Interaction (including dragging)
                panel_event_handled = False
                if show_physics_panel:
                    panel_rect_screen = pygame.Rect(physics_panel_pos[0], physics_panel_pos[1], PHYSICS_PANEL_WIDTH, GAME_SCREEN_HEIGHT + PHYSICS_PANEL_TITLE_BAR_HEIGHT)
                    title_bar_rect_screen = pygame.Rect(physics_panel_pos[0], physics_panel_pos[1], PHYSICS_PANEL_WIDTH, PHYSICS_PANEL_TITLE_BAR_HEIGHT)

                    if event.button == 1: # Left click
                        if title_bar_rect_screen.collidepoint(mouse_pos):
                            dragging_physics_panel = True
                            physics_panel_drag_start_offset = (mouse_pos[0] - physics_panel_pos[0], mouse_pos[1] - physics_panel_pos[1])
                            panel_event_handled = True # Event handled by starting a drag
                        elif panel_rect_screen.collidepoint(mouse_pos): # Click is within the panel content area
                            panel_event_handled = True # Assume click is for a UI element, prevent camera drag
                            clicked_on_ui_element = False
                            for param in physics_params_config:
                                if "_value_rect" in param and param["_value_rect"].collidepoint(mouse_pos):
                                    if active_text_input_param_key == param["var_name"]:
                                        pass 
                                    else: 
                                        if active_text_input_param_key: 
                                            try:
                                                new_val = float(text_input_string)
                                                for p_cfg_old in physics_params_config:
                                                    if p_cfg_old["var_name"] == active_text_input_param_key:
                                                        new_val = max(p_cfg_old["min_val"], min(p_cfg_old["max_val"], new_val))
                                                        break
                                                save_param_to_config(active_text_input_param_key, new_val)
                                            except ValueError: pass 
                                        active_text_input_param_key = param["var_name"]
                                        text_input_string = param["format_str"].format(globals()[param["var_name"]]).strip()
                                    clicked_on_ui_element = True
                                    break 
                                elif "_slider_track_rect" in param and param["_slider_track_rect"].collidepoint(mouse_pos):
                                    dragging_slider_param_key = param["var_name"]
                                    st_rect = param["_slider_track_rect"]
                                    click_x_relative_to_track_start = mouse_pos[0] - st_rect.left
                                    click_ratio = click_x_relative_to_track_start / st_rect.width
                                    click_ratio = max(0.0, min(1.0, click_ratio))
                                    raw_ruler_val = -1000.0 + click_ratio * 2000.0
                                    snap_increment = 250.0
                                    snapped_ruler_val = round(raw_ruler_val / snap_increment) * snap_increment
                                    snapped_ruler_val = max(-1000.0, min(1000.0, snapped_ruler_val))
                                    norm_snapped_ratio = (snapped_ruler_val + 1000.0) / 2000.0
                                    p_min, p_max = param["min_val"], param["max_val"]
                                    actual_value = p_min + norm_snapped_ratio * (p_max - p_min)
                                    try:
                                        actual_value = float(param["format_str"].format(actual_value))
                                    except ValueError: pass
                                    actual_value = max(p_min, min(p_max, actual_value))
                                    save_param_to_config(param["var_name"], actual_value)
                                    clicked_on_ui_element = True
                                    break
                            
                            if not clicked_on_ui_element and active_text_input_param_key:
                                try:
                                    new_val = float(text_input_string)
                                    for p_cfg in physics_params_config:
                                        if p_cfg["var_name"] == active_text_input_param_key:
                                            new_val = max(p_cfg["min_val"], min(p_cfg["max_val"], new_val))
                                            break
                                    save_param_to_config(active_text_input_param_key, new_val)
                                except ValueError: pass
                                active_text_input_param_key = None
                                text_input_string = ""
                
                if panel_event_handled:
                    dragging_left = False # Prevent camera drag if panel was interacted with
                elif active_text_input_param_key: # Click was outside physics panel (or panel not shown) while input active
                    try:
                        new_val = float(text_input_string)
                        for p_cfg in physics_params_config:
                            if p_cfg["var_name"] == active_text_input_param_key:
                                new_val = max(p_cfg["min_val"], min(p_cfg["max_val"], new_val))
                                break
                        save_param_to_config(active_text_input_param_key, new_val)
                    except ValueError: pass
                    active_text_input_param_key = None
                    text_input_string = ""

            elif event.type == pygame.MOUSEWHEEL:
                mouse_pos = pygame.mouse.get_pos()
                panel_interaction_for_wheel = False
                if show_physics_panel:
                    panel_rect_screen = pygame.Rect(physics_panel_pos[0], physics_panel_pos[1], PHYSICS_PANEL_WIDTH, GAME_SCREEN_HEIGHT + PHYSICS_PANEL_TITLE_BAR_HEIGHT)
                    if panel_rect_screen.collidepoint(mouse_pos): # Mouse wheel over panel
                        panel_interaction_for_wheel = True # Indicate panel interaction
                        tuned_param_with_wheel = False
                        for param in physics_params_config:
                            if "_item_row_rect" in param and param["_item_row_rect"].collidepoint(mouse_pos):
                                current_value = globals().get(param["var_name"], 0.0)
                                p_range = param["max_val"] - param["min_val"]
                                step = p_range * 0.01 
                                if abs(step) < 1e-5 : 
                                    if "f" in param["format_str"]:
                                        decimals = int(param["format_str"].split('.')[1][0]) if '.' in param["format_str"] else 0
                                        step = 10**(-decimals)
                                    else:
                                        step = 0.01 
                                if abs(step) < 1e-9 and abs(p_range) < 1e-9 : step = 0.01 
                                elif abs(step) < 1e-9 : step = p_range * 0.01 if p_range != 0 else 0.01
                                new_value = current_value + event.y * step
                                new_value = max(param["min_val"], min(param["max_val"], new_value))
                                try:
                                    formatted_new_value = param["format_str"].format(new_value)
                                    new_value = float(formatted_new_value)
                                except ValueError:
                                    pass 
                                save_param_to_config(param["var_name"], new_value)
                                tuned_param_with_wheel = True
                                break 
                        if not tuned_param_with_wheel: 
                            # If wheel is over panel but not a specific item, do nothing with zoom
                            pass
                
                if not panel_interaction_for_wheel: # Mouse wheel not over panel, or panel not shown
                    zoom += event.y * 0.1
                    zoom = max(0.3, min(2.5, zoom))
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if is_charging_jump: # If a jump was being charged/boosted
                        is_charging_jump = False
                        # jump_charge_start_time will remain until max duration or landing
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 3:  # Right click
                    dragging_left = False  # Stop dragging when the mouse button is released
                if event.button == 1: # Left mouse button up
                    dragging_physics_panel = False # Stop dragging physics panel
                    dragging_slider_param_key = None # Stop dragging slider
            elif event.type == pygame.MOUSEMOTION:
                if dragging_physics_panel:
                    physics_panel_pos[0] = event.pos[0] - physics_panel_drag_start_offset[0]
                    physics_panel_pos[1] = event.pos[1] - physics_panel_drag_start_offset[1]
                    # Optional: Clamp panel_pos to stay within screen bounds
                    physics_panel_pos[0] = max(0, min(physics_panel_pos[0], SCREEN_WIDTH - PHYSICS_PANEL_WIDTH))
                    physics_panel_pos[1] = max(0, min(physics_panel_pos[1], SCREEN_HEIGHT - (PHYSICS_PANEL_TITLE_BAR_HEIGHT + 20))) # Min height for panel
                elif dragging_left:
                    mpos = pygame.mouse.get_pos()
                    if mpos[1] > TOOLBAR_HEIGHT:
                        dx, dy = mpos[0] - drag_start_left[0], mpos[1] - drag_start_left[1]
                        camera_offset_x += dx; camera_offset_y += dy
                        drag_start_left = mpos
                if dragging_slider_param_key:
                    for param in physics_params_config:
                        if param["var_name"] == dragging_slider_param_key:
                            st_rect = param["_slider_track_rect"] # Screen coordinates
                            
                            click_x_relative_to_track_start = event.pos[0] - st_rect.left
                            click_ratio = click_x_relative_to_track_start / st_rect.width
                            click_ratio = max(0.0, min(1.0, click_ratio))

                            raw_ruler_val = -1000.0 + click_ratio * 2000.0
                            
                            snap_increment = 250.0
                            snapped_ruler_val = round(raw_ruler_val / snap_increment) * snap_increment
                            snapped_ruler_val = max(-1000.0, min(1000.0, snapped_ruler_val))
                            
                            norm_snapped_ratio = (snapped_ruler_val + 1000.0) / 2000.0
                            
                            p_min, p_max = param["min_val"], param["max_val"]
                            actual_value = p_min + norm_snapped_ratio * (p_max - p_min)
                            
                            try:
                                actual_value = float(param["format_str"].format(actual_value))
                            except ValueError: pass
                            actual_value = max(p_min, min(p_max, actual_value))

                            save_param_to_config(param["var_name"], actual_value)
                            break
                # Deactivate slider dragging if mouse button is released (globally, not just for this event type)
                if not pygame.mouse.get_pressed()[0]: # Check if primary mouse button (usually left) is up
                    dragging_slider_param_key = None


        if paused:
            # Draw pause overlay and skip updates
            screen.fill((30, 30, 30))
            pause_text = font_big.render("Paused", True, (255, 255, 255))
            screen.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, SCREEN_HEIGHT//2 - 40))
            hint_text = font.render("Press P to resume", True, (200, 200, 200))
            screen.blit(hint_text, (SCREEN_WIDTH//2 - hint_text.get_width()//2, SCREEN_HEIGHT//2 + 10))
            pygame.display.flip()
            clock.tick(60)
            continue

        light_dir_normalized = normalize_vector(light_direction) # Ensure it's normalized for calcs

        keys = pygame.key.get_pressed()

        # --- Movement Physics - XY Plane using Forces (Adjusted Speed) ---
        current_accel_rate = FAST_ACCEL_RATE if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_ACCEL_RATE
        # Apply multiplier to allow a higher base acceleration
        current_accel_rate *= cfg.get("BASE_SPEED_MULTIPLIER")
        current_max_speed_ups = FAST_MAX_SPEED_UPS if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_MAX_SPEED_UPS
        input_force_x, input_force_y = 0.0, 0.0
        if keys[pygame.K_a]:
            input_force_x = -current_accel_rate
        if keys[pygame.K_d]:
            input_force_x =  current_accel_rate
        if keys[pygame.K_w]:
            input_force_y = -current_accel_rate
        if keys[pygame.K_s]:
            input_force_y =  current_accel_rate
        ground_control_multiplier = 1.2 if is_on_ground else 1.0
        input_force_x *= ground_control_multiplier
        input_force_y *= ground_control_multiplier

        # Use a reduced friction factor for smoothing without over-damping:
        local_friction = 0.015   # decreased from 0.025 to reduce undue slowing
        friction_force_x = local_friction * player_vel[0]
        friction_force_y = local_friction * player_vel[1]

        total_force_x = input_force_x - friction_force_x
        total_force_y = input_force_y - friction_force_y

        # Update velocity using F = ma:
        player_vel[0] += (total_force_x / MASS) * dt
        player_vel[1] += (total_force_y / MASS) * dt
        
        # Calculate current speed before using it 
        current_speed_xy = math.hypot(player_vel[0], player_vel[1])
        
        # Apply stiction/extra friction to help ball come to a complete stop
        if current_speed_xy < cfg.get("STICTION_THRESHOLD"):
            player_vel[0] *= (1 - cfg.get("EXTRA_FRICTION"))
            player_vel[1] *= (1 - cfg.get("EXTRA_FRICTION"))
            # If even smaller, snap to zero
            if current_speed_xy < 0.1:
                player_vel[0] = 0.0
                player_vel[1] = 0.0

        # Clamp XY speed to max value:
        # current_speed_xy already calculated above
        if current_speed_xy > current_max_speed_ups:
            scale = current_max_speed_ups / current_speed_xy
            player_vel[0] *= scale
            player_vel[1] *= scale

        # --- Jump and Vertical Physics ---
        current_time = pygame.time.get_ticks() / 1000.0
        
        # Apply gravity if not firmly on ground
        if not is_on_ground:
            player_vel[2] += GRAVITY_ACCEL * dt
            
            # Jump boost (if charging jump)
            if is_charging_jump and keys[pygame.K_SPACE] and jump_charge_start_time is not None:
                charge_duration = current_time - jump_charge_start_time
                if charge_duration < MAX_JUMP_CHARGE_DURATION:
                    player_vel[2] += JUMP_CHARGE_BOOST_ACCEL_RATE * dt
                    # Squish deepens with charge (visual feedback)
                    charge_progress = charge_duration / MAX_JUMP_CHARGE_DURATION
                    squish_from_charge = SQUISH_ON_JUMP_START - charge_progress * (SQUISH_ON_JUMP_START - MAX_SQUISH_FROM_CHARGE)
                    target_squish = min(target_squish, squish_from_charge)
                else: # Max charge reached
                    is_charging_jump = False

        # Update position (all axes)
        # prev_pos = player_pos_world.copy() # This was unused
        for i in range(3): player_pos_world[i] += player_vel[i] * dt
        
        # --- Ground Collision Detection ---
        player_bottom_z = player_pos_world[2] - current_radius
        ground_surface_z = ground_level_z + 1 # Top of the ground voxels
        
        # Check if player has hit the ground
        if player_bottom_z < ground_surface_z:
            # Store the previous velocity before correction for impact calculation
            impact_velocity = -player_vel[2]  # Capture downward velocity (as positive number)
            
            # Correct position to be exactly on ground
            player_pos_world[2] = ground_surface_z + current_radius
            
            # Handle landing
            if not is_on_ground: # This means it *wasn't* on ground, and now it is
                just_landed_this_frame = True # Set the flag indicating landing this frame
                landing_impact_velocity = impact_velocity
                
                # Calculate impact strength as a factor from 0.0 to 1.0
                impact_factor = min(1.0, max(0.0, (impact_velocity - IMPACT_VELOCITY_THRESHOLD) / 
                                              (MAX_IMPACT_VELOCITY - IMPACT_VELOCITY_THRESHOLD)))
                
                # Scale squish amount based on impact factor
                if impact_velocity > IMPACT_VELOCITY_THRESHOLD:
                    # More forceful impact = more squish (lower value)
                    impact_squish = MIN_SQUISH_ON_LANDING - impact_factor * (MIN_SQUISH_ON_LANDING - MAX_SQUISH_ON_LANDING)
                    target_squish = impact_squish
                    
                    # Apply bounce scaled by impact and coefficient of restitution
                    player_vel[2] = -impact_velocity * COEFFICIENT_OF_RESTITUTION
                    
                    # Visual feedback - squish harder with higher impacts
                    squish_velocity = (target_squish - squish) * 15.0  # Increased for faster response
                else:
                    # Gentle landing
                    player_vel[2] = 0
                    target_squish = 0.98  # Very slight squish
                
                # End any active jump charging
                is_charging_jump = False
            
            # Set ground contact state
            is_on_ground = True
        else:
            # Not in contact with ground
            if is_on_ground and player_vel[2] > 0:  # Moving upward away from ground
                is_on_ground = False
            elif is_on_ground:
                # Small tolerance for ground contact to prevent jitter
                if player_bottom_z > ground_surface_z + GROUND_CONTACT_THRESHOLD:
                    is_on_ground = False
        
        # When firmly on ground and not actively moving, ensure stability
        if is_on_ground:
            if current_speed_xy < REST_VELOCITY_THRESHOLD and not is_charging_jump:
                player_vel[2] = 0  # Cancel any lingering vertical velocity
            
            if abs(player_vel[2]) < 0.1:
                player_vel[2] = 0  # Avoid tiny bounces
        
        # --- Update Squish ---
        if jump_initiated_this_frame:
            target_squish = SQUISH_ON_JUMP_START
        elif just_landed_this_frame:
            target_squish = SQUISH_ON_LANDING if landing_impact_velocity > BOUNCE_THRESHOLD else 0.98
        elif is_charging_jump:
            if keys[pygame.K_SPACE] and jump_charge_start_time is not None:
                charge_duration = current_time - jump_charge_start_time
                if charge_duration < MAX_JUMP_CHARGE_DURATION:
                    progress = charge_duration / MAX_JUMP_CHARGE_DURATION
                    target_squish = SQUISH_ON_JUMP_START - progress * (SQUISH_ON_JUMP_START - MAX_SQUISH_FROM_CHARGE)
                else:
                    target_squish = MAX_SQUISH_FROM_CHARGE
        else:
            # Much faster recovery rate for more responsive feel
            target_squish += (1.0 - target_squish) * 10.0 * dt
         
        # Increase to 10.0 for more responsive spring
        _spring = (target_squish - squish) * 10.0
        _damp   = squish_velocity * SQUISH_DAMPING
        _accel  = _spring - _damp
        squish_velocity += _accel * dt
        squish += squish_velocity * dt
        squish = max(MAX_SQUISH_FROM_CHARGE * 0.95, min(1.05, squish))
        if abs(squish - 1.0) < 0.01 and abs(squish_velocity) < 0.1:
            squish = 1.0
            squish_velocity = 0.0
            if not (jump_initiated_this_frame or just_landed_this_frame or is_charging_jump):
                target_squish = 1.0

        # --- Update True 3D Rolling Rotation via Quaternion ---
        new_player_xy = (player_pos_world[0], player_pos_world[1])
        dx = new_player_xy[0] - prev_player_xy[0]
        dy = new_player_xy[1] - prev_player_xy[1]
        distance = math.hypot(dx, dy)
        
        # Only update rotation if there's significant movement
        # This prevents micro-jitters in rotation when nearly stationary
        if distance > 0.05:
            # Invert roll direction by using (-dy, dx) instead of (dy, -dx)
            axis = (-dy, dx, 0)
            norm = math.hypot(axis[0], axis[1])
            if norm > 0:
                axis = (axis[0]/norm, axis[1]/norm, 0)
                angle = distance / current_radius  # rotation angle in radians
                q_increment = quat_from_axis_angle(axis, angle)
                player_rotation = quat_mult(q_increment, player_rotation)
                
                # Normalize the quaternion occasionally to prevent drift
                quat_mag = math.sqrt(sum(x*x for x in player_rotation))
                if abs(quat_mag - 1.0) > 0.01:
                    player_rotation = tuple(x/quat_mag for x in player_rotation)

        prev_player_xy = new_player_xy

        # --- Drawing ---
        game_surface.fill(BLACK)
        draw_origin_x = origin_x_base + camera_offset_x
        draw_origin_y = origin_y_base + camera_offset_y

        # --- Draw Ground and Grid using Cached Surface ---
        # Re-render cached ground surface only if zoom or camera offset have changed significantly.
        if (cached_ground_surface is None or zoom != cached_ground_zoom or  # Use global zoom
            abs(camera_offset_x - (cached_camera_offset[0] or 0)) > 10 or 
            abs(camera_offset_y - (cached_camera_offset[1] or 0)) > 10):
            cached_ground_surface = render_ground_surface(draw_origin_x, draw_origin_y, zoom, ground_level_z) # Pass global zoom and ground_level_z
            cached_ground_zoom = zoom # Use global zoom
            cached_camera_offset = (camera_offset_x, camera_offset_y)
        # Blit the cached ground surface to game_surface at proper offset.
        game_surface.blit(cached_ground_surface, (0, 0))

        # Draw Player Shadow
        shadow_world_z_on_ground = ground_level_z + 1 # Top surface of ground
        if abs(light_dir_normalized[2]) > 0.01: # Avoid division by zero if light is horizontal
            # Light ray: ShadowPos = PlayerPos - t * LightDirNormalized (if light dir points TO the object)
            # Or: ShadowPos = PlayerPos + t * (-LightDirNormalized) (if light dir points FROM the light source)
            # Let's assume light_direction points FROM the light source.
            # ShadowPos.z = player_pos_world[2] + t * (-light_dir_normalized[2]) = shadow_world_z_on_ground
            # t * (-light_dir_normalized[2]) = shadow_world_z_on_ground - player_pos_world[2]
            # t = (shadow_world_z_on_ground - player_pos_world[2]) / (-light_dir_normalized[2])
            
            # If light_dir_normalized[2] is positive (light from above), t should be positive
            # If light_dir_normalized[2] is negative (light from below), shadow is above or t is negative
            if light_dir_normalized[2] > 0.01: # Light has downward component
                t = (player_pos_world[2] - (current_radius) - shadow_world_z_on_ground) / light_dir_normalized[2]
                shadow_world_x = player_pos_world[0] - t * light_dir_normalized[0]
                shadow_world_y = player_pos_world[1] - t * light_dir_normalized[1]
            else: # Light is horizontal or from below, shadow is complex or not on ground plane
                shadow_world_x = player_pos_world[0] # Default to directly below
                shadow_world_y = player_pos_world[1]
        else: # Light is perfectly horizontal
            shadow_world_x = player_pos_world[0]
            shadow_world_y = player_pos_world[1]

        shadow_proj_x, shadow_proj_y = project_iso(shadow_world_x, shadow_world_y, shadow_world_z_on_ground, zoom)
        shadow_screen_x = int(shadow_proj_x + draw_origin_x)
        shadow_screen_y = int(shadow_proj_y + draw_origin_y)
        height_above_shadow_plane = max(0, (player_pos_world[2] - current_radius) - shadow_world_z_on_ground)
        shadow_alpha = max(0, 120 - height_above_shadow_plane * 8) # Adjusted alpha fade
        shadow_size_factor = max(0.1, 1 - height_above_shadow_plane * 0.05) # Adjusted size fade
        
        shadow_base_width = int(VOXEL_SIZE * current_radius * 0.8 * zoom * shadow_size_factor)
        shadow_base_height = int(VOXEL_SIZE * current_radius * 0.4 * zoom * shadow_size_factor)
        if shadow_alpha > 5 and shadow_base_width > 1 and shadow_base_height > 1:
            shadow_surf = pygame.Surface((shadow_base_width, shadow_base_height), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, shadow_base_width, shadow_base_height))
            game_surface.blit(shadow_surf, (shadow_screen_x - shadow_base_width // 2, shadow_screen_y - shadow_base_height // 2))

        # Draw Player Sphere (voxels relative to player_pos_world)
        temp_player_draw_list = []
        for rel_ix, rel_iy, rel_iz_shape, base_color in player_voxels_shape:
            rotated = quat_rotate_point(player_rotation, (rel_ix, rel_iy, rel_iz_shape))
            scaled = (rotated[0] * (1.0/squish) * PLAYER_SCALE, rotated[1] * (1.0/squish) * PLAYER_SCALE, rotated[2] * squish * PLAYER_SCALE)
            abs_ix = scaled[0] + player_pos_world[0]
            abs_iy = scaled[1] + player_pos_world[1]
            abs_iz = scaled[2] + player_pos_world[2]
            temp_player_draw_list.append({'abs_pos': (abs_ix, abs_iy, abs_iz), 'color': base_color, 'rel_coords': (rel_ix, rel_iy, rel_iz_shape)})

        temp_player_draw_list.sort(key=lambda v: v['abs_pos'][2])
        faces_drawn_count = 0 # For debugging culling effectiveness

        for voxel_data in temp_player_draw_list:
            abs_ix, abs_iy, abs_iz = voxel_data['abs_pos']
            base_color = voxel_data['color']
            
            # Voxel's bottom-left-back corner in world space for face point calculation
            voxel_blb_x, voxel_blb_y, voxel_blb_z = abs_ix - 0.5, abs_iy - 0.5, abs_iz - 0.5

            for face_key, base_normal in FACE_NORMALS.items():
                rotated_normal = quat_rotate_point(player_rotation, base_normal)
                
                # --- Back-face Culling ---
                dot_product_view = (rotated_normal[0] * VIEW_DIRECTION_FOR_CULLING[0] +
                                    rotated_normal[1] * VIEW_DIRECTION_FOR_CULLING[1] +
                                    rotated_normal[2] * VIEW_DIRECTION_FOR_CULLING[2])
                if dot_product_view <= CULLING_THRESHOLD: # If normal is pointing away from camera or too parallel
                    continue
                
                faces_drawn_count +=1
                face_indices = get_voxel_face_points_from_indices(voxel_blb_x, voxel_blb_y, voxel_blb_z, face_key)
                # No need to check 'if face_indices:' as get_voxel_face_points_from_indices always returns points now

                shaded_color = compute_face_color_with_normal(base_color, rotated_normal, light_dir_normalized)
                raw_proj_pts = [project_iso(p[0], p[1], p[2], zoom) for p in face_indices]
                shifted = [(int(p[0] + draw_origin_x), int(p[1] + draw_origin_y)) for p in raw_proj_pts]
                pygame.draw.polygon(game_surface, shaded_color, shifted)

        # --- Draw Toolbar as Clickable UI ---
        toolbar_surface.fill(TOOLBAR_COLOR)
        # Draw light icon (a simple circle) at right side:
        light_icon_rect = pygame.Rect(SCREEN_WIDTH - 50, 5, 40, 30)
        mouse_pos = pygame.mouse.get_pos()
        mouse_over_icon = light_icon_rect.collidepoint(mouse_pos)
        pygame.draw.ellipse(toolbar_surface, WHITE, light_icon_rect, 2)
        if light_mode or mouse_over_icon:
            pygame.draw.ellipse(toolbar_surface, (255, 255, 0) if light_mode else (180, 180, 0), light_icon_rect, 0)

        # Draw state information for debugging
        lt = f"Light: X{light_direction[0]:.1f} Y{light_direction[1]:.1f} Z{light_direction[2]:.1f}"
        t_s = font.render(lt, True, TEXT_COLOR)
        toolbar_surface.blit(t_s, (5, 5))

        fps_text = f"FPS: {current_fps:.0f}" # Display FPS
        fps_s = font.render(fps_text, True, TEXT_COLOR)
        toolbar_surface.blit(fps_s, (SCREEN_WIDTH - 280, 5)) # Adjusted position for FPS

        zt = f"Zoom: {zoom:.2f}x"
        z_s = font.render(zt, True, TEXT_COLOR)
        toolbar_surface.blit(z_s, (SCREEN_WIDTH - 200, 5))

        state_color = (120, 255, 120) if is_on_ground else TEXT_COLOR
        pt = f"Pos: X{player_pos_world[0]:.1f} Y{player_pos_world[1]:.1f} Z{player_pos_world[2]:.1f}"
        p_s = font.render(pt, True, state_color)
        toolbar_surface.blit(p_s, (5, 20))

        st = f"Speed: {current_speed_xy:.1f}  Jump: {'CHARGE' if is_charging_jump else ('ON GROUND' if is_on_ground else 'AIR')}  Squish: {squish:.2f}" # Faces: {faces_drawn_count}"
        s_s = font.render(st, True, TEXT_COLOR)
        toolbar_surface.blit(s_s, (SCREEN_WIDTH - 450, 20)) # Adjusted position

        # --- Draw help overlay if toggled ---
        if show_help:
            help_lines = [
                "Controls:",
                "WASD: Roll/Move",
                "Space: Jump / Hold for higher jump",
                "Shift: Sprint",
                "Mouse Drag: Pan Camera",
                "Mouse Wheel: Zoom",
                "Click Lightbulb: Set Light Source",
                "H: Toggle Help   P: Pause",
                "",
                "Tip: The ball rolls with momentum. Use gentle steering for curves!"
            ]
            help_bg = pygame.Surface((400, 220))
            help_bg.set_alpha(220)
            help_bg.fill((30, 30, 30))
            screen.blit(help_bg, (SCREEN_WIDTH//2 - 200, 80))
            for i, line in enumerate(help_lines):
                txt = font.render(line, True, (255, 255, 180) if i == 0 else (220, 220, 220))
                screen.blit(txt, (SCREEN_WIDTH//2 - 190, 90 + i*24))

        screen.blit(toolbar_surface, (0, 0))
        screen.blit(game_surface, (0, TOOLBAR_HEIGHT))

        # --- Draw Physics Tuning Panel (on top of everything else) ---
        if show_physics_panel:
            # panel_x_pos and panel_y_pos are now taken from global physics_panel_pos
            panel_content_height = GAME_SCREEN_HEIGHT # Height for the scrollable content area
            draw_physics_panel(screen, font, panel_content_height)

        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()