import copy
import unittest

from motion_studio.scene import PRESETS, canonical_json, new_scene, validate_scene

from helpers import shape_layer, text_layer, with_layers


def paths(errors):
    return [e["path"] for e in errors]


class TemplateTests(unittest.TestCase):
    def test_blank_is_valid_for_both_presets(self):
        for preset, (w, h) in PRESETS.items():
            scene = new_scene("Blank fixture", "blank", preset)
            self.assertEqual(validate_scene(scene), [])
            self.assertEqual((scene["width"], scene["height"]), (w, h))
            self.assertEqual(scene["layers"], [])
            self.assertEqual(scene["schema_version"], 1)
            self.assertEqual(scene["fps"], 30)

    def test_title_card_has_three_valid_layers(self):
        for preset in PRESETS:
            scene = new_scene("Card fixture", "title_card", preset)
            self.assertEqual(validate_scene(scene), [])
            self.assertEqual(len(scene["layers"]), 3)
            self.assertEqual(len({l["id"] for l in scene["layers"]}), 3)

    def test_portrait_dimensions(self):
        scene = new_scene("Portrait", "blank", "portrait")
        self.assertEqual((scene["width"], scene["height"]), (720, 1280))


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.base = new_scene("Validation fixture", "blank", "landscape")

    def test_non_object(self):
        self.assertTrue(validate_scene([]))
        self.assertTrue(validate_scene(None))

    def test_unknown_and_missing_fields(self):
        scene = copy.deepcopy(self.base)
        scene["extra"] = 1
        self.assertTrue(validate_scene(scene))
        del scene["extra"]
        del scene["background"]
        self.assertTrue(validate_scene(scene))

    def test_dimension_preset_mismatch(self):
        scene = copy.deepcopy(self.base)
        scene["width"], scene["height"] = 720, 1280
        self.assertTrue(validate_scene(scene))

    def test_duration_bounds_and_bool(self):
        for bad in (0, 301, 1.5, True, "150"):
            scene = copy.deepcopy(self.base)
            scene["duration_frames"] = bad
            self.assertTrue(validate_scene(scene), bad)
        for good in (1, 300):
            scene = copy.deepcopy(self.base)
            scene["duration_frames"] = good
            self.assertEqual(validate_scene(scene), [], good)

    def test_fps_must_be_30(self):
        scene = copy.deepcopy(self.base)
        scene["fps"] = 24
        self.assertTrue(validate_scene(scene))

    def test_background_format(self):
        for bad in ("#FFFFFF", "ffffff", "#fff", "#gggggg", 5):
            scene = copy.deepcopy(self.base)
            scene["background"] = bad
            self.assertTrue(validate_scene(scene), bad)

    def test_title_rules(self):
        for bad in ("", "x" * 81, "bad\x00title", 3):
            scene = copy.deepcopy(self.base)
            scene["title"] = bad
            self.assertTrue(validate_scene(scene), repr(bad))

    def test_valid_layers_of_each_kind(self):
        scene = with_layers(self.base, shape_layer("rectangle"), shape_layer("ellipse"), text_layer())
        self.assertEqual(validate_scene(scene), [])

    def test_duplicate_layer_ids(self):
        a = shape_layer()
        b = shape_layer(id=a["id"])
        self.assertTrue(validate_scene(with_layers(self.base, a, b)))

    def test_layer_cap(self):
        layers = [shape_layer() for _ in range(33)]
        self.assertTrue(validate_scene(with_layers(self.base, *layers)))
        self.assertEqual(validate_scene(with_layers(self.base, *layers[:32])), [])

    def test_position_bounds(self):
        self.assertEqual(validate_scene(with_layers(self.base, shape_layer(x=-2560, y=1440))), [])
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(x=2561))))
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(y=-1441))))

    def test_opacity_bounds(self):
        for bad in (-0.01, 1.01, True, "1"):
            self.assertTrue(validate_scene(with_layers(self.base, shape_layer(opacity=bad))), bad)

    def test_non_finite_numbers(self):
        for bad in (float("nan"), float("inf")):
            self.assertTrue(validate_scene(with_layers(self.base, shape_layer(x=bad))))

    def test_shape_size_bounds(self):
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(width=0))))
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(width=1281))))
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(height=721))))
        self.assertEqual(validate_scene(with_layers(self.base, shape_layer(width=1280, height=720))), [])

    def test_text_rules(self):
        self.assertEqual(validate_scene(with_layers(self.base, text_layer(text="Line one\nLine two"))), [])
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(text=""))))
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(text="x" * 257))))
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(text="tab\there"))))
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(font_size=7))))
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(font_size=193))))
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(align="justify"))))

    def test_text_layer_rejects_width_height(self):
        self.assertTrue(validate_scene(with_layers(self.base, text_layer(width=10, height=10))))

    def test_unknown_kind_and_extra_layer_field(self):
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(kind="star"))))
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(rotation=3))))

    def test_bad_layer_id(self):
        self.assertTrue(validate_scene(with_layers(self.base, shape_layer(id="not-a-uuid"))))

    def test_error_paths_point_at_the_layer(self):
        errors = validate_scene(with_layers(self.base, shape_layer(), shape_layer(opacity=2)))
        self.assertIn("layers[1].opacity", paths(errors))

    def test_empty_tracks_allowed(self):
        for tracks in ({}, {"x": [], "y": [], "opacity": []}):
            self.assertEqual(validate_scene(with_layers(self.base, shape_layer(tracks=tracks))), [])

    def test_valid_track_keys(self):
        tracks = {"x": [{"frame": 0, "value": 32, "easing": "linear"},
                        {"frame": 60, "value": 272, "easing": "hold"}],
                  "opacity": [{"frame": 0, "value": 0, "easing": "smoothstep"}]}
        self.assertEqual(validate_scene(with_layers(self.base, shape_layer(tracks=tracks))), [])

    def test_invalid_track_keys(self):
        key = {"frame": 0, "value": 1, "easing": "linear"}
        cases = [
            {"x": [key, dict(key)]},                                  # duplicate frame
            {"x": [{"frame": 150, "value": 1, "easing": "linear"}]},  # beyond duration 150
            {"x": [{"frame": -1, "value": 1, "easing": "linear"}]},
            {"x": [{"frame": 0, "value": 1, "easing": "cubic"}]},
            {"opacity": [{"frame": 0, "value": 2, "easing": "hold"}]},
            {"rotation": []},
            {"x": [{"frame": i, "value": 0, "easing": "hold"} for i in range(65)]},
        ]
        for tracks in cases:
            self.assertTrue(validate_scene(with_layers(self.base, shape_layer(tracks=tracks))), tracks)

    def test_canonical_json_is_stable(self):
        self.assertEqual(canonical_json({"b": 1, "a": [1, 2]}), '{"a":[1,2],"b":1}')
        self.assertEqual(canonical_json({"t": "é"}), '{"t":"é"}')


if __name__ == "__main__":
    unittest.main()
