import pygame
import math

# --- Constants ---
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 900
TOOLBAR_HEIGHT = 40 # Height for our simple toolbar
GAME_SCREEN_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN_BASE = (34, 139, 34)
BROWN = (139, 69, 19)
TOOLBAR_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)

VOXEL_SIZE = 10 # This is more of a conceptual unit now, projection handles actual screen size
ISO_TILE_WIDTH_HALF_BASE = VOXEL_SIZE * 0.866 # Base for zoom
ISO_TILE_HEIGHT_HALF_BASE = VOXEL_SIZE * 0.5   # Base for zoom
ISO_Z_FACTOR_BASE = VOXEL_SIZE                # Base for zoom


GROUND_RANGE = 60

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
CULLING_THRESHOLD = 0.05 # Small positive threshold to avoid z-fighting or shimmering at edges

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
BASE_ACCEL_RATE = 12.0      # increased from 8.0 for more responsive acceleration
FAST_ACCEL_RATE = 16.0      # increased from 10.0
BASE_MAX_SPEED_UPS = 30.0   # increased from 18.0
FAST_MAX_SPEED_UPS = 50.0   # increased from 35.0
DAMPING_FACTOR = 6.0        # Affects how quickly player slows down
MASS = 1.0                 # New mass constant for momentum calculations

GRAVITY_ACCEL = -20.0       # units/sec^2 (Increased for less floaty feel)
INITIAL_JUMP_VELOCITY_UPS = 10.0 # units/sec (Increased for stronger initial jump)
JUMP_CHARGE_BOOST_ACCEL_RATE = 20.0 # units/sec^2 (Increased boost while charging)
MAX_JUMP_CHARGE_DURATION = 0.8   # seconds (Max time space can be held for boost)
BOUNCE_ON_LAND_VELOCITY_UPS = 0.5 # Reduced bounce to prevent jitter
BOUNCE_THRESHOLD = 5.0      # Minimum landing velocity to cause a bounce

# --- Ground Contact Detection ---
GROUND_CONTACT_THRESHOLD = 0.1  # Tolerance for ground contact detection
REST_VELOCITY_THRESHOLD = 0.5   # Below this speed, player is considered at rest

# --- Updated Jump and Elasticity Variables ---
elasticity = 6.0            # Rate at which blob returns to normal shape (increased for faster recovery)
SQUISH_ON_JUMP_START = 0.8  # Less squish on jump start (closer to 1.0)
SQUISH_ON_LANDING = 0.95    # Increased from 0.8 to reduce flattening effect
MAX_SQUISH_FROM_CHARGE = 0.4 # Deepest squish when fully charged
SQUISH_DAMPING = 8.0        # Prevents rapid oscillation in squish

# Player state for jumping
is_charging_jump = False    # True while space is held after initial jump, for boost
jump_charge_start_time = None # Time when jump key was pressed
squish = 1.0                # 1.0 = normal shape; lower values mean squished
is_on_ground = False        # Track ground contact state
target_squish = 1.0         # Target squish value (for damping)
squish_velocity = 0.0       # Rate of change of squish (for damping)

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
GROUND_CACHE_MARGIN = 100  # extra pixels to cover shifting

def render_ground_surface(draw_origin_x, draw_origin_y, current_zoom, ground_level_z_val):
    global cached_ground_surface, cached_ground_zoom, cached_camera_offset
    surface_width = SCREEN_WIDTH + GROUND_CACHE_MARGIN
    surface_height = GAME_SCREEN_HEIGHT + GROUND_CACHE_MARGIN
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

# --- Main Game Logic ---
def main():
    global zoom, light_direction, player_rotation, light_mode, light_source_pos, \
           squish, jump_charge_start_time, is_charging_jump, is_on_ground, \
           target_squish, squish_velocity
    global cached_ground_surface, cached_ground_zoom, cached_camera_offset  # Added caching globals
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game_surface = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT))
    toolbar_surface = pygame.Surface((SCREEN_WIDTH, TOOLBAR_HEIGHT))
    pygame.display.set_caption("Voxel Planetoid Controls - Phase 3")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    font_big = pygame.font.Font(None, 48)

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
    player_pos_world = [0.0, 0.0, float(radius)] # Start with bottom of sphere at z=0
    player_vel = [0.0, 0.0, 0.0] # Velocities in units/sec
    prev_player_xy = (player_pos_world[0], player_pos_world[1])
    # For rolling physics using true 3D rotation, we track the player_rotation quaternion.
    # It starts with identity and is updated based on horizontal movement.

    running = True
    while running:
        dt = clock.get_time() / 1000.0  # Delta time in seconds
        current_fps = clock.get_fps() # Get current FPS

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_h:
                    show_help = not show_help
                elif event.key == pygame.K_p:
                    paused = not paused
                if event.key == pygame.K_SPACE:
                    # On press, if on ground and not already charging a jump, begin a jump.
                    if is_on_ground and not is_charging_jump:
                        player_vel[2] = INITIAL_JUMP_VELOCITY_UPS # Apply initial jump velocity
                        is_charging_jump = True
                        jump_charge_start_time = pygame.time.get_ticks() / 1000.0
                        target_squish = SQUISH_ON_JUMP_START   # Target squish on jump start
                        is_on_ground = False                   # No longer on ground
                elif event.key == pygame.K_j: light_direction[0] = max(-1, light_direction[0] - 0.1)
                elif event.key == pygame.K_l: light_direction[0] = min(1, light_direction[0] + 0.1)
                elif event.key == pygame.K_i: light_direction[1] = max(-1, light_direction[1] - 0.1)
                elif event.key == pygame.K_k: light_direction[1] = min(1, light_direction[1] + 0.1)
                elif event.key == pygame.K_u: light_direction[2] = max(-1, light_direction[2] - 0.1)
                elif event.key == pygame.K_o: light_direction[2] = min(1, light_direction[2] + 0.1)
                light_direction = normalize_vector(light_direction) # Keep it normalized
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # If click occurs in toolbar area, check for light icon click
                    if event.pos[1] < TOOLBAR_HEIGHT:
                        # Assume light icon occupies a small rect at right side
                        icon_rect = pygame.Rect(SCREEN_WIDTH - 50, 5, 40, 30)
                        if icon_rect.collidepoint(event.pos):
                            light_mode = not light_mode  # Toggle mode
                    else:
                        if light_mode:
                            # In light mode, set light_source_pos based on game area click
                            # Convert screen click to world coordinate (inverse projection approx)
                            # Here we simply subtract draw_origin offsets and divide by zoom
                            mpos = event.pos
                            world_x = (mpos[0] - (origin_x_base + camera_offset_x)) / zoom
                            world_y = (mpos[1] - (origin_y_base + camera_offset_y)) / zoom
                            light_source_pos = (world_x, world_y)
                            # Set light_direction from player to light_source_pos (keep Z same as player's contact point)
                            dx = light_source_pos[0] - player_pos_world[0]
                            dy = light_source_pos[1] - player_pos_world[1]
                            light_direction = normalize_vector((dx, dy, 0.5))  # add slight upward bias
                            light_mode = False
                        else:
                            dragging_left = True
                            drag_start_left = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1: 
                    dragging_left = False
            elif event.type == pygame.MOUSEWHEEL:
                zoom += event.y * 0.1
                zoom = max(0.3, min(2.5, zoom))  # Clamp zoom to reasonable range
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if is_charging_jump: # If a jump was being charged/boosted
                        is_charging_jump = False
                        # jump_charge_start_time will remain until max duration or landing

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

        if dragging_left:
            mpos = pygame.mouse.get_pos()
            if mpos[1] > TOOLBAR_HEIGHT:
                dx, dy = mpos[0] - drag_start_left[0], mpos[1] - drag_start_left[1]
                camera_offset_x += dx; camera_offset_y += dy
                drag_start_left = mpos

        light_dir_normalized = normalize_vector(light_direction) # Ensure it's normalized for calcs

        keys = pygame.key.get_pressed()

        # --- Movement Physics - XY Plane using Forces (Adjusted Speed) ---
        current_accel_rate = FAST_ACCEL_RATE if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_ACCEL_RATE
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

        # Clamp XY speed to max value:
        current_speed_xy = math.hypot(player_vel[0], player_vel[1])
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
        prev_pos = player_pos_world.copy()
        for i in range(3): player_pos_world[i] += player_vel[i] * dt
        
        # --- Ground Collision Detection ---
        player_bottom_z = player_pos_world[2] - radius
        ground_surface_z = ground_level_z + 1 # Top of the ground voxels
        
        # Check if player has hit the ground
        if player_bottom_z < ground_surface_z:
            # Correct position to be exactly on ground
            player_pos_world[2] = ground_surface_z + radius
            
            # Handle landing
            if not is_on_ground:
                # impact_velocity was here, removed as unused
                if abs(player_vel[2]) > BOUNCE_THRESHOLD:
                    # Significant landing - apply bounce and squish
                    player_vel[2] = BOUNCE_ON_LAND_VELOCITY_UPS
                    target_squish = SQUISH_ON_LANDING
                    squish_velocity = (SQUISH_ON_LANDING - squish) * 5.0  # Rapid squish
                else:
                    # Gentle landing - stop vertical movement
                    player_vel[2] = 0
                
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
        
        # --- Update Squish with Improved Deformation Model ---
        if is_on_ground:
            # Use damped spring model only when on the ground (landing or push-off)
            spring_force = (target_squish - squish) * elasticity
            squish_velocity = squish_velocity * (1.0 - SQUISH_DAMPING * dt) + spring_force * dt
            squish += squish_velocity
            # When not actively jumping, set target to normal instantly
            if not is_charging_jump:
                target_squish = 1.0
        else:
            # When airborne, quickly restore shape (avoid extra oscillation)
            squish = squish + (1.0 - squish) * 0.2 * dt
            squish_velocity = 0.0

        # Clamp and snap to normal when nearly restored
        squish = max(0.3, min(1.2, squish))
        if abs(squish - 1.0) < 0.02:
            squish = 1.0
            squish_velocity = 0.0
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
                angle = distance / radius  # rotation angle in radians
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
                t = (player_pos_world[2] - (radius) - shadow_world_z_on_ground) / light_dir_normalized[2]
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
        height_above_shadow_plane = max(0, (player_pos_world[2] - radius) - shadow_world_z_on_ground)
        shadow_alpha = max(0, 120 - height_above_shadow_plane * 8) # Adjusted alpha fade
        shadow_size_factor = max(0.1, 1 - height_above_shadow_plane * 0.05) # Adjusted size fade
        
        shadow_base_width = int(VOXEL_SIZE * radius * 0.8 * zoom * shadow_size_factor)
        shadow_base_height = int(VOXEL_SIZE * radius * 0.4 * zoom * shadow_size_factor)
        if shadow_alpha > 5 and shadow_base_width > 1 and shadow_base_height > 1:
            shadow_surf = pygame.Surface((shadow_base_width, shadow_base_height), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow_surf, (0, 0, 0, shadow_alpha), (0, 0, shadow_base_width, shadow_base_height))
            game_surface.blit(shadow_surf, (shadow_screen_x - shadow_base_width // 2, shadow_screen_y - shadow_base_height // 2))

        # Draw Player Sphere (voxels relative to player_pos_world)
        temp_player_draw_list = []
        for rel_ix, rel_iy, rel_iz_shape, base_color in player_voxels_shape:
            rotated = quat_rotate_point(player_rotation, (rel_ix, rel_iy, rel_iz_shape))
            scaled = (rotated[0] * (1.0/squish), rotated[1] * (1.0/squish), rotated[2] * squish)
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
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()