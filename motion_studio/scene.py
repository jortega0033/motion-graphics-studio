"""Scene v1 model: templates, canonical JSON and strict validation."""

import json
import math
import re
import unicodedata
import uuid

PRESETS = {"landscape": (1280, 720), "portrait": (720, 1280)}
FPS = 30
MAX_LAYERS = 32

MAX_ERRORS = 50
MAX_KEYS = 64
MAX_DURATION = 300
KINDS = ("text", "rectangle", "ellipse")
EASINGS = ("hold", "linear", "smoothstep")
ALIGNS = ("left", "center", "right")
TRACK_PROPS = ("x", "y", "opacity")

UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
HEX_RE = re.compile(r"#[0-9a-f]{6}")

SCENE_FIELDS = (
    "schema_version",
    "title",
    "preset",
    "width",
    "height",
    "fps",
    "duration_frames",
    "background",
    "layers",
)
COMMON_LAYER_FIELDS = ("id", "kind", "name", "x", "y", "opacity", "fill")
SHAPE_FIELDS = ("width", "height")
TEXT_FIELDS = ("text", "font_size", "align")


def canonical_json(obj) -> str:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def is_uuid(value) -> bool:
    return isinstance(value, str) and UUID_RE.fullmatch(value) is not None


def new_scene(name: str, template: str, preset: str) -> dict:
    if preset not in PRESETS:
        raise ValueError("unknown preset")
    if template not in ("blank", "title_card"):
        raise ValueError("unknown template")
    width, height = PRESETS[preset]
    scene = {
        "schema_version": 1,
        "title": name,
        "preset": preset,
        "width": width,
        "height": height,
        "fps": FPS,
        "duration_frames": 150,
        "background": "#14181f",
        "layers": [],
    }
    if template == "title_card":
        portrait = preset == "portrait"
        margin = 60 if portrait else 80
        bar_y = 480 if portrait else 240
        title_size = 56 if portrait else 72
        sub_size = 28 if portrait else 32
        title_y = bar_y + 32
        sub_y = title_y + title_size + 24
        scene["layers"] = [
            {
                "id": str(uuid.uuid4()),
                "kind": "rectangle",
                "name": "Accent bar",
                "x": margin,
                "y": bar_y,
                "opacity": 1,
                "fill": "#f5a524",
                "width": 160,
                "height": 10,
            },
            {
                "id": str(uuid.uuid4()),
                "kind": "text",
                "name": "Title",
                "x": margin,
                "y": title_y,
                "opacity": 1,
                "fill": "#f4f1ea",
                "text": "Northwind Demo",
                "font_size": title_size,
                "align": "left",
            },
            {
                "id": str(uuid.uuid4()),
                "kind": "text",
                "name": "Subtitle",
                "x": margin,
                "y": sub_y,
                "opacity": 1,
                "fill": "#c9c3b6",
                "text": "A short product walkthrough",
                "font_size": sub_size,
                "align": "left",
            },
        ]
    return scene


class _Errors:
    def __init__(self):
        self.items = []

    def add(self, path, message):
        if len(self.items) < MAX_ERRORS:
            self.items.append({"path": path, "message": message})


def _join(prefix, name):
    return "%s.%s" % (prefix, name) if prefix else name


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _is_number(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return False
    try:
        return math.isfinite(v)
    except (OverflowError, ValueError):
        return False


def _check_str(value, path, errs, lo, hi, allow_newline=False):
    if not isinstance(value, str):
        errs.add(path, "must be a string")
        return False
    if len(value) < lo or len(value) > hi:
        errs.add(path, "length must be between %d and %d characters" % (lo, hi))
        return False
    for ch in value:
        if allow_newline and ch == "\n":
            continue
        if unicodedata.category(ch) in ("Cc", "Cs"):
            errs.add(path, "must not contain control characters")
            return False
    return True


def _check_num(value, path, errs, lo, hi, lo_exclusive=False):
    if not _is_number(value):
        errs.add(path, "must be a finite number")
        return False
    if (value <= lo) if lo_exclusive else (value < lo):
        errs.add(path, "must be %s %s" % (">" if lo_exclusive else ">=", lo))
        return False
    if value > hi:
        errs.add(path, "must be <= %s" % (hi,))
        return False
    return True


def _check_color(value, path, errs):
    if not isinstance(value, str) or HEX_RE.fullmatch(value) is None:
        errs.add(path, "must be a lowercase #rrggbb color")
        return False
    return True


def _check_fields(obj, required, prefix, errs, check_unknown=True):
    for name in required:
        if name not in obj:
            errs.add(_join(prefix, name), "is required")
    if check_unknown:
        allowed = set(required)
        for key in obj:
            if key not in allowed:
                errs.add(
                    _join(prefix, "<unknown>") if not isinstance(key, str)
                    else _join(prefix, _safe_key(key)),
                    "unknown field",
                )


def _safe_key(key):
    key = key[:40]
    return "".join(c if c.isprintable() and c not in "[]." else "?" for c in key)


def _validate_tracks(tracks, path, errs, bound_x, bound_y, duration):
    if not isinstance(tracks, dict):
        errs.add(path, "must be an object")
        return
    for prop in tracks:
        if prop not in TRACK_PROPS:
            errs.add(_join(path, _safe_key(prop) if isinstance(prop, str) else "?"),
                     "unknown track")
    for prop in TRACK_PROPS:
        if prop not in tracks:
            continue
        keys = tracks[prop]
        kpath = _join(path, prop)
        if not isinstance(keys, list):
            errs.add(kpath, "must be an array")
            continue
        if len(keys) > MAX_KEYS:
            errs.add(kpath, "must have at most %d keys" % MAX_KEYS)
            continue
        if prop == "x":
            lo, hi = -bound_x, bound_x
        elif prop == "y":
            lo, hi = -bound_y, bound_y
        else:
            lo, hi = 0, 1
        seen = set()
        for i, key in enumerate(keys):
            p = "%s[%d]" % (kpath, i)
            if not isinstance(key, dict):
                errs.add(p, "must be an object")
                continue
            _check_fields(key, ("frame", "value", "easing"), p, errs)
            if "frame" in key:
                f = key["frame"]
                if _is_int(f) and 0 <= f < duration:
                    if f in seen:
                        errs.add(p + ".frame", "duplicate frame")
                    seen.add(f)
                else:
                    errs.add(p + ".frame",
                             "must be an integer from 0 to %d" % (duration - 1))
            if "value" in key:
                v = key["value"]
                if not _is_number(v):
                    errs.add(p + ".value", "must be a finite number")
                elif v < lo or v > hi:
                    errs.add(p + ".value", "must be between %s and %s" % (lo, hi))
            if "easing" in key and key["easing"] not in EASINGS:
                errs.add(p + ".easing", "must be hold, linear or smoothstep")


def _validate_layer(layer, path, errs, width, height, duration):
    if not isinstance(layer, dict):
        errs.add(path, "must be an object")
        return None
    kind = layer.get("kind")
    kind_ok = isinstance(kind, str) and kind in KINDS
    required = list(COMMON_LAYER_FIELDS)
    if kind_ok:
        required += list(TEXT_FIELDS if kind == "text" else SHAPE_FIELDS)
    for name in required:
        if name not in layer:
            errs.add(_join(path, name), "is required")
    allowed = set(required) | {"tracks"}
    if kind_ok:
        for key in layer:
            if key not in allowed:
                errs.add(_join(path, _safe_key(key) if isinstance(key, str) else "?"),
                         "unknown field")
    layer_id = None
    if "id" in layer:
        if is_uuid(layer["id"]):
            layer_id = layer["id"]
        else:
            errs.add(_join(path, "id"), "must be a lowercase UUID")
    if "kind" in layer and not kind_ok:
        errs.add(_join(path, "kind"), "must be text, rectangle or ellipse")
    if "name" in layer:
        _check_str(layer["name"], _join(path, "name"), errs, 1, 60)
    if "x" in layer:
        _check_num(layer["x"], _join(path, "x"), errs, -2 * width, 2 * width)
    if "y" in layer:
        _check_num(layer["y"], _join(path, "y"), errs, -2 * height, 2 * height)
    if "opacity" in layer:
        _check_num(layer["opacity"], _join(path, "opacity"), errs, 0, 1)
    if "fill" in layer:
        _check_color(layer["fill"], _join(path, "fill"), errs)
    if kind_ok and kind == "text":
        if "text" in layer:
            _check_str(layer["text"], _join(path, "text"), errs, 1, 256,
                       allow_newline=True)
        if "font_size" in layer:
            _check_num(layer["font_size"], _join(path, "font_size"), errs, 8, 192)
        if "align" in layer and layer["align"] not in ALIGNS:
            errs.add(_join(path, "align"), "must be left, center or right")
    elif kind_ok:
        if "width" in layer:
            _check_num(layer["width"], _join(path, "width"), errs, 0, width,
                       lo_exclusive=True)
        if "height" in layer:
            _check_num(layer["height"], _join(path, "height"), errs, 0, height,
                       lo_exclusive=True)
    if "tracks" in layer:
        _validate_tracks(layer["tracks"], _join(path, "tracks"), errs,
                         2 * width, 2 * height, duration)
    return layer_id


def _validate(scene, errs):
    if not isinstance(scene, dict):
        errs.add("scene", "must be an object")
        return
    _check_fields(scene, SCENE_FIELDS, "", errs)

    if "schema_version" in scene:
        v = scene["schema_version"]
        if not _is_int(v) or v != 1:
            errs.add("schema_version", "must be 1")
    if "title" in scene:
        _check_str(scene["title"], "title", errs, 1, 80)

    preset = scene.get("preset")
    preset_ok = isinstance(preset, str) and preset in PRESETS
    if "preset" in scene and not preset_ok:
        errs.add("preset", "must be landscape or portrait")
    dims = PRESETS[preset] if preset_ok else None
    for field, idx in (("width", 0), ("height", 1)):
        if field in scene:
            v = scene[field]
            if not _is_int(v):
                errs.add(field, "must be an integer")
            elif dims is not None and v != dims[idx]:
                errs.add(field, "must be %d for the %s preset" % (dims[idx], preset))
            elif dims is None and v not in (720, 1280):
                errs.add(field, "must be 720 or 1280")
    if "fps" in scene:
        v = scene["fps"]
        if not _is_int(v) or v != FPS:
            errs.add("fps", "must be %d" % FPS)

    duration = MAX_DURATION
    if "duration_frames" in scene:
        v = scene["duration_frames"]
        if _is_int(v) and 1 <= v <= MAX_DURATION:
            duration = v
        else:
            errs.add("duration_frames",
                     "must be an integer from 1 to %d" % MAX_DURATION)
    if "background" in scene:
        _check_color(scene["background"], "background", errs)

    width, height = dims if dims else (1280, 720)
    if "layers" in scene:
        layers = scene["layers"]
        if not isinstance(layers, list):
            errs.add("layers", "must be an array")
        elif len(layers) > MAX_LAYERS:
            errs.add("layers", "must have at most %d layers" % MAX_LAYERS)
        else:
            seen = set()
            for i, layer in enumerate(layers):
                lid = _validate_layer(layer, "layers[%d]" % i, errs,
                                      width, height, duration)
                if lid is not None:
                    if lid in seen:
                        errs.add("layers[%d].id" % i, "duplicate layer id")
                    seen.add(lid)


def validate_scene(scene: object) -> list:
    """Return a list of {path, message}; empty means valid. Never raises."""
    errs = _Errors()
    try:
        _validate(scene, errs)
    except Exception:
        errs.add("scene", "could not be validated")
    return errs.items
