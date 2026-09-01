"""
Simply Capture
==============
A robust camera settings tool for Autodesk Maya.

This tool allows artists to easily set, load, and keyframe camera parameters
like focal length, aperture, focus distance, and shutter speed.

Features:
- Preset-based configuration for Lenses and Sensor Sizes (Film Backs).
- Real-time Field of View (FOV) calculation.
- Focus Distance helper (to selection or specific object).
- Focus Pull Assistant (creates 2-key rack focus animations).
- Shutter Speed presets with Motion Blur preview.
- Unit-safe: UI displays in Meters; Camera attributes set in Scene Units.

Requires: Maya 2026+ (uses specific keyTangent flags)
Author: [Your Name]
License: MIT / Internal Use
"""

import math
from collections import OrderedDict

import maya.cmds as cmds

# ---------------------------------------------------------------------------
# Constants & Presets
# ---------------------------------------------------------------------------

TAG = "SimplyCapture"

# UI Constants
FOCUS_UI_MAX_METERS = 100.0  # Max visible range in the UI slider
FOCUS_INFINITY = 1e9         # Large number to represent infinity in scene units
SHUTTER_MENU_NAME = "scShutterMenu"
CAM_ROW_NAME = "scCameraRow"
CAM_MENU_NAME = "scCameraMenu"
SHUTTER_ROW_NAME = "scShutterRow"
LENS_MENU_NAME = "scLensMenu"
SENSOR_MENU_NAME = "scSensorMenu"
CUSTOM_SHUTTER_LABEL = "Custom"

# Default UI Values
DEFAULTS = {
    "focal_length": 50.0,       # mm
    "aperture": 2.8,            # f-stop
    "focus_distance": 1.0,      # meters
    "sensor_preset": "Full Frame 35mm",
    "lens_preset": "50mm Normal",
    "shutter": "1/48",
    "dof": False,               # Depth of Field enabled?
    "focus_point_mode": "BBox Center",
    "focus_offset": 0.0,        # meters
    "apply_focus": True,
    "keyframe": False,
}

# Focus Modes
FOCUS_MODE_BBOX = "BBox Center"
FOCUS_MODE_PIVOT = "Pivot"

# Interpolation Options for Focus Pull
INTERPOLATION_LINEAR = "Linear"
INTERPOLATION_SMOOTH = "Smooth"
INTERPOLATION_EASE_IN = "Ease In"
INTERPOLATION_EASE_OUT = "Ease Out"
INTERPOLATION_OPTIONS = [
    INTERPOLATION_LINEAR,
    INTERPOLATION_SMOOTH,
    INTERPOLATION_EASE_IN,
    INTERPOLATION_EASE_OUT,
]

FOCUS_PULL_DEFAULT_DURATION = 24.0 # frames

# Lens Presets
# Updated with user requested additions: 8mm, 60mm, 100mm, 200mm
# Kept existing presets
LENS_PRESETS = {
    "8mm Ultra Wide":  {"focal_length": 8.0},
    "14mm Ultra Wide": {"focal_length": 14.0},
    "24mm Wide":       {"focal_length": 24.0},
    "35mm Classic":    {"focal_length": 35.0},
    "50mm Normal":     {"focal_length": 50.0},
    "60mm Mid-Tele":   {"focal_length": 60.0},
    "85mm Portrait":   {"focal_length": 85.0},
    "100mm Macro":     {"focal_length": 100.0},
    "135mm Tele":      {"focal_length": 135.0},
    "200mm Telephoto": {"focal_length": 200.0},
    "Custom":          {"focal_length": 50.0}, # Fallback
}

# Sensor / Film Back Presets
# Dimensions in millimeters. Maya uses inches for filmAperture attrs.
# Updated per request:
# - Renamed: "8mm Microscope" -> "Super 8mm"
# - Renamed: "16mm Super 8" -> "16mm"
# - Added: Micro Four Thirds, 65mm, IMAX 70mm
# - Removed: Anamorphic 2.39, 16:9 Digital, 4:3 Digital
# - Kept: Full Frame 35mm, Super 35
SENSOR_PRESETS = {
    "Super 8mm":         {"horizontal_mm": 8.00, "vertical_mm": 6.00},
    "16mm":              {"horizontal_mm": 16.00, "vertical_mm": 10.00},
    "Micro Four Thirds": {"horizontal_mm": 17.30, "vertical_mm": 13.00},
    "Full Frame 35mm":   {"horizontal_mm": 36.00, "vertical_mm": 24.00},
    "Super 35":          {"horizontal_mm": 24.89, "vertical_mm": 18.66},
    "65mm VistaVision":  {"horizontal_mm": 65.00, "vertical_mm": 30.00},
    "IMAX 70mm":         {"horizontal_mm": 70.00, "vertical_mm": 46.85},
    "Custom":            {"horizontal_mm": 36.00, "vertical_mm": 24.00},
}

# Shutter Speed Presets (labels in seconds/fraction)
SHUTTER_OPTIONS = [
    "1/24", "1/25", "1/30", "1/48", "1/50", "1/60", 
    "1/96", "1/100", "1/120", "1/125", "1/180", "1/250",
    "1/256", "1/360", "1/500", "1/720", "1/1000", "1/2000"
]


# ---------------------------------------------------------------------------
# Unit Conversion Utilities
# ---------------------------------------------------------------------------

def get_scene_units():
    """Return the current Maya linear scene unit as a string."""
    try:
        return cmds.currentUnit(query=True, linear=True)
    except (RuntimeError, ValueError):
        return "cm"


def inches_to_mm(value_inches):
    """Convert inches to millimeters."""
    if value_inches is None or value_inches == 0:
        return 0.0
    return value_inches * 25.4

def mm_to_inches(value_mm):
    """Convert millimeters to inches."""
    if value_mm is None or value_mm == 0:
        return 0.0
    return value_mm / 25.4

def _scene_units_to_meters(value_scene_units):
    """
    Convert a distance in the current Maya scene units to Meters.
    The UI always displays in Meters.
    """
    if value_scene_units is None:
        return 0.0
        
    unit = get_scene_units()
    
    factor = 1.0
    if unit == "cm":
        factor = 0.01
    elif unit == "mm":
        factor = 0.001
    elif unit == "m":
        factor = 1.0
    elif unit == "inch":
        factor = 0.0254
    elif unit == "ft":
        factor = 0.3048
    elif unit == "yd":
        factor = 0.9144
    elif unit == "mi":
        factor = 1609.34
    
    return value_scene_units * factor


def _meters_to_scene_units(value_meters):
    """
    Convert a distance in Meters to the current Maya scene units.
    Used when setting camera attributes.
    """
    if value_meters is None:
        return 0.0
        
    unit = get_scene_units()
    
    factor = 1.0
    if unit == "cm":
        factor = 100.0
    elif unit == "mm":
        factor = 1000.0
    elif unit == "m":
        factor = 1.0
    elif unit == "inch":
        factor = 39.3701
    elif unit == "ft":
        factor = 3.28084
    elif unit == "yd":
        factor = 1.09361
    elif unit == "mi":
        factor = 0.000621371
        
    return value_meters * factor


def _is_infinity(value):
    """Check if a value represents 'infinity' (very large number)."""
    return value >= FOCUS_INFINITY


def _get_frame_rate():
    """Get the scene's frame rate (frames per second)."""
    try:
        return float(cmds.sceneTime(query=True, unit="fps"))
    except:
        return 24.0


# ---------------------------------------------------------------------------
# Core Helper Functions
# ---------------------------------------------------------------------------

def _partial_name(node):
    """Get the short name of a node, handling long paths."""
    if not node:
        return ""
    return node.split("|")[-1]

def _short_name(node):
    """Get the short name of a node."""
    return _partial_name(node)


def _shutter_to_seconds(label):
    """
    Convert a shutter label (e.g., "1/48") to seconds.
    Returns 0.0 if parsing fails.
    """
    if not label or label == CUSTOM_SHUTTER_LABEL:
        return 0.0
        
    if "/" in label:
        parts = label.split("/")
        if len(parts) == 2:
            try:
                num = float(parts[0])
                den = float(parts[1])
                if den == 0:
                    return 0.0
                return num / den
            except (ValueError, ZeroDivisionError):
                return 0.0
    else:
        try:
            return float(label)
        except ValueError:
            return 0.0


def _shutter_to_angle(label, fps):
    """
    Calculate the shutter angle in degrees based on label and fps.
    Angle = (shutter_time / frame_time) * 360
    frame_time = 1 / fps
    """
    shutter_time = _shutter_to_seconds(label)
    if fps <= 0:
        return 0.0
        
    frame_time = 1.0 / fps
    if frame_time <= 0:
        return 0.0
        
    angle = (shutter_time / frame_time) * 360.0
    return angle


def _shutter_angle_to_label(angle, fps):
    """
    Find the closest standard shutter label for a given angle.
    Returns the label string, or None if it's 'custom' (non-standard).
    """
    if angle <= 0:
        return "1/1" # Or None, but 1/1 is safer for 360
        
    frame_time = 1.0 / fps if fps > 0 else 1.0
    shutter_time = (angle / 360.0) * frame_time
    
    closest_label = None
    closest_diff = float('inf')
    
    for label in SHUTTER_OPTIONS:
        sec = _shutter_to_seconds(label)
        diff = abs(sec - shutter_time)
        if diff < closest_diff:
            closest_diff = diff
            closest_label = label
            
    # If the difference is significant, it's a custom value
    # Tolerance: 1% of the shutter time or 1/1000th of a sec?
    # Let's use a relative tolerance of 5%
    if shutter_time > 0 and (closest_diff / shutter_time) > 0.05:
        return None 
        
    return closest_label


# ---------------------------------------------------------------------------
# Camera Discovery
# ---------------------------------------------------------------------------

def _is_perspective_camera(shape):
    """
    Return True if the camera shape is a perspective camera.
    """
    try:
        ortho = cmds.getAttr(shape + ".orthographic")
        return not ortho
    except (RuntimeError, ValueError, TypeError):
        return True


def _resolve_group(group):
    """
    Given a list of transforms sharing the same short name, determine the
    minimum path depth at which all members are unique, then assign names
    at that depth to ALL members for visual consistency.
    """
    if len(group) == 1:
        return [(_short_name(group[0]), group[0])]

    max_parts = max(len(t.strip("|").split("|")) for t in group)

    for depth in range(1, max_parts + 1):
        names = ["/".join(t.strip("|").split("|")[-depth:]) for t in group]
        if len(set(names)) == len(names):
            return list(zip(names, group))

    used = set()
    results = []
    for t in group:
        base = t.strip("|")
        name = base
        count = 1
        while name in used:
            name = "%s_%d" % (base, count)
            count += 1
        used.add(name)
        results.append((name, t))
    return results


def _get_cameras():
    """
    Return a list of (display_name, long_path) tuples for all
    perspective cameras in the scene.
    """
    long_paths = cmds.ls(type="camera", long=True) or []
    if not long_paths:
        return []

    transforms = []
    for cam in long_paths:
        if not _is_perspective_camera(cam):
            continue

        parents = cmds.listRelatives(cam, parent=True, fullPath=True) or []
        transforms.append(parents[0] if parents else cam)

    transforms.sort(key=lambda x: _short_name(x))

    groups = OrderedDict()
    for t in transforms:
        sn = _short_name(t)
        groups.setdefault(sn, []).append(t)

    results = []
    used_names = set()

    for group in groups.values():
        resolved = _resolve_group(group)
        for display_name, long_path in resolved:
            name = display_name
            count = 2
            while name in used_names:
                name = "%s_%d" % (display_name, count)
                count += 1
            used_names.add(name)
            results.append((name, long_path))

    return results


def _get_camera_shape(node):
    """
    Given a camera transform (short name, long path, or shape),
    return the camera shape node as a long path, or None.
    """
    if not node:
        return None

    if "|" not in node:
        matches = cmds.ls(node, long=True) or []
        if len(matches) != 1:
            return None
        node = matches[0]

    if not cmds.objExists(node):
        return None

    if cmds.objectType(node) == "transform":
        shapes = cmds.listRelatives(node, shapes=True, type="camera", fullPath=True) or []
        return shapes[0] if shapes else None
    elif cmds.objectType(node) == "camera":
        return node

    return None


def _get_camera_transform(node):
    """
    Given a camera shape, transform, short name, or long path,
    return the parent camera transform as a long path, or None.
    """
    if not node:
        return None

    if "|" not in node:
        matches = cmds.ls(node, long=True) or []
        if len(matches) != 1:
            return None
        node = matches[0]

    if not cmds.objExists(node):
        return None

    if cmds.objectType(node) == "camera":
        parents = cmds.listRelatives(node, parent=True, fullPath=True) or []
        return parents[0] if parents else None
    elif cmds.objectType(node) == "transform":
        return node

    return None


def _get_current_render_camera():
    """Return the first renderable perspective camera transform as a long path."""
    cameras = cmds.ls(type="camera", long=True) or []

    for shape in cameras:
        try:
            if not cmds.getAttr(shape + ".renderable"):
                continue
        except (RuntimeError, ValueError):
            continue

        if not _is_perspective_camera(shape):
            continue

        parents = cmds.listRelatives(shape, parent=True, fullPath=True) or []
        if parents:
            return parents[0]

    return None


# ---------------------------------------------------------------------------
# Attribute Utilities
# ---------------------------------------------------------------------------

def _attr_exists(node, attr):
    """Check if an attribute exists on a node."""
    try:
        return cmds.attributeQuery(attr, node=node, exists=True)
    except (RuntimeError, ValueError):
        return False


def _attr_is_locked(node, attr):
    """Check if an attribute is locked on a node."""
    try:
        return cmds.getAttr(node + "." + attr, lock=True)
    except (RuntimeError, ValueError):
        return False


def _set_attr_if_possible(node, attr, value):
    """
    Set an attribute on a node if it exists and is not locked.
    Returns True on success, False if the attribute is unavailable.
    """
    if not cmds.objExists(node):
        cmds.warning("Node does not exist: %s" % node)
        return False

    if not _attr_exists(node, attr):
        cmds.warning("Attribute does not exist: %s.%s" % (node, attr))
        return False

    if _attr_is_locked(node, attr):
        cmds.warning("Attribute is locked: %s.%s" % (node, attr))
        return False

    try:
        cmds.setAttr(node + "." + attr, value)
        return True
    except (RuntimeError, ValueError, TypeError) as exc:
        cmds.warning("Could not set %s.%s: %s" % (node, attr, exc))
        return False


def _keyframe_attr(shape, attr):
    """
    Create a keyframe on the given attribute at the current timeline time.
    Returns True on success, False on failure.
    """
    try:
        cmds.setKeyframe(shape, attribute=attr)
        return True
    except (RuntimeError, ValueError, TypeError) as exc:
        cmds.warning(
            "%s Could not keyframe %s.%s: %s" % (TAG, shape, attr, exc)
        )
        return False


def _undo_group(action_fn, chunkName="Simply Capture"):
    """Execute action_fn as one Maya undo chunk."""
    opened = False
    try:
        cmds.undoInfo(openChunk=True, chunkName=chunkName)
        opened = True
        return action_fn()
    finally:
        if opened:
            try:
                cmds.undoInfo(closeChunk=True)
            except (RuntimeError, ValueError):
                pass


def _rebuild_optionMenu(parent_layout, menu_name, label, width, populate_fn):
    """
    Delete and recreate an optionMenu in the given parent layout.
    """
    if cmds.optionMenu(menu_name, exists=True):
        cmds.deleteUI(menu_name)
    cmds.setParent(parent_layout)
    new_menu = cmds.optionMenu(menu_name, label=label, width=width)
    populate_fn(new_menu)
    return new_menu


# ---------------------------------------------------------------------------
# Field of View Calculation
# ---------------------------------------------------------------------------

def _compute_fov(focal_length_mm, sensor_h_mm, sensor_v_mm):
    """
    Compute horizontal and vertical field of view in degrees.
    """
    if focal_length_mm <= 0.0 or sensor_h_mm <= 0.0 or sensor_v_mm <= 0.0:
        return (0.0, 0.0)

    h_fov = 2.0 * math.atan(sensor_h_mm / (2.0 * focal_length_mm)) * (180.0 / math.pi)
    v_fov = 2.0 * math.atan(sensor_v_mm / (2.0 * focal_length_mm)) * (180.0 / math.pi)

    return (h_fov, v_fov)


def _update_fov_display(controls):
    """Update the FOV display text based on current focal length and sensor."""
    try:
        focal = cmds.floatSliderGrp(controls["focal"], query=True, value=True)
        sensor_h = cmds.floatField(controls["sensor_h"], query=True, value=True)
        sensor_v = cmds.floatField(controls["sensor_v"], query=True, value=True)

        h_fov, v_fov = _compute_fov(focal, sensor_h, sensor_v)

        text = "H: %.1f\u00b0  V: %.1f\u00b0" % (h_fov, v_fov)
        cmds.text(controls["fov_display"], edit=True, label=text)
    except (RuntimeError, ValueError, KeyError, TypeError):
        return


# ---------------------------------------------------------------------------
# Lens Preset Helpers
# ---------------------------------------------------------------------------

def _get_matching_lens_preset(focal_length, tolerance=0.5):
    """
    Find the lens preset that matches the given focal length.
    """
    for preset_name, data in LENS_PRESETS.items():
        if preset_name == "Custom":
            continue
        if abs(data["focal_length"] - focal_length) <= tolerance:
            return preset_name
    return None


def _set_lens_preset(controls, preset_name):
    """Set the lens preset menu and update focal length UI."""
    if preset_name not in LENS_PRESETS:
        return

    cmds.optionMenu(controls["lens_preset"], edit=True, value=preset_name)

    if preset_name == "Custom":
        _update_fov_display(controls)
        return

    focal_value = LENS_PRESETS[preset_name]["focal_length"]
    cmds.floatSliderGrp(controls["focal"], edit=True, value=focal_value)
    _update_fov_display(controls)


def _on_focal_length_changed(controls, *_args):
    """Callback for focal length change. Updates preset menu and FOV."""
    try:
        current_value = cmds.floatSliderGrp(controls["focal"], query=True, value=True)
    except (RuntimeError, ValueError, KeyError):
        return

    try:
        current_preset = cmds.optionMenu(controls["lens_preset"], query=True, value=True)
    except (RuntimeError, ValueError, KeyError):
        return

    if current_preset in LENS_PRESETS and current_preset != "Custom":
        preset_focal = LENS_PRESETS[current_preset]["focal_length"]
        if abs(preset_focal - current_value) <= 0.5:
            _update_fov_display(controls)
            return

    matched = _get_matching_lens_preset(current_value)

    if matched is not None:
        if matched != current_preset:
            cmds.optionMenu(controls["lens_preset"], edit=True, value=matched)
    else:
        if current_preset != "Custom":
            cmds.optionMenu(controls["lens_preset"], edit=True, value="Custom")

    _update_fov_display(controls)


def _on_lens_preset_changed(controls, preset_name, *_args):
    """Callback for lens preset menu change."""
    if preset_name not in LENS_PRESETS:
        return

    if preset_name == "Custom":
        _update_fov_display(controls)
        return

    focal_value = LENS_PRESETS[preset_name]["focal_length"]
    cmds.floatSliderGrp(controls["focal"], edit=True, value=focal_value)
    _update_fov_display(controls)


# ---------------------------------------------------------------------------
# Sensor Preset Matching
# ---------------------------------------------------------------------------

def _match_sensor_preset(horizontal_mm, vertical_mm, tolerance=0.05):
    """Attempt to match sensor dimensions to a known preset."""
    for preset_name, data in SENSOR_PRESETS.items():
        if preset_name == "Custom":
            continue
        if (abs(data["horizontal_mm"] - horizontal_mm) <= tolerance and
                abs(data["vertical_mm"] - vertical_mm) <= tolerance):
            return preset_name
    return None


# ---------------------------------------------------------------------------
# Focus distance calculation (shared logic)
# ---------------------------------------------------------------------------

def _get_root_transform(node):
    """
    Robustly resolve a node to its root transform.
    Handles cases where a shape is passed or the hierarchy is deep.
    """
    if not node or not cmds.objExists(node):
        return None
    
    current = node
    # If it's a shape, get parent transform
    if cmds.objectType(current) != "transform":
        parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
        if not parents:
            return None
        current = parents[0]
        
    # Walk up to the top
    while True:
        parents = cmds.listRelatives(current, parent=True, fullPath=True) or []
        if not parents:
            return current
        current = parents[0]


def _get_world_point(node, mode):
    """
    Return the world-space (x, y, z) position for a given node based on mode.
    """
    if not node or not cmds.objExists(node):
        return None

    # Ensure we are working with the root transform for accurate world BBox/Position
    root_transform = _get_root_transform(node)
    if not root_transform:
        return None

    try:
        if mode == FOCUS_MODE_PIVOT:
            pos = cmds.xform(root_transform, query=True, worldSpace=True, translation=True)
            return (pos[0], pos[1], pos[2])
        else:
            # exactWorldBoundingBox works best on transforms
            bbox = cmds.exactWorldBoundingBox(root_transform)
            if bbox:
                return (
                    (bbox[0] + bbox[3]) * 0.5,
                    (bbox[1] + bbox[4]) * 0.5,
                    (bbox[2] + bbox[5]) * 0.5,
                )
    except (RuntimeError, ValueError, TypeError):
        return None

    return None


def _get_combined_bbox_center(nodes):
    """
    Compute the center of the combined bounding box of multiple nodes.
    """
    bboxes = []
    for node in nodes:
        if not node or not cmds.objExists(node):
            continue
        root_transform = _get_root_transform(node)
        if not root_transform:
            continue
        try:
            bbox = cmds.exactWorldBoundingBox(root_transform)
            if bbox:
                bboxes.append(bbox)
        except (RuntimeError, ValueError, TypeError):
            continue

    if not bboxes:
        return None

    combined = [
        min(b[0] for b in bboxes),
        min(b[1] for b in bboxes),
        min(b[2] for b in bboxes),
        max(b[3] for b in bboxes),
        max(b[4] for b in bboxes),
        max(b[5] for b in bboxes),
    ]

    return (
        (combined[0] + combined[3]) * 0.5,
        (combined[1] + combined[4]) * 0.5,
        (combined[2] + combined[5]) * 0.5,
    )


def _average_world_points(points):
    """Average a list of (x, y, z) tuples."""
    if not points:
        return None
    n = len(points)
    return (
        sum(p[0] for p in points) / n,
        sum(p[1] for p in points) / n,
        sum(p[2] for p in points) / n,
    )


def _distance_from_camera(camera_transform, target_point):
    """Compute Euclidean distance from camera to point."""
    if target_point is None:
        return None

    try:
        camera_pos = cmds.xform(
            camera_transform, query=True, worldSpace=True, translation=True
        )
    except (RuntimeError, ValueError, TypeError):
        return None

    dx = target_point[0] - camera_pos[0]
    dy = target_point[1] - camera_pos[1]
    dz = target_point[2] - camera_pos[2]

    return (dx * dx + dy * dy + dz * dz) ** 0.5


def _get_focus_distance_to_selection(camera_transform, mode):
    """Return distance from camera to current selection."""
    selection = cmds.ls(selection=True, long=True) or []

    if not selection:
        cmds.warning("Select an object in the scene to focus on.")
        return None

    dag_objects = [obj for obj in selection if cmds.objExists(obj)]

    if not dag_objects:
        cmds.warning("Selected object no longer exists.")
        return None

    if mode == FOCUS_MODE_PIVOT:
        points = []
        for obj in dag_objects:
            pt = _get_world_point(obj, FOCUS_MODE_PIVOT)
            if pt is not None:
                points.append(pt)
        target_point = _average_world_points(points)
    else:
        target_point = _get_combined_bbox_center(dag_objects)

    if target_point is None:
        cmds.warning("Could not compute focus point for selection.")
        return None

    return _distance_from_camera(camera_transform, target_point)


def _get_focus_distance_to_target(camera_transform, target_path, mode):
    """Return distance from camera to a specific target object."""
    if not target_path or not cmds.objExists(target_path):
        return None

    target_point = _get_world_point(target_path, mode)

    if target_point is None:
        return None

    return _distance_from_camera(camera_transform, target_point)


# ---------------------------------------------------------------------------
# Angle display and blur preview
# ---------------------------------------------------------------------------

def _set_blur_preview(controls, angle):
    """Update the shutter-angle display text and motion-blur progress bar."""
    try:
        angle = max(0.0, min(float(angle), 360.0))

        cmds.text(
            controls["angle_display"],
            edit=True,
            label="= %.1f deg" % angle,
        )

        cmds.progressBar(
            controls["blur_preview"],
            edit=True,
            progress=int(round(angle)),
        )
    except (RuntimeError, ValueError, TypeError, KeyError):
        return


def _update_angle_display(controls, *_):
    """Update the shutter-angle text and motion-blur indicator from menu state."""
    try:
        val = cmds.optionMenu(controls["shutter"], query=True, value=True)
        fps = _get_frame_rate()
        angle = _shutter_to_angle(val, fps)
        _set_blur_preview(controls, angle)
    except (RuntimeError, ValueError, KeyError):
        return


def _set_shutter_menu_value(controls, matched_label, exact_angle):
    """Set the shutter optionMenu and update preview."""
    menu = controls["shutter"]

    if matched_label is not None:
        _remove_custom_shutter_item(menu)
        cmds.optionMenu(menu, edit=True, value=matched_label)
        controls["custom_shutter_angle"] = None

        fps = _get_frame_rate()
        angle = _shutter_to_angle(matched_label, fps)

    else:
        _remove_custom_shutter_item(menu)
        cmds.menuItem(parent=menu, label=CUSTOM_SHUTTER_LABEL)
        cmds.optionMenu(menu, edit=True, value=CUSTOM_SHUTTER_LABEL)
        angle = max(0.0, min(float(exact_angle), 360.0))
        controls["custom_shutter_angle"] = angle

    _set_blur_preview(controls, angle)


def _remove_custom_shutter_item(menu):
    """Remove the 'Custom' menuItem from the shutter menu if it exists."""
    items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
    for item in items:
        try:
            if cmds.menuItem(item, query=True, label=True) == CUSTOM_SHUTTER_LABEL:
                cmds.deleteUI(item)
        except (RuntimeError, ValueError):
            continue


# ---------------------------------------------------------------------------
# Focus Target helpers
# ---------------------------------------------------------------------------

def _set_focus_target(controls):
    """Store the currently selected scene object as the focus target."""
    selection = cmds.ls(selection=True, long=True) or []

    if not selection:
        cmds.warning("%s Select exactly one object to set as focus target." % TAG)
        return

    valid_objects = [obj for obj in selection if cmds.objExists(obj)]

    if not valid_objects:
        cmds.warning("%s Selected object no longer exists." % TAG)
        return

    if len(valid_objects) > 1:
        cmds.warning(
            "%s Multiple objects selected (%d). Deselect all but one and try again."
            % (TAG, len(valid_objects))
        )
        return

    target_path = valid_objects[0]
    controls["focus_target_path"] = target_path

    display_name = _partial_name(target_path)
    cmds.textField(controls["focus_target_display"], edit=True, text=display_name)
    cmds.checkBox(controls["focus_target_use"], edit=True, value=True, enable=True)

    print("%s Focus target set: %s" % (TAG, display_name))


def _clear_focus_target(controls):
    """Remove the stored focus target."""
    controls["focus_target_path"] = None
    cmds.textField(controls["focus_target_display"], edit=True, text="None")
    cmds.checkBox(controls["focus_target_use"], edit=True, value=False, enable=False)
    print("%s Focus target cleared." % TAG)


def _validate_focus_target(controls):
    """Verify that the stored focus target still exists."""
    target_path = controls.get("focus_target_path")
    if target_path is None:
        return False

    if not cmds.objExists(target_path):
        display = _partial_name(target_path)
        cmds.warning(
            "%s Focus target '%s' no longer exists. Target cleared."
            % (TAG, display)
        )
        _clear_focus_target(controls)
        return False

    return True


# ---------------------------------------------------------------------------
# Focus Pull Assistant Helpers
# ---------------------------------------------------------------------------

def _set_focus_pull_target_a(controls):
    """Store the currently selected scene object as Focus Pull Target A."""
    selection = cmds.ls(selection=True, long=True) or []

    if not selection:
        cmds.warning("%s [Focus Pull] Select exactly one object for Target A." % TAG)
        return

    valid_objects = [obj for obj in selection if cmds.objExists(obj)]

    if not valid_objects:
        cmds.warning("%s [Focus Pull] Selected object for Target A no longer exists." % TAG)
        return

    if len(valid_objects) > 1:
        cmds.warning(
            "%s [Focus Pull] Multiple objects selected (%d) for Target A. "
            "Deselect all but one." % (TAG, len(valid_objects))
        )
        return

    target_path = valid_objects[0]
    controls["focus_pull_target_a"] = target_path

    display_name = _partial_name(target_path)
    cmds.textField(controls["focus_pull_target_a_display"], edit=True, text=display_name)
    print("%s [Focus Pull] Target A set: %s" % (TAG, display_name))


def _set_focus_pull_target_b(controls):
    """Store the currently selected scene object as Focus Pull Target B."""
    selection = cmds.ls(selection=True, long=True) or []

    if not selection:
        cmds.warning("%s [Focus Pull] Select exactly one object for Target B." % TAG)
        return

    valid_objects = [obj for obj in selection if cmds.objExists(obj)]

    if not valid_objects:
        cmds.warning("%s [Focus Pull] Selected object for Target B no longer exists." % TAG)
        return

    if len(valid_objects) > 1:
        cmds.warning(
            "%s [Focus Pull] Multiple objects selected (%d) for Target B. "
            "Deselect all but one." % (TAG, len(valid_objects))
        )
        return

    target_path = valid_objects[0]
    controls["focus_pull_target_b"] = target_path

    display_name = _partial_name(target_path)
    cmds.textField(controls["focus_pull_target_b_display"], edit=True, text=display_name)
    print("%s [Focus Pull] Target B set: %s" % (TAG, display_name))


def _validate_focus_pull_targets(controls):
    """Validate that both Focus Pull targets still exist."""
    a_path = controls.get("focus_pull_target_a")
    b_path = controls.get("focus_pull_target_b")

    if a_path is None:
        cmds.warning("%s [Focus Pull] Target A is not set." % TAG)
        return False

    if b_path is None:
        cmds.warning("%s [Focus Pull] Target B is not set." % TAG)
        return False

    if not cmds.objExists(a_path):
        display = _partial_name(a_path)
        cmds.warning("%s [Focus Pull] Target A '%s' no longer exists." % (TAG, display))
        controls["focus_pull_target_a"] = None
        cmds.textField(controls["focus_pull_target_a_display"], edit=True, text="(deleted)")
        return False

    if not cmds.objExists(b_path):
        display = _partial_name(b_path)
        cmds.warning("%s [Focus Pull] Target B '%s' no longer exists." % (TAG, display))
        controls["focus_pull_target_b"] = None
        cmds.textField(controls["focus_pull_target_b_display"], edit=True, text="(deleted)")
        return False

    return True


def _apply_interpolation(shape, attr, interpolation_type, time_a=None, time_b=None):
    """
    Adjust keyframe tangent types to achieve the desired interpolation curve.
    """
    try:
        num_keys = cmds.keyframe(shape, query=True, attribute=attr, keyframeCount=True)
    except (RuntimeError, ValueError):
        return

    if not num_keys or num_keys < 2:
        return

    if interpolation_type == INTERPOLATION_LINEAR:
        cmds.keyTangent(shape, attribute=attr, et="linear", ot="linear")

    elif interpolation_type == INTERPOLATION_SMOOTH:
        cmds.keyTangent(shape, attribute=attr, et="smooth", ot="smooth")

    elif interpolation_type == INTERPOLATION_EASE_IN:
        if time_a is not None and time_b is not None:
            cmds.keyTangent(shape, attribute=attr, time=time_a, et="linear", ot="smooth")
            cmds.keyTangent(shape, attribute=attr, time=time_b, et="linear", ot="linear")
        else:
            cmds.keyTangent(shape, attribute=attr, timeIndex=0, et="linear", ot="smooth")
            cmds.keyTangent(shape, attribute=attr, timeIndex=1, et="linear", ot="linear")

    elif interpolation_type == INTERPOLATION_EASE_OUT:
        if time_a is not None and time_b is not None:
            cmds.keyTangent(shape, attribute=attr, time=time_a, et="linear", ot="linear")
            cmds.keyTangent(shape, attribute=attr, time=time_b, et="smooth", ot="linear")
        else:
            cmds.keyTangent(shape, attribute=attr, timeIndex=0, et="linear", ot="linear")
            cmds.keyTangent(shape, attribute=attr, timeIndex=1, et="smooth", ot="linear")

    else:
        cmds.keyTangent(shape, attribute=attr, et="linear", ot="linear")


def _create_focus_pull(controls):
    """
    Create a 2-key rack-focus animation on the dropdown camera's focusDistance.
    """
    long_path = _get_dropdown_camera(controls)
    if not long_path:
        return

    cam_name = _short_name(long_path)
    shape = _get_camera_shape(long_path)
    if not shape:
        cmds.warning("%s [Focus Pull] Could not find camera shape for '%s'." % (TAG, cam_name))
        return

    if not _attr_exists(shape, "focusDistance"):
        cmds.warning("%s [Focus Pull] Camera '%s' has no focusDistance attribute." % (TAG, cam_name))
        return

    if _attr_is_locked(shape, "focusDistance"):
        cmds.warning("%s [Focus Pull] focusDistance is locked on '%s'." % (TAG, cam_name))
        return

    if not _validate_focus_pull_targets(controls):
        return

    target_a_path = controls["focus_pull_target_a"]
    target_b_path = controls["focus_pull_target_b"]
    display_a = _partial_name(target_a_path)
    display_b = _partial_name(target_b_path)

    mode = cmds.optionMenu(controls["focus_point_mode"], query=True, value=True)
    if mode not in (FOCUS_MODE_BBOX, FOCUS_MODE_PIVOT):
        mode = FOCUS_MODE_BBOX

    offset_m = cmds.floatField(controls["focus_offset"], query=True, value=True)
    offset_scene = _meters_to_scene_units(offset_m)

    dist_a_scene = _get_focus_distance_to_target(long_path, target_a_path, mode)
    if dist_a_scene is None:
        cmds.warning("%s [Focus Pull] Could not calculate distance to Target A '%s'." % (TAG, display_a))
        return

    dist_b_scene = _get_focus_distance_to_target(long_path, target_b_path, mode)
    if dist_b_scene is None:
        cmds.warning("%s [Focus Pull] Could not calculate distance to Target B '%s'." % (TAG, display_b))
        return

    final_dist_a = max(0.0, dist_a_scene + offset_scene)
    final_dist_b = max(0.0, dist_b_scene + offset_scene)

    start_frame = cmds.floatField(controls["focus_pull_start"], query=True, value=True)
    end_frame = cmds.floatField(controls["focus_pull_end"], query=True, value=True)

    if end_frame <= start_frame:
        cmds.warning(
            "%s [Focus Pull] End frame (%.1f) must be greater than start frame (%.1f)."
            % (TAG, end_frame, start_frame)
        )
        return

    interpolation = cmds.optionMenu(controls["focus_pull_interp"], query=True, value=True)
    if interpolation not in INTERPOLATION_OPTIONS:
        interpolation = INTERPOLATION_LINEAR

    original_time = cmds.currentTime(query=True)

    success = True

    def _do_focus_pull():
        nonlocal success
        try:
            cmds.cutKey(shape, attribute="focusDistance", clear=True)
        except (RuntimeError, ValueError):
            pass

        try:
            cmds.currentTime(start_frame)
            cmds.setAttr(shape + ".focusDistance", final_dist_a)
            cmds.setKeyframe(shape, attribute="focusDistance")
        except (RuntimeError, ValueError, TypeError) as exc:
            cmds.warning("%s [Focus Pull] Failed to key Target A: %s" % (TAG, exc))
            success = False
            return

        try:
            cmds.currentTime(end_frame)
            cmds.setAttr(shape + ".focusDistance", final_dist_b)
            cmds.setKeyframe(shape, attribute="focusDistance")
        except (RuntimeError, ValueError, TypeError) as exc:
            cmds.warning("%s [Focus Pull] Failed to key Target B: %s" % (TAG, exc))
            success = False
            return

        try:
            _apply_interpolation(shape, "focusDistance", interpolation, time_a=start_frame, time_b=end_frame)
        except (RuntimeError, ValueError, TypeError) as exc:
            cmds.warning("%s [Focus Pull] Warning: could not apply '%s' interpolation: %s" % (TAG, interpolation, exc))

        try:
            cmds.currentTime(original_time)
        except (RuntimeError, ValueError):
            pass

    _undo_group(_do_focus_pull, chunkName="Focus Pull Assistant")

    if not success:
        try:
            cmds.undo()
        except (RuntimeError, ValueError):
            pass
        return

    # Update UI to reflect new camera state
    try:
        current_focus_scene = cmds.getAttr(shape + ".focusDistance")
        if _is_infinity(current_focus_scene):
            cmds.checkBox(controls["infinity"], edit=True, value=True)
            cmds.floatSliderGrp(controls["focus"], edit=True, enable=False, value=FOCUS_INFINITY)
        else:
            focus_m = _scene_units_to_meters(current_focus_scene)
            ui_focus = min(focus_m, FOCUS_UI_MAX_METERS)
            cmds.checkBox(controls["infinity"], edit=True, value=False)
            cmds.floatSliderGrp(controls["focus"], edit=True, enable=True, value=ui_focus)
    except (RuntimeError, ValueError, TypeError):
        pass

    dist_a_m = _scene_units_to_meters(final_dist_a)
    dist_b_m = _scene_units_to_meters(final_dist_b)

    start_display = ("%.0f" % start_frame if start_frame == int(start_frame) else "%.1f" % start_frame)
    end_display = ("%.0f" % end_frame if end_frame == int(end_frame) else "%.1f" % end_frame)

    print(
        "%s Created focus pull: %s (%.1fm) frame %s \u2192 %s (%.1fm) frame %s [%s]"
        % (TAG, display_a, dist_a_m, start_display, display_b, dist_b_m, end_display, interpolation)
    )


def _init_focus_pull_frames(controls):
    """Initialize the Focus Pull start/end frame fields to defaults."""
    current = cmds.currentTime(query=True)
    cmds.floatField(controls["focus_pull_start"], edit=True, value=current)
    cmds.floatField(controls["focus_pull_end"], edit=True, value=current + FOCUS_PULL_DEFAULT_DURATION)


# ---------------------------------------------------------------------------
# UI Population
# ---------------------------------------------------------------------------

def _populate_cameras(menu, preserve_path=None):
    """Repopulate the camera optionMenu."""
    cameras = _get_cameras()
    camera_map = {display: path for display, path in cameras}

    items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
    for item in items:
        if cmds.menuItem(item, exists=True):
            cmds.deleteUI(item)

    if not cameras:
        cmds.menuItem(parent=menu, label="(no perspective cameras)")
        return camera_map

    for display_name, _ in cameras:
        cmds.menuItem(parent=menu, label=display_name)

    selected = None
    if preserve_path:
        for display_name, long_path in cameras:
            if long_path == preserve_path:
                selected = display_name
                break

    if not selected:
        render_cam_long = _get_current_render_camera()
        if render_cam_long:
            for display_name, long_path in cameras:
                if long_path == render_cam_long:
                    selected = display_name
                    break

    if not selected:
        selected = cameras[0][0]

    cmds.optionMenu(menu, edit=True, value=selected)
    return camera_map


def _populate_shutters(parent_layout):
    """Rebuild the shutter speed menu."""
    def _fill(menu):
        unique = list(dict.fromkeys(SHUTTER_OPTIONS))
        sorted_options = sorted(unique, key=_shutter_to_seconds)
        for opt in sorted_options:
            cmds.menuItem(label=opt)
        cmds.optionMenu(menu, edit=True, value=DEFAULTS["shutter"])

    return _rebuild_optionMenu(parent_layout, SHUTTER_MENU_NAME, "Speed:", 200, _fill)


def _populate_sensor_presets(menu):
    """Populate the sensor preset option menu."""
    items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
    for item in items:
        if cmds.menuItem(item, exists=True):
            cmds.deleteUI(item)

    for preset_name in SENSOR_PRESETS:
        cmds.menuItem(parent=menu, label=preset_name)
    cmds.optionMenu(menu, edit=True, value=DEFAULTS["sensor_preset"])


def _populate_lens_presets(menu):
    """Populate the lens preset option menu."""
    items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
    for item in items:
        if cmds.menuItem(item, exists=True):
            cmds.deleteUI(item)

    for preset_name in LENS_PRESETS:
        cmds.menuItem(parent=menu, label=preset_name)
    cmds.optionMenu(menu, edit=True, value=DEFAULTS["lens_preset"])


def _populate_interpolation(menu):
    """Populate the focus pull interpolation option menu."""
    items = cmds.optionMenu(menu, query=True, itemListLong=True) or []
    for item in items:
        if cmds.menuItem(item, exists=True):
            cmds.deleteUI(item)

    for option in INTERPOLATION_OPTIONS:
        cmds.menuItem(parent=menu, label=option)
    cmds.optionMenu(menu, edit=True, value=INTERPOLATION_SMOOTH)


# ---------------------------------------------------------------------------
# Sensor Preset UI Update
# ---------------------------------------------------------------------------

def _update_sensor_fields_from_preset(controls, preset_name):
    """Update sensor H/V fields when preset changes."""
    if preset_name not in SENSOR_PRESETS:
        return

    if preset_name == "Custom":
        _update_fov_display(controls)
        return

    data = SENSOR_PRESETS[preset_name]
    cmds.floatField(controls["sensor_h"], edit=True, value=data["horizontal_mm"])
    cmds.floatField(controls["sensor_v"], edit=True, value=data["vertical_mm"])
    _update_fov_display(controls)


def _set_sensor_preset_value(controls, preset_name, h_mm, v_mm):
    """Set the sensor preset menu and fields programmatically."""
    cmds.optionMenu(controls["sensor_preset"], edit=True, value=preset_name)
    cmds.floatField(controls["sensor_h"], edit=True, value=h_mm)
    cmds.floatField(controls["sensor_v"], edit=True, value=v_mm)
    _update_fov_display(controls)


# ---------------------------------------------------------------------------
# Dropdown Camera Helper
# ---------------------------------------------------------------------------

def _get_dropdown_camera(controls):
    """Return the long path of the selected camera."""
    cam_display = cmds.optionMenu(controls["camera"], query=True, value=True)

    if not cam_display or cam_display.startswith("(no"):
        cmds.warning("No camera selected in dropdown.")
        return None

    long_path = controls["camera_map"].get(cam_display)
    if not long_path:
        cmds.warning("Camera '%s' not found in current scene." % cam_display)
        return None

    if not cmds.objExists(long_path):
        cmds.warning("Camera '%s' no longer exists. Click Refresh." % cam_display)
        return None

    return long_path


# ---------------------------------------------------------------------------
# UI Construction
# ---------------------------------------------------------------------------

def create_camera_settings_ui():
    """Create (or recreate) the Simply Capture window."""
    window_name = "simplyCaptureWindow"

    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    window = cmds.window(window_name, title="Simply Capture", width=380, sizeable=True)
    main = cmds.columnLayout(adjustableColumn=True, rowSpacing=6)

    controls = {"window": window}
    controls["custom_shutter_angle"] = None
    controls["focus_target_path"] = None
    controls["focus_pull_target_a"] = None
    controls["focus_pull_target_b"] = None

    # --- Camera Selection ---
    cmds.text(label="Camera (perspective only)", align="left")
    cam_row = cmds.rowLayout(CAM_ROW_NAME, numberOfColumns=3, columnWidth3=(200, 50, 50))
    controls["camera_row"] = cam_row

    camera_menu = cmds.optionMenu(CAM_MENU_NAME, label="Select:", width=200)
    controls["camera"] = camera_menu

    camera_map = _populate_cameras(camera_menu)
    controls["camera_map"] = camera_map

    cmds.button(label="Refresh", width=50, command=lambda *_: _refresh_cameras(controls))
    cmds.button(label="Load", width=50, command=lambda *_: _load_camera_settings(controls))
    cmds.setParent(main)

    # --- Aperture ---
    cmds.text(label="Aperture (f-stop)", align="left")
    aperture = cmds.floatSliderGrp(label="f/", field=True, minValue=0.95, maxValue=22.0, value=DEFAULTS["aperture"], columnWidth2=(50, 240))
    controls["aperture"] = aperture

    # --- Depth of Field Toggle ---
    dof_chk = cmds.checkBox(label="Enable Depth of Field", value=DEFAULTS["dof"])
    controls["dof"] = dof_chk

    # --- Focal Length ---
    cmds.text(label="Focal Length", align="left")

    lens_preset_menu = cmds.optionMenu(LENS_MENU_NAME, label="Lens Preset:", width=200)
    _populate_lens_presets(lens_preset_menu)
    controls["lens_preset"] = lens_preset_menu

    focal_row = cmds.rowLayout(numberOfColumns=2, columnWidth2=(220, 100))
    focal = cmds.floatSliderGrp(label="mm", field=True, minValue=1.0, maxValue=600.0, value=float(DEFAULTS["focal_length"]), columnWidth2=(30, 190))
    fov_display = cmds.text(label="", align="right")
    controls["focal"] = focal
    controls["fov_display"] = fov_display
    cmds.setParent(main)

    # --- Sensor / Film Back ---
    cmds.text(label="Sensor / Film Back", align="left")

    sensor_preset_menu = cmds.optionMenu(SENSOR_MENU_NAME, label="Preset:", width=180)
    _populate_sensor_presets(sensor_preset_menu)
    controls["sensor_preset"] = sensor_preset_menu

    sensor_dims_row = cmds.rowLayout(numberOfColumns=4, columnWidth4=(45, 85, 45, 85))
    cmds.text(label="H (mm)", align="right")
    sensor_h = cmds.floatField(value=SENSOR_PRESETS[DEFAULTS["sensor_preset"]]["horizontal_mm"], precision=2, width=85)
    cmds.text(label="V (mm)", align="right")
    sensor_v = cmds.floatField(value=SENSOR_PRESETS[DEFAULTS["sensor_preset"]]["vertical_mm"], precision=2, width=85)
    controls["sensor_h"] = sensor_h
    controls["sensor_v"] = sensor_v
    cmds.setParent(main)

    # --- Shutter Speed ---
    cmds.text(label="Shutter Speed", align="left")
    shutter_row = cmds.rowLayout(SHUTTER_ROW_NAME, numberOfColumns=2, columnWidth2=(220, 80))
    controls["shutter_row"] = shutter_row

    shutter_menu = _populate_shutters(shutter_row)
    controls["shutter"] = shutter_menu

    angle_display = cmds.text(label="", align="right")
    controls["angle_display"] = angle_display
    cmds.setParent(main)

    # --- Motion Blur Preview ---
    blur_row = cmds.rowLayout(numberOfColumns=2, columnWidth2=(80, 200))
    cmds.text(label="Motion Blur:", align="left")
    blur_preview = cmds.progressBar(minValue=0, maxValue=360, progress=0, width=210, height=14)
    controls["blur_preview"] = blur_preview
    cmds.setParent(main)

    # --- Focus Distance ---
    cmds.text(label="Focus Distance", align="left")
    focus_row = cmds.rowLayout(numberOfColumns=3, columnWidth3=(210, 60, 50))
    focus = cmds.floatSliderGrp(label="m", field=True, minValue=0.0, maxValue=FOCUS_UI_MAX_METERS, value=DEFAULTS["focus_distance"], columnWidth2=(30, 180))
    infinity_chk = cmds.checkBox(label="Infinity")
    focus_btn = cmds.button(label="Focus", width=50, height=22, command=lambda *_: _focus_selected(controls))
    controls["focus"] = focus
    controls["infinity"] = infinity_chk
    controls["focus_btn"] = focus_btn
    cmds.setParent(main)

    # --- Focus Offset ---
    cmds.text(label="Focus Offset (m)", align="left")
    focus_offset = cmds.floatField(value=DEFAULTS["focus_offset"], precision=3, width=100)
    controls["focus_offset"] = focus_offset

    # --- Focus Target ---
    cmds.text(label="Focus Target", align="left")

    target_row = cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 50, 50))
    target_display = cmds.textField(text="None", editable=False, width=180, height=22)
    target_set_btn = cmds.button(label="Set", width=50, height=22, command=lambda *_: _set_focus_target(controls))
    target_clear_btn = cmds.button(label="Clear", width=50, height=22, command=lambda *_: _clear_focus_target(controls))
    controls["focus_target_display"] = target_display
    controls["focus_target_set_btn"] = target_set_btn
    controls["focus_target_clear_btn"] = target_clear_btn
    cmds.setParent(main)

    target_opts_row = cmds.rowLayout(numberOfColumns=2, columnWidth2=(140, 120))
    target_use_chk = cmds.checkBox(label="Use Focus Target", value=False, enable=False)
    focus_point_menu = cmds.optionMenu(label="Point:", width=120)
    cmds.menuItem(parent=focus_point_menu, label=FOCUS_MODE_BBOX)
    cmds.menuItem(parent=focus_point_menu, label=FOCUS_MODE_PIVOT)
    cmds.optionMenu(focus_point_menu, edit=True, value=DEFAULTS["focus_point_mode"])
    controls["focus_target_use"] = target_use_chk
    controls["focus_point_mode"] = focus_point_menu
    cmds.setParent(main)

    # --- Focus Pull Assistant ---
    cmds.separator(height=8, style="in")
    cmds.text(label="Focus Pull Assistant", align="left", font="boldLabelFont")

    fp_target_a_row = cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 50, 50))
    fp_target_a_display = cmds.textField(text="None", editable=False, width=180, height=22)
    fp_set_a_btn = cmds.button(label="Set A", width=50, height=22, command=lambda *_: _set_focus_pull_target_a(controls))
    fp_clear_a_btn = cmds.button(label="Clear", width=50, height=22, command=lambda *_: _clear_focus_pull_target_a(controls))
    controls["focus_pull_target_a_display"] = fp_target_a_display
    controls["focus_pull_set_a_btn"] = fp_set_a_btn
    controls["focus_pull_clear_a_btn"] = fp_clear_a_btn
    cmds.setParent(main)

    fp_target_b_row = cmds.rowLayout(numberOfColumns=3, columnWidth3=(180, 50, 50))
    fp_target_b_display = cmds.textField(text="None", editable=False, width=180, height=22)
    fp_set_b_btn = cmds.button(label="Set B", width=50, height=22, command=lambda *_: _set_focus_pull_target_b(controls))
    fp_clear_b_btn = cmds.button(label="Clear", width=50, height=22, command=lambda *_: _clear_focus_pull_target_b(controls))
    controls["focus_pull_target_b_display"] = fp_target_b_display
    controls["focus_pull_set_b_btn"] = fp_set_b_btn
    controls["focus_pull_clear_b_btn"] = fp_clear_b_btn
    cmds.setParent(main)

    fp_frames_row = cmds.rowLayout(numberOfColumns=6, columnWidth6=(70, 60, 70, 60, 80, 60))
    cmds.text(label="Start:", align="right", width=70)
    fp_start_field = cmds.floatField(value=0.0, precision=1, width=60)
    cmds.text(label="End:", align="right", width=70)
    fp_end_field = cmds.floatField(value=24.0, precision=1, width=60)
    fp_interp_menu = cmds.optionMenu(label="Curve:", width=80)
    _populate_interpolation(fp_interp_menu)
    controls["focus_pull_start"] = fp_start_field
    controls["focus_pull_end"] = fp_end_field
    controls["focus_pull_interp"] = fp_interp_menu
    cmds.setParent(main)

    fp_btn_row = cmds.rowLayout(numberOfColumns=1)
    fp_create_btn = cmds.button(label="Create Focus Pull", width=200, height=28, command=lambda *_: _create_focus_pull(controls))
    controls["focus_pull_create_btn"] = fp_create_btn
    cmds.setParent(main)

    _init_focus_pull_frames(controls)

    cmds.separator(height=10, style="in")

    # --- Apply Options ---
    cmds.text(label="Apply Options", align="left")

    apply_focus_chk = cmds.checkBox(label="Apply Focus Distance", value=DEFAULTS["apply_focus"])
    controls["apply_focus"] = apply_focus_chk

    keyframe_chk = cmds.checkBox(label="Keyframe on Apply", value=DEFAULTS["keyframe"])
    controls["keyframe"] = keyframe_chk

    # --- Buttons ---
    cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 100, 100))
    cmds.button(label="Apply", width=95, height=30, command=lambda *_: _apply(controls))
    cmds.button(label="Reset", width=95, height=30, command=lambda *_: _reset(controls))
    cmds.button(label="Close", width=95, height=30, command=lambda *_: cmds.deleteUI(window))
    cmds.setParent(main)

    # --- Attach callbacks ---
    cmds.optionMenu(controls["lens_preset"], edit=True, changeCommand=lambda *a: _on_lens_preset_changed(controls, a[0] if a else None))
    cmds.floatSliderGrp(controls["focal"], edit=True, changeCommand=lambda *a: _on_focal_length_changed(controls))
    cmds.optionMenu(controls["shutter"], edit=True, changeCommand=lambda *a: _update_angle_display(controls))
    cmds.optionMenu(controls["sensor_preset"], edit=True, changeCommand=lambda *a: _update_sensor_fields_from_preset(controls, a[0] if a else None))

    def _on_toggle_infinity(state, *_):
        if state:
            cmds.floatSliderGrp(controls["focus"], edit=True, enable=False, value=FOCUS_INFINITY)
        else:
            cmds.floatSliderGrp(controls["focus"], edit=True, enable=True, value=DEFAULTS["focus_distance"])

    cmds.checkBox(controls["infinity"], edit=True, changeCommand=_on_toggle_infinity)

    _update_angle_display(controls)
    _update_fov_display(controls)

    cmds.showWindow(window)
    return window


# ---------------------------------------------------------------------------
# Focus Pull Target Clear Helpers
# ---------------------------------------------------------------------------

def _clear_focus_pull_target_a(controls):
    """Clear the Focus Pull Target A."""
    controls["focus_pull_target_a"] = None
    cmds.textField(controls["focus_pull_target_a_display"], edit=True, text="None")
    print("%s [Focus Pull] Target A cleared." % TAG)


def _clear_focus_pull_target_b(controls):
    """Clear the Focus Pull Target B."""
    controls["focus_pull_target_b"] = None
    cmds.textField(controls["focus_pull_target_b_display"], edit=True, text="None")
    print("%s [Focus Pull] Target B cleared." % TAG)


# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

def _refresh_cameras(controls):
    """Refresh the contents of the existing camera menu."""
    camera = controls.get("camera")

    if not camera or not cmds.optionMenu(camera, exists=True):
        cmds.warning("Camera menu no longer exists.")
        return

    current_display = cmds.optionMenu(camera, query=True, value=True)
    preserve_path = controls.get("camera_map", {}).get(current_display)

    controls["camera_map"] = _populate_cameras(camera, preserve_path=preserve_path)


def _load_camera_settings(controls):
    """Read settings from the camera and update UI."""
    long_path = _get_dropdown_camera(controls)
    if not long_path:
        return

    cam_display = cmds.optionMenu(controls["camera"], query=True, value=True)
    shape = _get_camera_shape(long_path)
    if not shape:
        cmds.warning("Could not find camera shape for '%s'." % cam_display)
        return

    loaded_any = False

    # --- Focal Length + Lens Preset ---
    if _attr_exists(shape, "focalLength"):
        try:
            focal = cmds.getAttr(shape + ".focalLength")
            cmds.floatSliderGrp(controls["focal"], edit=True, value=focal)

            matched_preset = _get_matching_lens_preset(focal)
            if matched_preset:
                cmds.optionMenu(controls["lens_preset"], edit=True, value=matched_preset)
            else:
                cmds.optionMenu(controls["lens_preset"], edit=True, value="Custom")

            _update_fov_display(controls)
            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    # --- Aperture ---
    if _attr_exists(shape, "fStop"):
        try:
            fstop = cmds.getAttr(shape + ".fStop")
            cmds.floatSliderGrp(controls["aperture"], edit=True, value=fstop)
            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    # --- Depth of Field ---
    if _attr_exists(shape, "depthOfField"):
        try:
            dof = int(cmds.getAttr(shape + ".depthOfField"))
            cmds.checkBox(controls["dof"], edit=True, value=bool(dof))
            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    # --- Focus Distance ---
    if _attr_exists(shape, "focusDistance"):
        try:
            focus_scene = cmds.getAttr(shape + ".focusDistance")
            if _is_infinity(focus_scene):
                cmds.checkBox(controls["infinity"], edit=True, value=True)
                cmds.floatSliderGrp(controls["focus"], edit=True, enable=False, value=FOCUS_INFINITY)
            else:
                cmds.checkBox(controls["infinity"], edit=True, value=False)
                focus_m = _scene_units_to_meters(focus_scene)
                ui_focus = min(focus_m, FOCUS_UI_MAX_METERS)
                cmds.floatSliderGrp(controls["focus"], edit=True, enable=True, value=ui_focus)
            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    # --- Shutter Angle -> Speed ---
    if _attr_exists(shape, "shutterAngle"):
        try:
            angle = cmds.getAttr(shape + ".shutterAngle")
            fps = _get_frame_rate()
            matched = _shutter_angle_to_label(angle, fps)
            _set_shutter_menu_value(controls, matched, angle)
            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    # --- Sensor / Film Back ---
    if _attr_exists(shape, "horizontalFilmAperture") and _attr_exists(shape, "verticalFilmAperture"):
        try:
            h_inches = cmds.getAttr(shape + ".horizontalFilmAperture")
            v_inches = cmds.getAttr(shape + ".verticalFilmAperture")
            h_mm = inches_to_mm(h_inches)
            v_mm = inches_to_mm(v_inches)

            matched_preset = _match_sensor_preset(h_mm, v_mm)

            if matched_preset:
                _set_sensor_preset_value(controls, matched_preset, h_mm, v_mm)
            else:
                _set_sensor_preset_value(controls, "Custom", h_mm, v_mm)

            loaded_any = True
        except (RuntimeError, ValueError, TypeError):
            pass

    if loaded_any:
        print("%s Loaded settings from %s" % (TAG, cam_display))
    else:
        cmds.warning("%s No supported attributes found on '%s'." % (TAG, cam_display))


def _focus_selected(controls):
    """Calculate focus distance and apply to camera."""
    long_path = _get_dropdown_camera(controls)
    if not long_path:
        return

    mode = cmds.optionMenu(controls["focus_point_mode"], query=True, value=True)
    if mode not in (FOCUS_MODE_BBOX, FOCUS_MODE_PIVOT):
        mode = FOCUS_MODE_BBOX

    use_target = cmds.checkBox(controls["focus_target_use"], query=True, value=True)

    if use_target:
        if not _validate_focus_target(controls):
            cmds.warning("%s Focus target is invalid. Using current selection instead." % TAG)
            use_target = False

    if use_target:
        target_path = controls["focus_target_path"]
        base_distance_scene = _get_focus_distance_to_target(long_path, target_path, mode)
        if base_distance_scene is None:
            target_display = _partial_name(target_path)
            cmds.warning("%s Could not calculate focus to target '%s'." % (TAG, target_display))
            return
    else:
        base_distance_scene = _get_focus_distance_to_selection(long_path, mode)
        if base_distance_scene is None:
            return

    offset_m = cmds.floatField(controls["focus_offset"], query=True, value=True)
    offset_scene = _meters_to_scene_units(offset_m)
    final_distance_scene = max(0.0, base_distance_scene + offset_scene)

    base_m = _scene_units_to_meters(base_distance_scene)
    final_m = _scene_units_to_meters(final_distance_scene)

    cmds.checkBox(controls["infinity"], edit=True, value=False)
    ui_focus_m = min(final_m, FOCUS_UI_MAX_METERS)
    cmds.floatSliderGrp(controls["focus"], edit=True, enable=True, value=ui_focus_m)

    shape = _get_camera_shape(long_path)
    if shape:
        def _do_set():
            _set_attr_if_possible(shape, "focusDistance", final_distance_scene)
        _undo_group(_do_set)

    if offset_m >= 0:
        offset_str = "+%.3f m" % offset_m
    else:
        offset_str = "%.3f m" % offset_m

    source_str = ""
    if use_target:
        source_str = " (target: %s)" % _partial_name(controls["focus_target_path"])
    else:
        source_str = " (selection)"

    if final_m > FOCUS_UI_MAX_METERS:
        cmds.warning(
            "%s Focus distance %.3f m exceeds the UI range of %.0f m; "
            "the camera attribute was set to the full value."
            % (TAG, final_m, FOCUS_UI_MAX_METERS)
        )

    print(
        "%s Focus set to %.3f m (base %.3f m, offset %s)%s [%s]"
        % (TAG, final_m, base_m, offset_str, source_str, mode)
    )


def _apply(controls):
    """Apply all settings to the dropdown camera."""
    long_path = _get_dropdown_camera(controls)
    if not long_path:
        return

    cam_name = _short_name(long_path)
    shape = _get_camera_shape(long_path)
    if not shape:
        cmds.warning("%s Could not find camera shape for '%s'." % (TAG, cam_name))
        return

    f_stop = cmds.floatSliderGrp(controls["aperture"], query=True, value=True)
    dof_enabled = int(cmds.checkBox(controls["dof"], query=True, value=True))
    shutter_label = cmds.optionMenu(controls["shutter"], query=True, value=True)
    focal_len = cmds.floatSliderGrp(controls["focal"], query=True, value=True)
    apply_focus = cmds.checkBox(controls["apply_focus"], query=True, value=True)
    keyframe_enabled = cmds.checkBox(controls["keyframe"], query=True, value=True)

    sensor_h_mm = cmds.floatField(controls["sensor_h"], query=True, value=True)
    sensor_v_mm = cmds.floatField(controls["sensor_v"], query=True, value=True)

    fps = _get_frame_rate()

    if shutter_label == CUSTOM_SHUTTER_LABEL:
        custom_angle = controls.get("custom_shutter_angle")
        if custom_angle is not None:
            angle = custom_angle
        else:
            angle = 0.0
            cmds.warning("%s Shutter is in Custom state with no stored angle." % TAG)
    else:
        angle = _shutter_to_angle(shutter_label, fps)
        controls["custom_shutter_angle"] = None

    values = {
        "depthOfField": dof_enabled,
        "fStop": f_stop,
        "focalLength": focal_len,
        "shutterAngle": angle,
    }

    if apply_focus:
        if cmds.checkBox(controls["infinity"], query=True, value=True):
            values["focusDistance"] = FOCUS_INFINITY
        else:
            focus_dist_m = cmds.floatSliderGrp(controls["focus"], query=True, value=True)
            values["focusDistance"] = _meters_to_scene_units(focus_dist_m)

    film_back_values = {
        "horizontalFilmAperture": mm_to_inches(sensor_h_mm),
        "verticalFilmAperture": mm_to_inches(sensor_v_mm),
    }

    current_time = cmds.currentTime(query=True)

    success_count = 0
    failed_attrs = []
    keyframe_failed = []
    film_back_failed = []

    def _do_apply():
        nonlocal success_count

        # Apply core camera values
        for attr, val in values.items():
            if not _attr_exists(shape, attr):
                failed_attrs.append(attr)
                continue
            if _attr_is_locked(shape, attr):
                failed_attrs.append(attr)
                continue

            if not _set_attr_if_possible(shape, attr, val):
                failed_attrs.append(attr)
                continue

            success_count += 1

            if keyframe_enabled:
                if not _keyframe_attr(shape, attr):
                    keyframe_failed.append(attr)

        # Apply film back values
        for attr, val in film_back_values.items():
            if not _attr_exists(shape, attr):
                film_back_failed.append(attr)
                continue
            if _attr_is_locked(shape, attr):
                film_back_failed.append(attr)
                continue

            if not _set_attr_if_possible(shape, attr, val):
                film_back_failed.append(attr)
                continue

            success_count += 1
            
            if keyframe_enabled:
                if not _keyframe_attr(shape, attr):
                    keyframe_failed.append(attr)

    _undo_group(_do_apply)

    if keyframe_enabled:
        frame_display = ("%.0f" % current_time if current_time == int(current_time) else str(current_time))
        action_str = "Applied and keyed at frame %s" % frame_display
    else:
        action_str = "Applied"

    applied_summary_parts = [
        "f/%.2f" % f_stop,
        "%.1f mm" % focal_len,
        "%.2f x %.2f mm" % (sensor_h_mm, sensor_v_mm),
    ]

    if apply_focus:
        if cmds.checkBox(controls["infinity"], query=True, value=True):
            applied_summary_parts.append("focus \u221e")
        else:
            focus_dist_m = cmds.floatSliderGrp(controls["focus"], query=True, value=True)
            applied_summary_parts.append("focus %.2f m" % focus_dist_m)

    applied_summary = ", ".join(applied_summary_parts)

    all_failed = failed_attrs + film_back_failed

    if not all_failed:
        if keyframe_enabled and keyframe_failed:
            print(
                "%s %s to %s: %s. Keyframe warning: could not key [%s]"
                % (TAG, action_str, cam_name, applied_summary, ", ".join(keyframe_failed))
            )
        elif keyframe_enabled:
            print(
                "%s %s to %s: %s"
                % (TAG, action_str, cam_name, applied_summary)
            )
        else:
            print(
                "%s Applied to %s: %s"
                % (TAG, cam_name, applied_summary)
            )
    elif keyframe_failed:
        cmds.warning(
            "%s Partially applied to %s. Set issues: [%s]. "
            "Keyframe issues: [%s]"
            % (TAG, cam_name, ", ".join(all_failed), ", ".join(keyframe_failed))
        )
    else:
        cmds.warning(
            "%s Failed to apply to %s. Issues: [%s]"
            % (TAG, cam_name, ", ".join(all_failed))
        )


def _reset(controls):
    """Reset all UI controls to defaults."""
    cmds.optionMenu(controls["shutter"], edit=True, value=DEFAULTS["shutter"])
    cmds.floatSliderGrp(controls["aperture"], edit=True, value=DEFAULTS["aperture"])
    cmds.checkBox(controls["dof"], edit=True, value=DEFAULTS["dof"])

    default_focal = float(DEFAULTS["focal_length"])
    cmds.floatSliderGrp(controls["focal"], edit=True, value=default_focal)

    matched = _get_matching_lens_preset(default_focal)
    if matched:
        cmds.optionMenu(controls["lens_preset"], edit=True, value=matched)
    else:
        cmds.optionMenu(controls["lens_preset"], edit=True, value="Custom")

    cmds.checkBox(controls["infinity"], edit=True, value=False)
    cmds.floatSliderGrp(controls["focus"], edit=True, enable=True, value=DEFAULTS["focus_distance"])
    cmds.floatField(controls["focus_offset"], edit=True, value=DEFAULTS["focus_offset"])

    default_sensor = SENSOR_PRESETS[DEFAULTS["sensor_preset"]]
    _set_sensor_preset_value(
        controls,
        DEFAULTS["sensor_preset"],
        default_sensor["horizontal_mm"],
        default_sensor["vertical_mm"],
    )

    _clear_focus_target(controls)
    cmds.optionMenu(controls["focus_point_mode"], edit=True, value=DEFAULTS["focus_point_mode"])
    cmds.checkBox(controls["apply_focus"], edit=True, value=DEFAULTS["apply_focus"])
    cmds.checkBox(controls["keyframe"], edit=True, value=DEFAULTS["keyframe"])

    _clear_focus_pull_target_a(controls)
    _clear_focus_pull_target_b(controls)
    _init_focus_pull_frames(controls)
    cmds.optionMenu(controls["focus_pull_interp"], edit=True, value=INTERPOLATION_SMOOTH)

    _remove_custom_shutter_item(controls["shutter"])
    controls["custom_shutter_angle"] = None

    fps = _get_frame_rate()
    angle = _shutter_to_angle(DEFAULTS["shutter"], fps)
    _set_blur_preview(controls, angle)
    _update_fov_display(controls)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    create_camera_settings_ui()
