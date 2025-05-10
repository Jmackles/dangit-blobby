import pygame
import math

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
TOOLBAR_HEIGHT = 40 # Height for our simple toolbar
GAME_SCREEN_HEIGHT = SCREEN_HEIGHT - TOOLBAR_HEIGHT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN_BASE = (34, 139, 34)
BROWN = (139, 69, 19)
TOOLBAR_COLOR = (50, 50, 50)
TEXT_COLOR = (200, 200, 200)

VOXEL_SIZE = 20 # This is more of a conceptual unit now, projection handles actual screen size
ISO_TILE_WIDTH_HALF_BASE = VOXEL_SIZE * 0.866 # Base for zoom
ISO_TILE_HEIGHT_HALF_BASE = VOXEL_SIZE * 0.5   # Base for zoom
ISO_Z_FACTOR_BASE = VOXEL_SIZE                # Base for zoom


GROUND_RANGE = 30

# --- Global Variables ---
zoom = 1.0
light_direction = [-0.577, -0.577, 0.577] # Normalized default: up-left-ish

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
BASE_ACCEL_RATE = 10.0      # units/sec^2
FAST_ACCEL_RATE = 20.0      # units/sec^2
BASE_MAX_SPEED_UPS = 3.0    # units/sec
FAST_MAX_SPEED_UPS = 6.0    # units/sec
DAMPING_FACTOR = 5.0        # Affects how quickly player slows down

GRAVITY_ACCEL = -25.0       # units/sec^2 (Increased for less floaty feel)
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
SQUISH_ON_LANDING = 0.6     # More squish on landing (when velocity is high)
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
def normalize_vector(v):
    mag = math.sqrt(v[0]**2 + v[1]**2 + v[2]**2)
    if mag == 0:
        return (0, 0, 0) # Or raise an error, or return v
    return (v[0]/mag, v[1]/mag, v[2]/mag)

def project_iso(ix, iy, iz, current_zoom):
    """Converts 3D VOXEL INDICES (ix, iy, iz) to 2D isometric screen coordinates, applying zoom."""
    # Scale projection factors by zoom
    iso_tile_width_half = ISO_TILE_WIDTH_HALF_BASE * current_zoom
    iso_tile_height_half = ISO_TILE_HEIGHT_HALF_BASE * current_zoom
    iso_z_factor = ISO_Z_FACTOR_BASE * current_zoom
    screen_x = (ix - iy) * iso_tile_width_half
    screen_y = (ix + iy) * iso_tile_height_half - iz * iso_z_factor
    return int(screen_x), int(screen_y)

def get_voxel_face_points_from_indices(ix, iy, iz, face_key):
    s = 1
    corners_idx = [
        (ix, iy, iz), (ix, iy + s, iz), (ix + s, iy + s, iz), (ix + s, iy, iz),
        (ix, iy, iz + s), (ix, iy + s, iz + s), (ix + s, iy + s, iz + s), (ix + s, iy, iz + s)
    ]
    if face_key == "iso_top": return [corners_idx[4], corners_idx[5], corners_idx[6], corners_idx[7]]
    elif face_key == "iso_bottom": return [corners_idx[3], corners_idx[2], corners_idx[1], corners_idx[0]]
    elif face_key == "iso_left_side": return [corners_idx[0], corners_idx[1], corners_idx[5], corners_idx[4]]
    elif face_key == "iso_right_side": return [corners_idx[7], corners_idx[6], corners_idx[2], corners_idx[3]]
    elif face_key == "iso_front_side": return [corners_idx[5], corners_idx[1], corners_idx[2], corners_idx[6]]
    elif face_key == "iso_back_side": return [corners_idx[4], corners_idx[7], corners_idx[3], corners_idx[0]]
    return []

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

# --- Main Game Logic ---
def main():
    global zoom, light_direction, player_rotation, light_mode, light_source_pos, \
           squish, jump_charge_start_time, is_charging_jump, is_on_ground, \
           target_squish, squish_velocity
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    game_surface = pygame.Surface((SCREEN_WIDTH, GAME_SCREEN_HEIGHT))
    toolbar_surface = pygame.Surface((SCREEN_WIDTH, TOOLBAR_HEIGHT))
    pygame.display.set_caption("Voxel Planetoid Controls - Phase 3")
    clock = pygame.time.Clock()
    font = pygame.font.Font(None, 24)
    
    # --- Player Sphere Generation ---
    player_voxels_shape = [] # Stores (rel_ix, rel_iy, rel_iz_shape, base_color)
    radius = 6
    # sphere_vertical_offset is the Z-index of the sphere's bottom-most voxel when resting
    sphere_vertical_offset = 0 # Let player_pos_world handle the actual Z position
    for i in range(-radius, radius + 1):
        for j in range(-radius, radius + 1):
            for k in range(-radius, radius + 1): # k is relative to sphere's center
                vx, vy, vz = i + 0.5, j + 0.5, k + 0.5
                if vx**2 + vy**2 + vz**2 <= radius**2 * 1.05:
                    # Store relative to sphere's own (0,0,0) center for shape definition
                    player_voxels_shape.append((i, j, k, GREEN_BASE))

    # Set for culling, using relative coordinates
    voxel_set_player_shape = {(v[0], v[1], v[2]) for v in player_voxels_shape}
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

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT: 
                running = False
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
                zoom += event.y * 0.1; zoom = max(0.1, zoom)
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_SPACE:
                    if is_charging_jump: # If a jump was being charged/boosted
                        is_charging_jump = False
                        # jump_charge_start_time will remain until max duration or landing
            elif event.type == pygame.KEYDOWN:
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

        if dragging_left:
            mpos = pygame.mouse.get_pos()
            if mpos[1] > TOOLBAR_HEIGHT:
                dx, dy = mpos[0] - drag_start_left[0], mpos[1] - drag_start_left[1]
                camera_offset_x += dx; camera_offset_y += dy
                drag_start_left = mpos

        light_dir_normalized = normalize_vector(light_direction) # Ensure it's normalized for calcs

        keys = pygame.key.get_pressed()

        # --- Movement Physics - XY Plane ---
        # Determine acceleration rate and max speed based on shift key
        current_accel_rate = FAST_ACCEL_RATE if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_ACCEL_RATE
        current_max_speed_ups = FAST_MAX_SPEED_UPS if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT] else BASE_MAX_SPEED_UPS

        accel_rate_x, accel_rate_y = 0.0, 0.0
        if keys[pygame.K_a]: accel_rate_x = -current_accel_rate
        if keys[pygame.K_d]: accel_rate_x =  current_accel_rate
        if keys[pygame.K_w]: accel_rate_y = -current_accel_rate
        if keys[pygame.K_s]: accel_rate_y =  current_accel_rate

        # Apply accelerations with greater control on ground
        ground_control_multiplier = 1.2 if is_on_ground else 1.0
        player_vel[0] += accel_rate_x * dt * ground_control_multiplier
        player_vel[1] += accel_rate_y * dt * ground_control_multiplier

        # Apply damping with stronger effect on ground
        ground_damping_multiplier = 1.5 if is_on_ground else 1.0
        if accel_rate_x == 0: player_vel[0] *= (1 - DAMPING_FACTOR * dt * ground_damping_multiplier)
        if accel_rate_y == 0: player_vel[1] *= (1 - DAMPING_FACTOR * dt * ground_damping_multiplier)
        
        # Clamp to max speed for XY plane
        current_speed_xy = math.hypot(player_vel[0], player_vel[1])
        if current_speed_xy > current_max_speed_ups:
            scale = current_max_speed_ups / current_speed_xy
            player_vel[0] *= scale
            player_vel[1] *= scale

        # Stop if very slow to prevent drifting
        if abs(player_vel[0]) < 0.01: player_vel[0] = 0
        if abs(player_vel[1]) < 0.01: player_vel[1] = 0

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
                impact_velocity = prev_pos[2] - player_pos_world[2]
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
        
        # --- Update Squish with Damped Spring Physics ---
        # Use a damped spring model for squish animation to avoid oscillation
        
        # Calculate spring force
        spring_force = (target_squish - squish) * elasticity
        
        # Apply damping to the squish velocity
        squish_velocity = squish_velocity * (1.0 - SQUISH_DAMPING * dt) + spring_force * dt
        
        # Update squish value
        squish += squish_velocity
        
        # Gradually return target squish to 1.0 (normal shape)
        if is_on_ground and not is_charging_jump:
            target_squish += (1.0 - target_squish) * 2.0 * dt
        
        # Clamp squish value to reasonable range and snap if close to 1.0
        squish = max(0.3, min(1.2, squish))
        if abs(squish - 1.0) < 0.02 and abs(squish_velocity) < 0.1:
            squish = 1.0
            squish_velocity = 0.0
            if not is_charging_jump:
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

        # Combine all drawable items (ground and player voxels) and sort by Z for painter's
        # This is a simplified approach; for complex scenes, more granular sorting is needed.
        # For now, we draw ground first, then player, relying on player's Z being generally higher.
        
        # Draw Ground (only top faces)
        for gx, gy, gz in ground_voxels_coords:
            face_key = "iso_top"
            face_indices = get_voxel_face_points_from_indices(gx, gy, gz, face_key)
            if face_indices:
                face_normal = FACE_NORMALS[face_key]
                shaded_g_color = compute_face_color_with_normal(BROWN, face_normal, light_dir_normalized)
                # Project the 3D indices of the face corners
                raw_proj_pts = [project_iso(p[0], p[1], p[2], zoom) for p in face_indices]
                # Shift by camera origin
                shifted = [(p[0] + draw_origin_x, p[1] + draw_origin_y) for p in raw_proj_pts]
                pygame.draw.polygon(game_surface, shaded_g_color, shifted)

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

        shadow_proj = project_iso(shadow_world_x, shadow_world_y, shadow_world_z_on_ground, zoom)
        shadow_screen_x = shadow_proj[0] + draw_origin_x
        shadow_screen_y = shadow_proj[1] + draw_origin_y
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
        # We need to sort player voxels by their absolute Z for correct intra-sphere drawing
        # This is a bit inefficient to do every frame, but necessary for rotation later
        # For now, player_voxels_shape is already sorted by relative Z.
        # When combined with player_pos_world[2], the order should largely hold for drawing.

        temp_player_draw_list = []
        for rel_ix, rel_iy, rel_iz_shape, base_color in player_voxels_shape:
            # Compute rotated coordinate using quaternion
            rotated = quat_rotate_point(player_rotation, (rel_ix, rel_iy, rel_iz_shape))
            # Apply squish: horizontal scaled by 1/squish; vertical (z) scaled by squish.
            scaled = (rotated[0] * (1.0/squish), rotated[1] * (1.0/squish), rotated[2] * squish)
            abs_ix = scaled[0] + player_pos_world[0]
            abs_iy = scaled[1] + player_pos_world[1]
            abs_iz = scaled[2] + player_pos_world[2]
            temp_player_draw_list.append((abs_ix, abs_iy, abs_iz, base_color, (rel_ix, rel_iy, rel_iz_shape)))

        # Sort by absolute Z for drawing this frame
        temp_player_draw_list.sort(key=lambda v: v[2])

        for abs_ix, abs_iy, abs_iz, base_color, rel_coords in temp_player_draw_list:
            # Instead of culling based on unrotated shape, draw all faces for a solid sphere.
            for face_key in FACE_NORMALS.keys():
                # Adjust for get_voxel_face_points_from_indices expecting bottom-left-back corner
                voxel_corner_x, voxel_corner_y, voxel_corner_z = abs_ix - 0.5, abs_iy - 0.5, abs_iz - 0.5
                face_indices = get_voxel_face_points_from_indices(voxel_corner_x, voxel_corner_y, voxel_corner_z, face_key)
                if face_indices:
                    base_normal = FACE_NORMALS[face_key]
                    # Rotate the base face normal using the same quaternion:
                    rotated_normal = quat_rotate_point(player_rotation, base_normal)
                    shaded_color = compute_face_color_with_normal(base_color, rotated_normal, light_dir_normalized)
                    raw_proj_pts = [project_iso(p[0], p[1], p[2], zoom) for p in face_indices]
                    shifted = [(p[0] + draw_origin_x, p[1] + draw_origin_y) for p in raw_proj_pts]
                    pygame.draw.polygon(game_surface, shaded_color, shifted)

        # --- Draw Toolbar as Clickable UI ---
        toolbar_surface.fill(TOOLBAR_COLOR)
        # Draw light icon (a simple circle) at right side:
        light_icon_rect = pygame.Rect(SCREEN_WIDTH - 50, 5, 40, 30)
        pygame.draw.ellipse(toolbar_surface, WHITE, light_icon_rect, 2)
        if light_mode:
            pygame.draw.ellipse(toolbar_surface, (255, 255, 0), light_icon_rect)
        
        # Draw state information for debugging
        lt = f"Light: X{light_direction[0]:.1f} Y{light_direction[1]:.1f} Z{light_direction[2]:.1f}"
        t_s = font.render(lt, True, TEXT_COLOR)
        toolbar_surface.blit(t_s, (5, 5))
        
        zt = f"Zoom: {zoom:.1f}x"
        z_s = font.render(zt, True, TEXT_COLOR)
        toolbar_surface.blit(z_s, (SCREEN_WIDTH - 200, 5))
        
        state_color = (120, 255, 120) if is_on_ground else TEXT_COLOR
        pt = f"Pos: X{player_pos_world[0]:.1f} Y{player_pos_world[1]:.1f} Z{player_pos_world[2]:.1f}"
        p_s = font.render(pt, True, state_color)
        toolbar_surface.blit(p_s, (5, 20))
        
        st = f"Vel: {current_speed_xy:.1f} Squish: {squish:.2f}"
        s_s = font.render(st, True, TEXT_COLOR)
        toolbar_surface.blit(s_s, (SCREEN_WIDTH - 200, 20))

        screen.blit(toolbar_surface, (0, 0))
        screen.blit(game_surface, (0, TOOLBAR_HEIGHT))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()