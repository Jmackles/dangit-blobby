import pygame
import math
import game_config as cfg
import time
import sys
import json

pygame.font.init() # Initialize font module

# --- Constants and Config Loading ---
SCREEN_WIDTH = cfg.get("SCREEN_WIDTH")
SCREEN_HEIGHT = cfg.get("SCREEN_HEIGHT")
TOOLBAR_HEIGHT = cfg.get("UI_TOOLBAR_HEIGHT")
GAME_SCREEN_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT
BASE_RADIUS = 6 # Base radius for player shape definition

# Colors
BLACK, WHITE, GREEN_BASE, BROWN = (0,0,0), (255,255,255), (34,139,34), (139,69,19)
TOOLBAR_COLOR, TEXT_COLOR = (50,50,50), (200,200,200)

# Iso & Voxel settings from config
VOXEL_SIZE = cfg.get("VOXEL_SIZE")
ISO_TILE_WIDTH_HALF_BASE = VOXEL_SIZE * 0.866
ISO_TILE_HEIGHT_HALF_BASE = VOXEL_SIZE * 0.5
ISO_Z_FACTOR_BASE = VOXEL_SIZE
GROUND_RANGE = cfg.get("GROUND_RANGE")
GROUND_CACHE_MARGIN = cfg.get("UI_GROUND_CACHE_MARGIN")

# --- Global Game State Variables ---
zoom = 1.0
light_direction = [-0.577, -0.577, 0.577] # Default light
player_rotation = (1.0, 0.0, 0.0, 0.0)   # Quaternion (w, x, y, z)
light_mode = False

# Physics state variables
is_charging_jump = False
jump_charge_start_time = None
squish = 1.0
is_on_ground = False
target_squish = 1.0
squish_velocity = 0.0

# --- Physics Parameters (will be loaded from cfg) ---
# Declare all to be loaded to avoid NameErrors if accessed before main() fully runs load_physics_params
PLAYER_SCALE_cfg = 1.0 # Note: _cfg suffix to distinguish from any potential local 'PLAYER_SCALE'
CULLING_THRESHOLD_cfg = 0.05
BASE_ACCEL_RATE, FAST_ACCEL_RATE, BASE_MAX_SPEED_UPS, FAST_MAX_SPEED_UPS = 0,0,0,0
DAMPING_FACTOR, MASS, GRAVITY_ACCEL, COEFFICIENT_OF_RESTITUTION = 0,0,0,0
INITIAL_JUMP_VELOCITY_UPS, JUMP_CHARGE_BOOST_ACCEL_RATE, MAX_JUMP_CHARGE_DURATION = 0,0,0
BOUNCE_ON_LAND_VELOCITY_UPS, BOUNCE_THRESHOLD, GROUND_CONTACT_THRESHOLD = 0,0,0
REST_VELOCITY_THRESHOLD, elasticity, SQUISH_ON_JUMP_START, SQUISH_ON_LANDING = 0,0,0,0
MAX_SQUISH_FROM_CHARGE, SQUISH_DAMPING, IMPACT_VELOCITY_THRESHOLD = 0,0,0
MAX_IMPACT_VELOCITY, MIN_SQUISH_ON_LANDING, MAX_SQUISH_ON_LANDING = 0,0,0
BOUNCE_SOUND_THRESHOLD, STICTION_THRESHOLD, EXTRA_FRICTION, BASE_SPEED_MULTIPLIER = 0,0,0,0

def load_physics_params_from_config():
    """Loads all physics parameters from the cfg module into their respective global variables."""
    global PLAYER_SCALE_cfg, CULLING_THRESHOLD_cfg, \
           BASE_ACCEL_RATE, FAST_ACCEL_RATE, BASE_MAX_SPEED_UPS, FAST_MAX_SPEED_UPS, \
           DAMPING_FACTOR, MASS, GRAVITY_ACCEL, COEFFICIENT_OF_RESTITUTION, \
           INITIAL_JUMP_VELOCITY_UPS, JUMP_CHARGE_BOOST_ACCEL_RATE, MAX_JUMP_CHARGE_DURATION, \
           BOUNCE_ON_LAND_VELOCITY_UPS, BOUNCE_THRESHOLD, GROUND_CONTACT_THRESHOLD, \
           REST_VELOCITY_THRESHOLD, elasticity, SQUISH_ON_JUMP_START, SQUISH_ON_LANDING, \
           MAX_SQUISH_FROM_CHARGE, SQUISH_DAMPING, IMPACT_VELOCITY_THRESHOLD, \
           MAX_IMPACT_VELOCITY, MIN_SQUISH_ON_LANDING, MAX_SQUISH_ON_LANDING, \
           BOUNCE_SOUND_THRESHOLD, STICTION_THRESHOLD, EXTRA_FRICTION, BASE_SPEED_MULTIPLIER

    PLAYER_SCALE_cfg = cfg.get("PLAYER_SCALE")
    CULLING_THRESHOLD_cfg = cfg.get("CULLING_THRESHOLD")
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
    GROUND_CONTACT_THRESHOLD = cfg.get("GROUND_CONTACT_THRESHOLD")
    REST_VELOCITY_THRESHOLD = cfg.get("REST_VELOCITY_THRESHOLD")
    elasticity = cfg.get("elasticity")
    SQUISH_ON_JUMP_START = cfg.get("SQUISH_ON_JUMP_START")
    SQUISH_ON_LANDING = cfg.get("SQUISH_ON_LANDING")
    MAX_SQUISH_FROM_CHARGE = cfg.get("MAX_SQUISH_FROM_CHARGE")
    SQUISH_DAMPING = cfg.get("SQUISH_DAMPING")
    IMPACT_VELOCITY_THRESHOLD = cfg.get("IMPACT_VELOCITY_THRESHOLD")
    MAX_IMPACT_VELOCITY = cfg.get("MAX_IMPACT_VELOCITY")
    MIN_SQUISH_ON_LANDING = cfg.get("MIN_SQUISH_ON_LANDING")
    MAX_SQUISH_ON_LANDING = cfg.get("MAX_SQUISH_ON_LANDING")
    BOUNCE_SOUND_THRESHOLD = cfg.get("BOUNCE_SOUND_THRESHOLD")
    STICTION_THRESHOLD = cfg.get("STICTION_THRESHOLD")
    EXTRA_FRICTION = cfg.get("EXTRA_FRICTION")
    BASE_SPEED_MULTIPLIER = cfg.get("BASE_SPEED_MULTIPLIER")

# --- Helper Functions ---
def normalize_vector(v): mag = math.sqrt(sum(c*c for c in v)); return tuple(c/mag for c in v) if mag else (0,0,0)
VOXEL_CORNER_OFFSETS = { "iso_top": [(0,0,1),(0,1,1),(1,1,1),(1,0,1)], "iso_bottom": [(1,0,0),(1,1,0),(0,1,0),(0,0,0)], "iso_left_side": [(0,0,0),(0,1,0),(0,1,1),(0,0,1)], "iso_right_side": [(1,0,1),(1,1,1),(1,1,0),(1,0,0)], "iso_front_side": [(0,1,1),(0,1,0),(1,1,0),(1,1,1)], "iso_back_side": [(0,0,1),(1,0,1),(1,0,0),(0,0,0)]}
VIEW_DIRECTION_FOR_CULLING = normalize_vector((1,1,0.8))
FACE_NORMALS = {"iso_top":(0,0,1),"iso_bottom":(0,0,-1),"iso_left_side":(-1,0,0),"iso_right_side":(1,0,0),"iso_front_side":(0,1,0),"iso_back_side":(0,-1,0)}
def project_iso(ix,iy,iz,current_zoom): iso_w,iso_h,iso_z = ISO_TILE_WIDTH_HALF_BASE*current_zoom, ISO_TILE_HEIGHT_HALF_BASE*current_zoom, ISO_Z_FACTOR_BASE*current_zoom; return (ix-iy)*iso_w, (ix+iy)*iso_h - iz*iso_z
def get_voxel_face_points_from_indices(ix,iy,iz,face_key): offsets=VOXEL_CORNER_OFFSETS[face_key]; return [(ix+off[0],iy+off[1],iz+off[2]) for off in offsets]
def compute_face_color_with_normal(base_color,face_normal_world,light_dir_normalized): dot=sum(fn*ld for fn,ld in zip(face_normal_world,light_dir_normalized)); amb=0.45;diff=max(0,dot);bright=amb+(1-amb)*diff; return tuple(min(255,int(c*bright)) for c in base_color)
cached_ground_surface, cached_ground_zoom, cached_camera_offset = None, -1, (None,None)
def render_ground_surface(current_zoom, ground_level_z_val): # Removed draw_origin args
    surface_width = SCREEN_WIDTH + GROUND_CACHE_MARGIN
    surface_height = GAME_SCREEN_HEIGHT + GROUND_CACHE_MARGIN
    surf = pygame.Surface((surface_width, surface_height)); surf.fill(BLACK)
    center_x_on_cache = surface_width // 2
    center_y_on_cache = surface_height // 2
    R = int(GROUND_RANGE * 1.5)
    corners = [(-R,-R,ground_level_z_val),(R,-R,ground_level_z_val),(R,R,ground_level_z_val),(-R,R,ground_level_z_val)]
    proj_corners = [project_iso(cx,cy,cz, current_zoom) for (cx,cy,cz) in corners]
    shifted = [(int(pt[0] + center_x_on_cache), int(pt[1] + center_y_on_cache)) for pt in proj_corners]
    color = compute_face_color_with_normal(BROWN, FACE_NORMALS["iso_top"], light_direction)
    pygame.draw.polygon(surf, color, shifted)
    return surf

# --- Quaternion Functions ---
def quat_from_axis_angle(axis, angle): ax,ay,az=axis; half_angle=angle/2.0; s=math.sin(half_angle); return (math.cos(half_angle),ax*s,ay*s,az*s)
def quat_mult(q1,q2): w1,x1,y1,z1=q1; w2,x2,y2,z2=q2; return (w1*w2-x1*x2-y1*y2-z1*z2, w1*x2+x1*w2+y1*z2-z1*y2, w1*y2-x1*z2+y1*w2+z1*x2, w1*z2+x1*y2-y1*x2+z1*w2)
def quat_conjugate(q): w,x,y,z=q; return (w,-x,-y,-z)
def quat_rotate_point(q,point): p=(0.0,point[0],point[1],point[2]); qc=quat_conjugate(q); p_rot=quat_mult(quat_mult(q,p),qc); return (p_rot[1],p_rot[2],p_rot[3])

# --- Physics Panel State & Config ---
show_physics_panel = False
PHYSICS_PANEL_WIDTH = cfg.get("UI_PHYSICS_PANEL_WIDTH") # Current width
physics_panel_content_height = cfg.get("UI_PHYSICS_PANEL_CONTENT_HEIGHT") # Current content area height
UI_PHYSICS_PANEL_MIN_WIDTH = cfg.get("UI_PHYSICS_PANEL_MIN_WIDTH")
UI_PHYSICS_PANEL_MAX_WIDTH = cfg.get("UI_PHYSICS_PANEL_MAX_WIDTH")
UI_PHYSICS_PANEL_MIN_CONTENT_HEIGHT = cfg.get("UI_PHYSICS_PANEL_MIN_CONTENT_HEIGHT")
UI_PHYSICS_PANEL_MAX_CONTENT_HEIGHT = cfg.get("UI_PHYSICS_PANEL_MAX_CONTENT_HEIGHT")
PHYSICS_PANEL_COLOR = (40, 40, 60, 230)
PHYSICS_PANEL_TEXT_COLOR = (220, 220, 220)
PHYSICS_PANEL_TITLE_BAR_HEIGHT = cfg.get("UI_PHYSICS_PANEL_TITLE_BAR_HEIGHT")
PHYSICS_PANEL_TITLE_COLOR = tuple(cfg.get("UI_PHYSICS_PANEL_TITLE_COLOR"))
PHYSICS_PANEL_BORDER_COLOR = tuple(cfg.get("UI_PHYSICS_PANEL_BORDER_COLOR"))
PHYSICS_PANEL_CLOSE_BTN_SIZE = cfg.get("UI_PHYSICS_PANEL_CLOSE_BTN_SIZE")
PHYSICS_PANEL_CLOSE_BTN_COLOR = tuple(cfg.get("UI_PHYSICS_PANEL_CLOSE_BTN_COLOR"))
PHYSICS_PANEL_CLOSE_BTN_HOVER_COLOR = tuple(cfg.get("UI_PHYSICS_PANEL_CLOSE_BTN_HOVER_COLOR"))
UI_PANEL_RESIZE_HANDLE_SIZE = cfg.get("UI_PANEL_RESIZE_HANDLE_SIZE")
UI_SCROLLBAR_WIDTH = cfg.get("UI_SCROLLBAR_WIDTH")
UI_SCROLLBAR_COLOR = tuple(cfg.get("UI_SCROLLBAR_COLOR"))
UI_SCROLLBAR_HANDLE_COLOR = tuple(cfg.get("UI_SCROLLBAR_HANDLE_COLOR"))
UI_SCROLLBAR_HANDLE_HOVER_COLOR = tuple(cfg.get("UI_SCROLLBAR_HANDLE_HOVER_COLOR"))

physics_panel_pos = list(cfg.get("PHYSICS_PANEL_POS"))
dragging_physics_panel = False; physics_panel_drag_start_offset = (0,0)
dragging_panel_resize = False; panel_resize_drag_start_mouse_pos = (0,0); panel_resize_drag_start_dims = (0,0)
active_text_input_param_key = None; text_input_string = ""
dragging_slider_param_key = None # For Phase 2
physics_panel_scroll = 0; physics_panel_scroll_max = 0
dragging_scrollbar = False; scrollbar_drag_start_mouse_y = 0; scrollbar_drag_start_scroll_y = 0
physics_panel_search = ""; physics_panel_show_only_changed = False
physics_panel_collapsed = False; physics_panel_active_search_box = False
param_flash_times = {}; FLASH_DURATION = 0.3

# physics_params_config list (as defined before)
physics_params_config = [
    {"var_name": "BASE_ACCEL_RATE", "label": "Base Accel Rate", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"var_name": "FAST_ACCEL_RATE", "label": "Fast Accel Rate", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"var_name": "BASE_MAX_SPEED_UPS", "label": "Base Max Speed", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"var_name": "FAST_MAX_SPEED_UPS", "label": "Fast Max Speed", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"var_name": "DAMPING_FACTOR", "label": "Damping Factor", "min_val": 0.0, "max_val": 20.0, "format_str": "{:.2f}"},
    {"var_name": "MASS", "label": "Mass", "min_val": 0.1, "max_val": 20.0, "format_str": "{:.1f}"},
    {"var_name": "STICTION_THRESHOLD", "label": "Stiction Threshold", "min_val": 0.0, "max_val": 5.0, "format_str": "{:.2f}"},
    {"var_name": "EXTRA_FRICTION", "label": "Extra Friction", "min_val": 0.0, "max_val": 0.5, "format_str": "{:.3f}"},
    {"var_name": "BASE_SPEED_MULTIPLIER", "label": "Base Speed Multi", "min_val": 0.1, "max_val": 5.0, "format_str": "{:.2f}"},
    {"var_name": "GRAVITY_ACCEL", "label": "Gravity Accel", "min_val": -100.0, "max_val": -1.0, "format_str": "{:.1f}"},
    {"var_name": "INITIAL_JUMP_VELOCITY_UPS", "label": "Initial Jump Vel.", "min_val": 1.0, "max_val": 50.0, "format_str": "{:.1f}"},
    {"var_name": "JUMP_CHARGE_BOOST_ACCEL_RATE", "label": "Jump Charge Boost", "min_val": 0.0, "max_val": 50.0, "format_str": "{:.1f}"},
    {"var_name": "MAX_JUMP_CHARGE_DURATION", "label": "Max Jump Charge (s)", "min_val": 0.1, "max_val": 3.0, "format_str": "{:.2f}"},
    {"var_name": "COEFFICIENT_OF_RESTITUTION", "label": "Restitution Coeff.", "min_val": 0.0, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "BOUNCE_THRESHOLD", "label": "Bounce Threshold", "min_val": 0.0, "max_val": 20.0, "format_str": "{:.1f}"},
    {"var_name": "BOUNCE_ON_LAND_VELOCITY_UPS", "label": "Min Bounce Vel.", "min_val": 0.0, "max_val": 10.0, "format_str": "{:.2f}"},
    {"var_name": "GROUND_CONTACT_THRESHOLD", "label": "Ground Contact Thr.", "min_val": 0.01, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "REST_VELOCITY_THRESHOLD", "label": "Rest Velocity Thr.", "min_val": 0.01, "max_val": 2.0, "format_str": "{:.2f}"},
    {"var_name": "elasticity", "label": "Squish Elasticity", "min_val": 1.0, "max_val": 50.0, "format_str": "{:.1f}"},
    {"var_name": "SQUISH_ON_JUMP_START", "label": "Squish on Jump", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "SQUISH_ON_LANDING", "label": "Base Squish Land", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "MAX_SQUISH_FROM_CHARGE", "label": "Max Squish (Charge)", "min_val": 0.1, "max_val": 0.9, "format_str": "{:.2f}"},
    {"var_name": "SQUISH_DAMPING", "label": "Squish Damping", "min_val": 0.0, "max_val": 30.0, "format_str": "{:.1f}"},
    {"var_name": "IMPACT_VELOCITY_THRESHOLD", "label": "Impact Vel. Thr.", "min_val": 0.0, "max_val": 20.0, "format_str": "{:.1f}"},
    {"var_name": "MAX_IMPACT_VELOCITY", "label": "Max Impact Vel.", "min_val": 1.0, "max_val": 100.0, "format_str": "{:.1f}"},
    {"var_name": "MIN_SQUISH_ON_LANDING", "label": "Min Squish (Land)", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "MAX_SQUISH_ON_LANDING", "label": "Max Squish (Land)", "min_val": 0.1, "max_val": 1.0, "format_str": "{:.2f}"},
    {"var_name": "PLAYER_SCALE_cfg", "label": "Player Scale", "min_val": 0.1, "max_val": 5.0, "format_str": "{:.2f}"},
    {"var_name": "CULLING_THRESHOLD_cfg", "label": "Culling Threshold", "min_val": -1.0, "max_val": 1.0, "format_str": "{:.3f}"},
]

def save_param_to_config_and_globals(param_name, value):
    if param_name in globals(): globals()[param_name] = value
    cfg.set_param(param_name, value)
    param_flash_times[param_name] = time.time() + FLASH_DURATION
def reset_all_physics_params_to_defaults():
    for param_cfg_item in physics_params_config:
        var_name = param_cfg_item["var_name"]
        default_val = cfg.DEFAULT_CONFIG.get(var_name)
        if default_val is not None:
            save_param_to_config_and_globals(var_name, default_val)
    print("All physics parameters reset to defaults.")
def copy_current_config_to_clipboard():
    current_config_dict = {}
    for p_cfg in physics_params_config:
        current_config_dict[p_cfg["var_name"]] = globals().get(p_cfg["var_name"])
    # Add other non-panel managed settings
    current_config_dict["SCREEN_WIDTH"] = SCREEN_WIDTH
    current_config_dict["SCREEN_HEIGHT"] = SCREEN_HEIGHT
    current_config_dict["PHYSICS_PANEL_POS"] = physics_panel_pos
    current_config_dict["UI_PHYSICS_PANEL_WIDTH"] = PHYSICS_PANEL_WIDTH
    current_config_dict["UI_PHYSICS_PANEL_CONTENT_HEIGHT"] = physics_panel_content_height
    try:
        config_json_string = json.dumps(current_config_dict, indent=4, sort_keys=True)
        if pygame.scrap.get_init(): pygame.scrap.put(pygame.SCRAP_TEXT, config_json_string.encode('utf-8')); print("Current config copied.")
        else: print("Clipboard not init. Config JSON:\n", config_json_string)
    except Exception as e: print(f"Clipboard error: {e}. Config JSON:\n", json.dumps(current_config_dict, indent=4, sort_keys=True))

def draw_physics_panel_ui(screen_surf, font_small, font_medium):
    global physics_panel_scroll, physics_panel_scroll_max, physics_panel_search, \
           physics_panel_show_only_changed, physics_panel_collapsed, \
           active_text_input_param_key, text_input_string, dragging_slider_param_key, \
           physics_panel_active_search_box, \
           PHYSICS_PANEL_WIDTH, physics_panel_content_height # These can now change

    panel_x, panel_y = physics_panel_pos
    padding = 10
    current_time_for_flash = time.time()

    header_h = PHYSICS_PANEL_TITLE_BAR_HEIGHT
    search_box_h = 26; buttons_h = 22; spacing_after_search = 4; spacing_after_buttons = padding
    controls_section_h = search_box_h + spacing_after_search + buttons_h + spacing_after_buttons
    
    actual_content_area_h = 0 if physics_panel_collapsed else physics_panel_content_height
    total_panel_h = header_h + controls_section_h + actual_content_area_h
    
    panel_surface = pygame.Surface((PHYSICS_PANEL_WIDTH, total_panel_h), pygame.SRCALPHA)
    panel_surface.fill((0,0,0,0))

    title_bar_rect = pygame.Rect(0, 0, PHYSICS_PANEL_WIDTH, header_h)
    pygame.draw.rect(panel_surface, PHYSICS_PANEL_TITLE_COLOR, title_bar_rect)
    title_text_surf = font_medium.render("Physics Controls (T)", True, PHYSICS_PANEL_TEXT_COLOR)
    panel_surface.blit(title_text_surf, (padding, (header_h - title_text_surf.get_height()) // 2))

    close_btn_rect_rel = pygame.Rect(PHYSICS_PANEL_WIDTH - PHYSICS_PANEL_CLOSE_BTN_SIZE - 5,
                                  (header_h - PHYSICS_PANEL_CLOSE_BTN_SIZE) // 2,
                                  PHYSICS_PANEL_CLOSE_BTN_SIZE, PHYSICS_PANEL_CLOSE_BTN_SIZE)
    mx_abs, my_abs = pygame.mouse.get_pos()
    close_btn_abs_coords = close_btn_rect_rel.move(panel_x, panel_y)
    hover_close = close_btn_abs_coords.collidepoint(mx_abs,my_abs)
    pygame.draw.rect(panel_surface, PHYSICS_PANEL_CLOSE_BTN_HOVER_COLOR if hover_close else PHYSICS_PANEL_CLOSE_BTN_COLOR, close_btn_rect_rel, border_radius=3)
    x_font = pygame.font.Font(None, PHYSICS_PANEL_CLOSE_BTN_SIZE + 4)
    x_surf = x_font.render("×", True, WHITE)
    panel_surface.blit(x_surf, (close_btn_rect_rel.x + (close_btn_rect_rel.width - x_surf.get_width()) // 2,
                               close_btn_rect_rel.y + (close_btn_rect_rel.height - x_surf.get_height()) // 2 - 2))

    current_y_on_panel = header_h + padding // 2
    search_box_rect_rel = pygame.Rect(padding, current_y_on_panel, PHYSICS_PANEL_WIDTH - 2 * padding - 95, search_box_h)
    pygame.draw.rect(panel_surface, (30,30,40) if physics_panel_active_search_box else (20,20,30), search_box_rect_rel, border_radius=3)
    search_border_c = (200,200,255) if physics_panel_active_search_box else (100,100,120)
    pygame.draw.rect(panel_surface, search_border_c, search_box_rect_rel, 1, border_radius=3)
    search_text = physics_panel_search + ("|" if physics_panel_active_search_box and int(current_time_for_flash*2)%2==0 else "")
    if not physics_panel_search and not physics_panel_active_search_box: search_text = "Search..."
    search_surf = font_small.render(search_text, True, PHYSICS_PANEL_TEXT_COLOR if physics_panel_search or physics_panel_active_search_box else (120,120,120))
    panel_surface.blit(search_surf, (search_box_rect_rel.x + 5, search_box_rect_rel.y + (search_box_rect_rel.height - search_surf.get_height()) // 2))

    changed_btn_width = 85
    changed_btn_rect_rel = pygame.Rect(PHYSICS_PANEL_WIDTH - padding - changed_btn_width, current_y_on_panel, changed_btn_width, search_box_h)
    changed_btn_abs_coords = changed_btn_rect_rel.move(panel_x, panel_y)
    hover_changed = changed_btn_abs_coords.collidepoint(mx_abs,my_abs)
    changed_bg_col = (90,130,190) if hover_changed else ((70,100,150) if physics_panel_show_only_changed else (50,70,100))
    pygame.draw.rect(panel_surface, changed_bg_col, changed_btn_rect_rel, border_radius=3)
    changed_text_surf = font_small.render("Changed", True, WHITE if physics_panel_show_only_changed else (180,180,180))
    panel_surface.blit(changed_text_surf, (changed_btn_rect_rel.centerx - changed_text_surf.get_width()//2,
                                         changed_btn_rect_rel.centery - changed_text_surf.get_height()//2))
    current_y_on_panel += search_box_h + spacing_after_search

    btn_spacing = 4; num_buttons = 3
    btn_w = (PHYSICS_PANEL_WIDTH - 2 * padding - (num_buttons - 1) * btn_spacing) // num_buttons
    collapse_btn_rect_rel = pygame.Rect(padding, current_y_on_panel, btn_w, buttons_h)
    copy_btn_rect_rel = pygame.Rect(collapse_btn_rect_rel.right + btn_spacing, current_y_on_panel, btn_w, buttons_h)
    reset_btn_rect_rel = pygame.Rect(copy_btn_rect_rel.right + btn_spacing, current_y_on_panel, btn_w, buttons_h)
    hover_collapse = collapse_btn_rect_rel.move(panel_x,panel_y).collidepoint(mx_abs,my_abs)
    hover_copy = copy_btn_rect_rel.move(panel_x,panel_y).collidepoint(mx_abs,my_abs)
    hover_reset = reset_btn_rect_rel.move(panel_x,panel_y).collidepoint(mx_abs,my_abs)
    pygame.draw.rect(panel_surface, (90,130,190) if hover_collapse else (70,100,150), collapse_btn_rect_rel, border_radius=3)
    pygame.draw.rect(panel_surface, (90,130,190) if hover_copy else (70,100,150), copy_btn_rect_rel, border_radius=3)
    pygame.draw.rect(panel_surface, (190,110,110) if hover_reset else (150,80,80), reset_btn_rect_rel, border_radius=3)
    collapse_text_str = "Expand" if physics_panel_collapsed else "Collapse"
    collapse_surf = font_small.render(collapse_text_str, True, WHITE); copy_surf = font_small.render("Copy Config", True, WHITE); reset_surf = font_small.render("Reset All", True, WHITE)
    panel_surface.blit(collapse_surf, (collapse_btn_rect_rel.centerx - collapse_surf.get_width()//2, collapse_btn_rect_rel.centery - collapse_surf.get_height()//2))
    panel_surface.blit(copy_surf, (copy_btn_rect_rel.centerx - copy_surf.get_width()//2, copy_btn_rect_rel.centery - copy_surf.get_height()//2))
    panel_surface.blit(reset_surf, (reset_btn_rect_rel.centerx - reset_surf.get_width()//2, reset_btn_rect_rel.centery - reset_surf.get_height()//2))
    current_y_on_panel += buttons_h + spacing_after_buttons

    if not physics_panel_collapsed:
        param_list_area_y_on_panel = current_y_on_panel
        param_list_area_h = actual_content_area_h
        param_list_render_width = PHYSICS_PANEL_WIDTH - (UI_SCROLLBAR_WIDTH + padding//2 if physics_panel_scroll_max > 0 else 0)
        
        # Placeholder: Simulate total height of items for scrollbar calculation
        # In Phase 2, this will be the actual sum of item heights.
        simulated_total_item_height = 0
        # For now, let's assume each item (label + slider + ruler) takes about 60 pixels.
        # Filter params first for accurate count.
        filtered_params_for_height_calc = [p for p in physics_params_config if not (physics_panel_search and physics_panel_search.lower() not in p["label"].lower()) and not (physics_panel_show_only_changed and math.isclose(globals().get(p["var_name"],0), cfg.DEFAULT_CONFIG.get(p["var_name"],0)))]
        simulated_total_item_height = len(filtered_params_for_height_calc) * 60 # Rough estimate
        
        physics_panel_scroll_max = max(0, simulated_total_item_height - param_list_area_h)
        physics_panel_scroll = max(0, min(physics_panel_scroll, physics_panel_scroll_max))

        param_list_subsurface = pygame.Surface((param_list_render_width, param_list_area_h), pygame.SRCALPHA)
        param_list_subsurface.fill(PHYSICS_PANEL_COLOR)

        placeholder_y_offset = -physics_panel_scroll
        for i in range(len(filtered_params_for_height_calc)): # Use count of filtered items
            item_h = 55; item_spacing = 5 # Placeholder item height
            ph_rect = pygame.Rect(padding//2, placeholder_y_offset, param_list_render_width - padding, item_h)
            if ph_rect.bottom > 0 and ph_rect.top < param_list_area_h:
                pygame.draw.rect(param_list_subsurface, (50 + i*2 % 205, 50 + i*3 % 205, 70 + i*4 % 185), ph_rect, border_radius=2)
                text_surf = font_small.render(f"Param: {filtered_params_for_height_calc[i]['label']}", True, WHITE)
                param_list_subsurface.blit(text_surf, (ph_rect.x + 5, ph_rect.y + 5))
            placeholder_y_offset += item_h + item_spacing
        
        panel_surface.blit(param_list_subsurface, (0, param_list_area_y_on_panel))

        if physics_panel_scroll_max > 0:
            scrollbar_track_h = param_list_area_h
            scrollbar_x = PHYSICS_PANEL_WIDTH - UI_SCROLLBAR_WIDTH - padding // 2
            pygame.draw.rect(panel_surface, UI_SCROLLBAR_COLOR, (scrollbar_x, param_list_area_y_on_panel, UI_SCROLLBAR_WIDTH, scrollbar_track_h), border_radius=UI_SCROLLBAR_WIDTH//2)
            handle_h_min = 20
            handle_h = max(handle_h_min, scrollbar_track_h * (param_list_area_h / simulated_total_item_height) if simulated_total_item_height > 0 else handle_h_min)
            handle_h = min(handle_h, scrollbar_track_h)
            scroll_ratio = physics_panel_scroll / physics_panel_scroll_max if physics_panel_scroll_max > 0 else 0
            handle_y_on_track = scroll_ratio * (scrollbar_track_h - handle_h)
            handle_rect_rel = pygame.Rect(scrollbar_x, param_list_area_y_on_panel + handle_y_on_track, UI_SCROLLBAR_WIDTH, handle_h)
            handle_abs_coords = handle_rect_rel.move(panel_x, panel_y)
            hover_scrollbar_handle = handle_abs_coords.collidepoint(mx_abs, my_abs)
            handle_col = UI_SCROLLBAR_HANDLE_HOVER_COLOR if hover_scrollbar_handle or dragging_scrollbar else UI_SCROLLBAR_HANDLE_COLOR
            pygame.draw.rect(panel_surface, handle_col, handle_rect_rel, border_radius=UI_SCROLLBAR_WIDTH//2)

    resize_handle_rect_rel = pygame.Rect(PHYSICS_PANEL_WIDTH - UI_PANEL_RESIZE_HANDLE_SIZE,
                                       total_panel_h - UI_PANEL_RESIZE_HANDLE_SIZE,
                                       UI_PANEL_RESIZE_HANDLE_SIZE, UI_PANEL_RESIZE_HANDLE_SIZE)
    resize_handle_abs_coords = resize_handle_rect_rel.move(panel_x, panel_y)
    hover_resize = resize_handle_abs_coords.collidepoint(mx_abs, my_abs)
    rh_points = [(resize_handle_rect_rel.left, resize_handle_rect_rel.bottom), (resize_handle_rect_rel.right, resize_handle_rect_rel.bottom), (resize_handle_rect_rel.right, resize_handle_rect_rel.top)]
    pygame.draw.polygon(panel_surface, (150,150,180) if hover_resize or dragging_panel_resize else (100,100,120), rh_points)

    pygame.draw.rect(panel_surface, PHYSICS_PANEL_BORDER_COLOR, (0,0,PHYSICS_PANEL_WIDTH, total_panel_h), 1)
    screen_surf.blit(panel_surface, physics_panel_pos)

# --- Main Game Loop ---
def main():
    global SCREEN_WIDTH, SCREEN_HEIGHT, GAME_SCREEN_HEIGHT, PLAYER_SCALE_cfg, CULLING_THRESHOLD_cfg
    global zoom, light_direction, player_rotation, light_mode
    global squish, jump_charge_start_time, is_charging_jump, is_on_ground, target_squish, squish_velocity
    global cached_ground_surface, cached_ground_zoom, cached_camera_offset
    global show_physics_panel, physics_panel_pos, dragging_physics_panel, physics_panel_drag_start_offset, \
           dragging_panel_resize, panel_resize_drag_start_mouse_pos, panel_resize_drag_start_dims
    global active_text_input_param_key, text_input_string # dragging_slider_param_key (for phase 2)
    global physics_panel_scroll, physics_panel_scroll_max, physics_panel_collapsed, physics_panel_search, \
           physics_panel_show_only_changed, physics_panel_active_search_box, \
           dragging_scrollbar, scrollbar_drag_start_mouse_y, scrollbar_drag_start_scroll_y
    global PHYSICS_PANEL_WIDTH, physics_panel_content_height

    pygame.init()
    load_physics_params_from_config() # Load all params into globals

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
    pygame.display.set_caption("Voxel World - Panel Resizing & Scrolling")
    try:
        if not pygame.scrap.get_init(): pygame.scrap.init()
        if not pygame.scrap.get_init(): print("Warning: Pygame scrap (clipboard) could not be initialized.")
    except Exception as e: print(f"Clipboard init error: {e}")

    game_surface = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT), pygame.SRCALPHA)
    toolbar_surface = pygame.Surface((SCREEN_WIDTH, TOOLBAR_HEIGHT))
    
    clock = pygame.time.Clock()
    font_small = pygame.font.Font(None, 20); font_medium = pygame.font.Font(None, 24); font_large = pygame.font.Font(None, 48)

    player_voxels_shape = []
    current_radius = BASE_RADIUS * PLAYER_SCALE_cfg
    for i in range(-BASE_RADIUS,BASE_RADIUS+1):
        for j in range(-BASE_RADIUS,BASE_RADIUS+1):
            for k in range(-BASE_RADIUS,BASE_RADIUS+1):
                if (i+0.5)**2+(j+0.5)**2+(k+0.5)**2 <= BASE_RADIUS**2*1.05: player_voxels_shape.append((i,j,k,GREEN_BASE))
    player_voxels_shape.sort(key=lambda v:(v[2],v[1],v[0]))
    ground_level_z = -1
    origin_x_base, origin_y_base = SCREEN_WIDTH//2, GAME_SCREEN_HEIGHT//2
    camera_offset_x, camera_offset_y = 0,0
    dragging_camera, drag_start_camera = False, (0,0)
    player_pos_world = [0.0,0.0,float(current_radius if current_radius>0 else 1.0)]
    player_vel = [0.0,0.0,0.0]; prev_player_xy = (player_pos_world[0],player_pos_world[1])
    show_help, paused, current_fps = False,False,0.0
    jump_initiated_this_frame, just_landed_this_frame, landing_impact_velocity = False,False,0.0

    panel_total_h_approx = PHYSICS_PANEL_TITLE_BAR_HEIGHT + physics_panel_content_height + 75
    physics_panel_pos[0] = max(0, min(physics_panel_pos[0], SCREEN_WIDTH - PHYSICS_PANEL_WIDTH))
    physics_panel_pos[1] = max(TOOLBAR_HEIGHT, min(physics_panel_pos[1], SCREEN_HEIGHT - panel_total_h_approx))

    running = True
    while running:
        dt = min(clock.get_time()/1000.0, 0.1); current_time = time.time(); current_fps = clock.get_fps()
        current_radius = BASE_RADIUS * PLAYER_SCALE_cfg
        if not pygame.mouse.get_pressed()[2]: dragging_camera = False
        jump_initiated_this_frame, just_landed_this_frame = False, False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.VIDEORESIZE:
                SCREEN_WIDTH,SCREEN_HEIGHT=event.w,event.h; GAME_SCREEN_HEIGHT=SCREEN_HEIGHT-TOOLBAR_HEIGHT
                screen=pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.RESIZABLE)
                try: game_surface=pygame.Surface((SCREEN_WIDTH,GAME_SCREEN_HEIGHT),pygame.SRCALPHA); toolbar_surface=pygame.Surface((SCREEN_WIDTH,TOOLBAR_HEIGHT))
                except pygame.error: game_surface=pygame.Surface((max(100,SCREEN_WIDTH),max(100,GAME_SCREEN_HEIGHT)),pygame.SRCALPHA); toolbar_surface=pygame.Surface((max(100,SCREEN_WIDTH),TOOLBAR_HEIGHT))
                origin_x_base,origin_y_base=SCREEN_WIDTH//2,GAME_SCREEN_HEIGHT//2
                PHYSICS_PANEL_WIDTH=max(UI_PHYSICS_PANEL_MIN_WIDTH,min(PHYSICS_PANEL_WIDTH,UI_PHYSICS_PANEL_MAX_WIDTH,SCREEN_WIDTH-20))
                physics_panel_content_height=max(UI_PHYSICS_PANEL_MIN_CONTENT_HEIGHT,min(physics_panel_content_height,UI_PHYSICS_PANEL_MAX_CONTENT_HEIGHT,SCREEN_HEIGHT-TOOLBAR_HEIGHT-PHYSICS_PANEL_TITLE_BAR_HEIGHT-100))
                panel_h_approx=PHYSICS_PANEL_TITLE_BAR_HEIGHT+physics_panel_content_height+75
                physics_panel_pos[0]=max(0,min(physics_panel_pos[0],SCREEN_WIDTH-PHYSICS_PANEL_WIDTH))
                physics_panel_pos[1]=max(TOOLBAR_HEIGHT,min(physics_panel_pos[1],SCREEN_HEIGHT-panel_h_approx))
                cfg.set_param("SCREEN_WIDTH",SCREEN_WIDTH); cfg.set_param("SCREEN_HEIGHT",SCREEN_HEIGHT); cached_ground_surface=None
            
            panel_event_consumed = False
            if show_physics_panel:
                mouse_abs_x, mouse_abs_y = event.pos if hasattr(event,'pos') else pygame.mouse.get_pos()
                panel_header_h = PHYSICS_PANEL_TITLE_BAR_HEIGHT
                panel_controls_h = 26+4+22+10
                panel_current_total_h = panel_header_h + panel_controls_h + (0 if physics_panel_collapsed else physics_panel_content_height)
                close_btn_abs_rect = pygame.Rect(physics_panel_pos[0]+PHYSICS_PANEL_WIDTH-PHYSICS_PANEL_CLOSE_BTN_SIZE-5, physics_panel_pos[1]+(panel_header_h-PHYSICS_PANEL_CLOSE_BTN_SIZE)//2, PHYSICS_PANEL_CLOSE_BTN_SIZE,PHYSICS_PANEL_CLOSE_BTN_SIZE)
                title_bar_abs_rect = pygame.Rect(physics_panel_pos[0],physics_panel_pos[1],PHYSICS_PANEL_WIDTH,panel_header_h)
                resize_handle_abs_rect = pygame.Rect(physics_panel_pos[0]+PHYSICS_PANEL_WIDTH-UI_PANEL_RESIZE_HANDLE_SIZE, physics_panel_pos[1]+panel_current_total_h-UI_PANEL_RESIZE_HANDLE_SIZE, UI_PANEL_RESIZE_HANDLE_SIZE,UI_PANEL_RESIZE_HANDLE_SIZE)
                param_list_abs_y_start = physics_panel_pos[1]+panel_header_h+panel_controls_h
                param_list_abs_h = 0 if physics_panel_collapsed else physics_panel_content_height
                scrollbar_track_abs_rect, scrollbar_handle_abs_rect = None,None
                if not physics_panel_collapsed and physics_panel_scroll_max > 0 and param_list_abs_h > 0: # Ensure param_list_abs_h is positive
                    scrollbar_x_abs = physics_panel_pos[0]+PHYSICS_PANEL_WIDTH-UI_SCROLLBAR_WIDTH-10//2
                    scrollbar_track_abs_rect = pygame.Rect(scrollbar_x_abs,param_list_abs_y_start,UI_SCROLLBAR_WIDTH,param_list_abs_h)
                    sim_total_h = param_list_abs_h + 300 # Placeholder
                    handle_h = max(20, param_list_abs_h*(param_list_abs_h/sim_total_h) if sim_total_h > 0 else 20)
                    handle_h = min(handle_h, param_list_abs_h)
                    scroll_ratio = physics_panel_scroll/physics_panel_scroll_max if physics_panel_scroll_max > 0 else 0
                    handle_y_on_track = scroll_ratio*(param_list_abs_h-handle_h)
                    scrollbar_handle_abs_rect = pygame.Rect(scrollbar_x_abs,param_list_abs_y_start+handle_y_on_track,UI_SCROLLBAR_WIDTH,handle_h)

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if close_btn_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): show_physics_panel=False; cfg.set_param("PHYSICS_PANEL_POS",physics_panel_pos); cfg.set_param("UI_PHYSICS_PANEL_WIDTH",PHYSICS_PANEL_WIDTH); cfg.set_param("UI_PHYSICS_PANEL_CONTENT_HEIGHT",physics_panel_content_height); active_text_input_param_key=None; physics_panel_active_search_box=False; panel_event_consumed=True
                    elif resize_handle_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): dragging_panel_resize=True; panel_resize_drag_start_mouse_pos=(mouse_abs_x,mouse_abs_y); panel_resize_drag_start_dims=(PHYSICS_PANEL_WIDTH,physics_panel_content_height); panel_event_consumed=True
                    elif scrollbar_handle_abs_rect and scrollbar_handle_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): dragging_scrollbar=True; scrollbar_drag_start_mouse_y=mouse_abs_y; scrollbar_drag_start_scroll_y=physics_panel_scroll; panel_event_consumed=True
                    elif scrollbar_track_abs_rect and scrollbar_track_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): relative_y_on_track=mouse_abs_y-scrollbar_track_abs_rect.top; scroll_ratio_clicked=relative_y_on_track/scrollbar_track_abs_rect.height if scrollbar_track_abs_rect.height > 0 else 0; physics_panel_scroll=scroll_ratio_clicked*physics_panel_scroll_max; physics_panel_scroll=max(0,min(physics_panel_scroll,physics_panel_scroll_max)); panel_event_consumed=True
                    elif title_bar_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): dragging_physics_panel=True; physics_panel_drag_start_offset=(mouse_abs_x-physics_panel_pos[0],mouse_abs_y-physics_panel_pos[1]); panel_event_consumed=True
                    else: # Check other panel buttons (simplified)
                        # This needs to map to the rects drawn in draw_physics_panel_ui
                        # Example for search box:
                        search_box_rel = pygame.Rect(10, panel_header_h + 10//2, PHYSICS_PANEL_WIDTH - 2*10 - 95, 26)
                        if search_box_rel.move(physics_panel_pos[0], physics_panel_pos[1]).collidepoint(mouse_abs_x, mouse_abs_y):
                            physics_panel_active_search_box = True; active_text_input_param_key = None; panel_event_consumed = True
                        # ... similar checks for "Changed", "Collapse", "Copy", "Reset" ...
                        # If click is within panel but not on a specific control:
                        elif pygame.Rect(physics_panel_pos[0], physics_panel_pos[1], PHYSICS_PANEL_WIDTH, panel_current_total_h).collidepoint(mouse_abs_x, mouse_abs_y):
                            if active_text_input_param_key: active_text_input_param_key = None; text_input_string = ""
                            if physics_panel_active_search_box: physics_panel_active_search_box = False
                            panel_event_consumed = True
                elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                    if dragging_panel_resize: dragging_panel_resize=False; cfg.set_param("UI_PHYSICS_PANEL_WIDTH",PHYSICS_PANEL_WIDTH); cfg.set_param("UI_PHYSICS_PANEL_CONTENT_HEIGHT",physics_panel_content_height)
                    dragging_physics_panel=False; dragging_scrollbar=False
                elif event.type == pygame.MOUSEMOTION:
                    if dragging_panel_resize: dx,dy=mouse_abs_x-panel_resize_drag_start_mouse_pos[0],mouse_abs_y-panel_resize_drag_start_mouse_pos[1]; PHYSICS_PANEL_WIDTH=panel_resize_drag_start_dims[0]+dx; physics_panel_content_height=panel_resize_drag_start_dims[1]+dy; PHYSICS_PANEL_WIDTH=max(UI_PHYSICS_PANEL_MIN_WIDTH,min(PHYSICS_PANEL_WIDTH,UI_PHYSICS_PANEL_MAX_WIDTH)); physics_panel_content_height=max(UI_PHYSICS_PANEL_MIN_CONTENT_HEIGHT,min(physics_panel_content_height,UI_PHYSICS_PANEL_MAX_CONTENT_HEIGHT)); cached_ground_surface=None; panel_event_consumed=True
                    elif dragging_physics_panel: physics_panel_pos[0]=mouse_abs_x-physics_panel_drag_start_offset[0]; physics_panel_pos[1]=mouse_abs_y-physics_panel_drag_start_offset[1]; panel_h_approx=panel_header_h+physics_panel_content_height+75; physics_panel_pos[0]=max(0,min(physics_panel_pos[0],SCREEN_WIDTH-PHYSICS_PANEL_WIDTH)); physics_panel_pos[1]=max(TOOLBAR_HEIGHT,min(physics_panel_pos[1],SCREEN_HEIGHT-panel_h_approx)); panel_event_consumed=True
                    elif dragging_scrollbar and scrollbar_track_abs_rect and scrollbar_track_abs_rect.height > 0: mouse_y_delta=mouse_abs_y-scrollbar_drag_start_mouse_y; scroll_delta_ratio=mouse_y_delta/scrollbar_track_abs_rect.height; physics_panel_scroll=scrollbar_drag_start_scroll_y+scroll_delta_ratio*physics_panel_scroll_max; physics_panel_scroll=max(0,min(physics_panel_scroll,physics_panel_scroll_max)); panel_event_consumed=True
                elif event.type == pygame.MOUSEWHEEL and not physics_panel_collapsed:
                    param_list_content_abs_rect = pygame.Rect(physics_panel_pos[0],param_list_abs_y_start,PHYSICS_PANEL_WIDTH,param_list_abs_h)
                    if param_list_content_abs_rect.collidepoint(mouse_abs_x,mouse_abs_y): physics_panel_scroll-=event.y*30; physics_panel_scroll=max(0,min(physics_panel_scroll,physics_panel_scroll_max)); panel_event_consumed=True
                elif event.type == pygame.KEYDOWN and (physics_panel_active_search_box): # or active_text_input_param_key
                    if physics_panel_active_search_box:
                        if event.key==pygame.K_ESCAPE: physics_panel_active_search_box=False; physics_panel_search=""
                        elif event.key==pygame.K_BACKSPACE: physics_panel_search=physics_panel_search[:-1]
                        elif event.key==pygame.K_RETURN: physics_panel_active_search_box=False
                        else: physics_panel_search+=event.unicode
                        physics_panel_scroll=0
                    panel_event_consumed=True
            if panel_event_consumed: continue

            # General game event handling (as before)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h: show_help = not show_help
                elif event.key == pygame.K_p: paused = not paused
                elif event.key == pygame.K_t:
                    show_physics_panel = not show_physics_panel
                    if not show_physics_panel: cfg.set_param("PHYSICS_PANEL_POS",physics_panel_pos); cfg.set_param("UI_PHYSICS_PANEL_WIDTH",PHYSICS_PANEL_WIDTH); cfg.set_param("UI_PHYSICS_PANEL_CONTENT_HEIGHT",physics_panel_content_height)
                    else: panel_h_approx=PHYSICS_PANEL_TITLE_BAR_HEIGHT+physics_panel_content_height+75; physics_panel_pos[0]=max(0,min(physics_panel_pos[0],SCREEN_WIDTH-PHYSICS_PANEL_WIDTH)); physics_panel_pos[1]=max(TOOLBAR_HEIGHT,min(physics_panel_pos[1],SCREEN_HEIGHT-panel_h_approx))
                elif event.key == pygame.K_ESCAPE:
                    if show_physics_panel: show_physics_panel=False; cfg.set_param("PHYSICS_PANEL_POS",physics_panel_pos); cfg.set_param("UI_PHYSICS_PANEL_WIDTH",PHYSICS_PANEL_WIDTH); cfg.set_param("UI_PHYSICS_PANEL_CONTENT_HEIGHT",physics_panel_content_height)
                    elif show_help: show_help=False
                elif event.key == pygame.K_c: camera_offset_x,camera_offset_y,zoom=0,0,1.0; cached_ground_surface=None
                elif event.key == pygame.K_m: light_mode = not light_mode
                elif event.key == pygame.K_SPACE:
                    if is_on_ground and not is_charging_jump: player_vel[2]=INITIAL_JUMP_VELOCITY_UPS; is_on_ground=False; is_charging_jump=True; jump_charge_start_time=current_time; jump_initiated_this_frame=True; target_squish=SQUISH_ON_JUMP_START
            elif event.type == pygame.KEYUP and event.key == pygame.K_SPACE and is_charging_jump: is_charging_jump=False; jump_charge_start_time=None
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 3 and event.pos[1] > TOOLBAR_HEIGHT: dragging_camera=True; drag_start_camera=(event.pos[0]-camera_offset_x,event.pos[1]-camera_offset_y)
                elif event.button == 1 and light_mode and event.pos[1] > TOOLBAR_HEIGHT: light_dir_x=event.pos[0]-SCREEN_WIDTH//2; light_dir_y=event.pos[1]-GAME_SCREEN_HEIGHT//2; light_direction=normalize_vector([-light_dir_x,-light_dir_y,200]); light_mode=False; cached_ground_surface=None
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 3: dragging_camera=False
            elif event.type == pygame.MOUSEMOTION and dragging_camera and event.pos[1] > TOOLBAR_HEIGHT: camera_offset_x=event.pos[0]-drag_start_camera[0]; camera_offset_y=event.pos[1]-drag_start_camera[1]; cached_ground_surface=None
            elif event.type == pygame.MOUSEWHEEL: zoom_factor=1.1 if event.y>0 else 1/1.1; zoom*=zoom_factor; zoom=max(0.1,min(zoom,5.0)); cached_ground_surface=None

        if not paused:
            # --- Full Physics Update (using global parameters) ---
            keys = pygame.key.get_pressed()
            accel_input = [0.0, 0.0]
            current_accel_rate_val = FAST_ACCEL_RATE if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_ACCEL_RATE
            current_max_speed_val = FAST_MAX_SPEED_UPS if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_MAX_SPEED_UPS
            current_max_speed_val *= BASE_SPEED_MULTIPLIER
            if keys[pygame.K_w]: accel_input[1] -= 1
            if keys[pygame.K_s]: accel_input[1] += 1
            if keys[pygame.K_a]: accel_input[0] -= 1
            if keys[pygame.K_d]: accel_input[0] += 1
            accel_mag = math.hypot(accel_input[0], accel_input[1])
            if accel_mag > 0: accel_input = [ (a / accel_mag) * current_accel_rate_val for a in accel_input]
            else: accel_input = [0.0, 0.0]
            player_vel[0] += accel_input[0] * dt; player_vel[1] += accel_input[1] * dt
            speed_xy = math.hypot(player_vel[0], player_vel[1])
            if speed_xy > 0:
                damping_force_x = -player_vel[0] / speed_xy * DAMPING_FACTOR
                damping_force_y = -player_vel[1] / speed_xy * DAMPING_FACTOR
                player_vel[0] += damping_force_x * dt; player_vel[1] += damping_force_y * dt
            if accel_mag == 0:
                player_vel[0] *= (1.0 - EXTRA_FRICTION); player_vel[1] *= (1.0 - EXTRA_FRICTION)
                if speed_xy < STICTION_THRESHOLD: player_vel[0] = 0.0; player_vel[1] = 0.0
            current_speed_xy_check = math.hypot(player_vel[0], player_vel[1]) # Use a different var name
            if current_speed_xy_check > current_max_speed_val:
                scale = current_max_speed_val / current_speed_xy_check
                player_vel[0] *= scale; player_vel[1] *= scale
            if not is_on_ground: player_vel[2] += GRAVITY_ACCEL * dt
            if is_charging_jump and keys[pygame.K_SPACE] and jump_charge_start_time is not None:
                charge_duration = current_time - jump_charge_start_time
                if charge_duration < MAX_JUMP_CHARGE_DURATION: player_vel[2] += JUMP_CHARGE_BOOST_ACCEL_RATE * dt
                else: is_charging_jump = False
            player_pos_world[0]+=player_vel[0]*dt; player_pos_world[1]+=player_vel[1]*dt; player_pos_world[2]+=player_vel[2]*dt
            player_bottom_z = player_pos_world[2] - current_radius
            if player_bottom_z <= ground_level_z + GROUND_CONTACT_THRESHOLD:
                if not is_on_ground:
                    just_landed_this_frame = True; landing_impact_velocity = abs(player_vel[2])
                    if landing_impact_velocity > BOUNCE_THRESHOLD: player_vel[2] = landing_impact_velocity * COEFFICIENT_OF_RESTITUTION
                    else: player_vel[2] = 0; player_pos_world[2] = ground_level_z + current_radius
                else: player_vel[2] = 0; player_pos_world[2] = ground_level_z + current_radius
                is_on_ground = True
            else: is_on_ground = False
            if is_on_ground and abs(player_vel[2]) < REST_VELOCITY_THRESHOLD: player_vel[2] = 0.0
            dx_world = player_pos_world[0]-prev_player_xy[0]; dy_world = player_pos_world[1]-prev_player_xy[1]
            prev_player_xy = (player_pos_world[0],player_pos_world[1])
            if is_on_ground and (abs(dx_world)>1e-5 or abs(dy_world)>1e-5) and current_radius > 1e-5:
                dist_moved=math.hypot(dx_world,dy_world); angle_rolled=dist_moved/current_radius
                roll_axis=normalize_vector((-dy_world,dx_world,0))
                if roll_axis!=(0,0,0):
                    delta_rot=quat_from_axis_angle(roll_axis,angle_rolled); player_rotation=quat_mult(delta_rot,player_rotation)
                    norm_sq=sum(c*c for c in player_rotation)
                    if norm_sq>1e-9: player_rotation=tuple(c/math.sqrt(norm_sq) for c in player_rotation)
            if jump_initiated_this_frame: target_squish = SQUISH_ON_JUMP_START
            elif just_landed_this_frame:
                norm_impact=0
                if MAX_IMPACT_VELOCITY > IMPACT_VELOCITY_THRESHOLD: norm_impact = (landing_impact_velocity - IMPACT_VELOCITY_THRESHOLD) / (MAX_IMPACT_VELOCITY - IMPACT_VELOCITY_THRESHOLD)
                norm_impact=max(0,min(1,norm_impact))
                target_squish = MIN_SQUISH_ON_LANDING - norm_impact * (MIN_SQUISH_ON_LANDING - MAX_SQUISH_ON_LANDING)
                target_squish=max(0.1,min(1.0,target_squish))
            elif is_on_ground and not is_charging_jump: target_squish = 1.0
            squish_force=elasticity*(target_squish-squish); damping_squish_force=SQUISH_DAMPING*squish_velocity
            squish_accel=squish_force-damping_squish_force; squish_velocity+=squish_accel*dt; squish+=squish_velocity*dt
            squish=max(0.1,min(2.0,squish))

        game_surface.fill(BLACK); toolbar_surface.fill(TOOLBAR_COLOR)
        draw_origin_x, draw_origin_y = origin_x_base+camera_offset_x, origin_y_base+camera_offset_y
        if cached_ground_surface is None or cached_ground_zoom!=zoom or abs(cached_camera_offset[0]-camera_offset_x)>GROUND_CACHE_MARGIN/4 or abs(cached_camera_offset[1]-camera_offset_y)>GROUND_CACHE_MARGIN/4:
            cached_ground_surface = render_ground_surface(zoom, ground_level_z) # Pass only zoom and z
            cached_ground_zoom=zoom; cached_camera_offset=(camera_offset_x,camera_offset_y)
        blit_x = draw_origin_x - cached_ground_surface.get_width()//2 # Center cache on draw_origin
        blit_y = draw_origin_y - cached_ground_surface.get_height()//2
        game_surface.blit(cached_ground_surface, (blit_x, blit_y))

        # Player Rendering (as before)
        player_render_voxels = []
        effective_squish_xy = 1.0 / squish if squish != 0 else 1.0
        for rel_ix, rel_iy, rel_iz_shape, base_color in player_voxels_shape:
            s_rel_x, s_rel_y, s_rel_z = rel_ix * PLAYER_SCALE_cfg, rel_iy * PLAYER_SCALE_cfg, rel_iz_shape * PLAYER_SCALE_cfg * squish
            rot_sub_voxel_rel = quat_rotate_point(player_rotation, (s_rel_x, s_rel_y, s_rel_z))
            vx,vy,vz = player_pos_world[0]+rot_sub_voxel_rel[0], player_pos_world[1]+rot_sub_voxel_rel[1], player_pos_world[2]+rot_sub_voxel_rel[2]
            player_render_voxels.append(((vx,vy,vz), base_color))
        player_render_voxels.sort(key=lambda item: (item[0][2], item[0][1], item[0][0]), reverse=True)
        for (voxel_w_center_x, voxel_w_center_y, voxel_w_center_z), base_color in player_render_voxels:
            for face_key, unrot_normal in FACE_NORMALS.items():
                world_face_normal = normalize_vector(quat_rotate_point(player_rotation, unrot_normal))
                dot_view_normal = sum(n*v for n,v in zip(world_face_normal, VIEW_DIRECTION_FOR_CULLING))
                if dot_view_normal > CULLING_THRESHOLD_cfg:
                    unit_corners = VOXEL_CORNER_OFFSETS[face_key]
                    face_pts_3d = []
                    for off_x,off_y,off_z in unit_corners:
                        lc_x,lc_y,lc_z = off_x-0.5, off_y-0.5, off_z-0.5
                        sl_x,sl_y,sl_z = lc_x*PLAYER_SCALE_cfg, lc_y*PLAYER_SCALE_cfg, lc_z*PLAYER_SCALE_cfg*squish
                        rot_lc = quat_rotate_point(player_rotation, (sl_x,sl_y,sl_z))
                        wc_x,wc_y,wc_z = voxel_w_center_x+rot_lc[0], voxel_w_center_y+rot_lc[1], voxel_w_center_z+rot_lc[2]
                        face_pts_3d.append((wc_x,wc_y,wc_z))
                    poly_2d = [ (int(sx+draw_origin_x), int(sy+draw_origin_y)) for sx,sy in 
                                [project_iso(p[0],p[1],p[2],zoom) for p in face_pts_3d] ]
                    face_col = compute_face_color_with_normal(base_color, world_face_normal, light_direction)
                    pygame.draw.polygon(game_surface, face_col, poly_2d)
        
        screen.blit(game_surface, (0, TOOLBAR_HEIGHT))
        help_txt_str = f"H:Help P:Pause T:Tune Esc:Close C:CamReset M:LightMode FPS:{current_fps:.0f}"
        help_surf = font_medium.render(help_txt_str, True, TEXT_COLOR)
        toolbar_surface.blit(help_surf, (10, (TOOLBAR_HEIGHT - help_surf.get_height()) // 2))
        settings_btn_rect_tb = pygame.Rect(SCREEN_WIDTH - 160, (TOOLBAR_HEIGHT - 24)//2, 32, 24)
        pygame.draw.rect(toolbar_surface, (80,120,180), settings_btn_rect_tb, border_radius=5)
        settings_icon_font = pygame.font.Font(None,28); settings_icon_surf = settings_icon_font.render("⚙", True,WHITE)
        toolbar_surface.blit(settings_icon_surf, (settings_btn_rect_tb.centerx - settings_icon_surf.get_width()//2, settings_btn_rect_tb.centery - settings_icon_surf.get_height()//2))
        reset_player_btn_rect_tb = pygame.Rect(SCREEN_WIDTH - 120, (TOOLBAR_HEIGHT - 24)//2, 110, 24)
        pygame.draw.rect(toolbar_surface, (180,100,100), reset_player_btn_rect_tb, border_radius=5)
        reset_player_text_surf = font_medium.render("Reset Player",True,WHITE)
        toolbar_surface.blit(reset_player_text_surf, (reset_player_btn_rect_tb.centerx - reset_player_text_surf.get_width()//2, reset_player_btn_rect_tb.centery - reset_player_text_surf.get_height()//2))
        screen.blit(toolbar_surface, (0,0))

        if show_physics_panel: draw_physics_panel_ui(screen, font_small, font_medium)
        if show_help:
            help_s = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT), pygame.SRCALPHA); help_s.fill((0,0,0,180))
            help_text_lines = ["--- Controls ---", "WASD: Move", "Shift: Sprint", "Space: Jump (Hold to boost)", "Mouse Wheel: Zoom", "RMB Drag: Pan Camera", "C: Reset Camera", "H: Help", "P: Pause", "T: Tune Physics", "Esc: Close UI / Exit Input", "M: Light Mode"]
            for i, line in enumerate(help_text_lines): line_surf = font_medium.render(line, True, WHITE); help_s.blit(line_surf, (50, 50 + i * 30))
            screen.blit(help_s, (0,TOOLBAR_HEIGHT))
        if paused:
            pause_s = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT), pygame.SRCALPHA); pause_s.fill((0,0,0,120))
            pause_text = font_large.render("PAUSED", True, WHITE)
            pause_s.blit(pause_text, (SCREEN_WIDTH//2 - pause_text.get_width()//2, GAME_SCREEN_HEIGHT//2 - pause_text.get_height()//2))
            screen.blit(pause_s, (0,TOOLBAR_HEIGHT))

        pygame.display.flip()
        clock.tick(60)

    if show_physics_panel: # Save panel state on quit
        cfg.set_param("PHYSICS_PANEL_POS", physics_panel_pos)
        cfg.set_param("UI_PHYSICS_PANEL_WIDTH", PHYSICS_PANEL_WIDTH)
        cfg.set_param("UI_PHYSICS_PANEL_CONTENT_HEIGHT", physics_panel_content_height)
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()