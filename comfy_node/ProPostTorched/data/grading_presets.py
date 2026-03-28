from dataclasses import dataclass

from .catalog_loader import (
    get_catalog_default,
    get_catalog_list,
    validate_catalog_default,
    validate_catalog_entries,
)


@dataclass(frozen=True)
class ColorWarperRegion:
    src_hue: float
    src_hue_width: float
    src_sat_min: float
    src_sat_max: float
    hue_shift: float
    sat_shift: float


@dataclass(frozen=True)
class ColorWarperPreset:
    name: str
    regions: tuple[ColorWarperRegion, ...]


@dataclass(frozen=True)
class SkinTonePreset:
    name: str
    hue_center: float
    hue_width: float
    saturation_min: float
    saturation_max: float
    luminance_min: float
    luminance_max: float


COLOR_WARPER_PRESETS = {
    "Orange & Teal push": ColorWarperPreset(
        name="Orange & Teal push",
        regions=(
            ColorWarperRegion(25, 60, 0.1, 1.0, 10, 20),
            ColorWarperRegion(200, 80, 0.1, 1.0, -15, 25),
        ),
    ),
    "Skin tone cleanup": ColorWarperPreset(
        name="Skin tone cleanup",
        regions=(
            ColorWarperRegion(20, 40, 0.15, 0.8, 5, -10),
            ColorWarperRegion(45, 30, 0.1, 0.6, -10, -5),
        ),
    ),
    "Sky blue intensify": ColorWarperPreset(
        name="Sky blue intensify",
        regions=(
            ColorWarperRegion(210, 70, 0.1, 1.0, 0, 40),
            ColorWarperRegion(190, 50, 0.1, 0.8, 10, 25),
        ),
    ),
    "Green -> teal shift": ColorWarperPreset(
        name="Green -> teal shift",
        regions=(
            ColorWarperRegion(120, 60, 0.1, 1.0, 50, 10),
            ColorWarperRegion(90, 40, 0.1, 0.8, 30, 5),
        ),
    ),
    "Warm color expansion": ColorWarperPreset(
        name="Warm color expansion",
        regions=(
            ColorWarperRegion(15, 50, 0.15, 1.0, 0, 30),
            ColorWarperRegion(35, 50, 0.15, 1.0, 0, 25),
            ColorWarperRegion(55, 40, 0.1, 1.0, 0, 20),
        ),
    ),
    "Cool color expansion": ColorWarperPreset(
        name="Cool color expansion",
        regions=(
            ColorWarperRegion(190, 50, 0.1, 1.0, 0, 30),
            ColorWarperRegion(230, 60, 0.1, 1.0, 0, 25),
            ColorWarperRegion(270, 40, 0.1, 1.0, 0, 20),
        ),
    ),
    "Complementary contrast": ColorWarperPreset(
        name="Complementary contrast",
        regions=(
            ColorWarperRegion(30, 70, 0.1, 1.0, 0, 30),
            ColorWarperRegion(210, 70, 0.1, 1.0, 0, 30),
            ColorWarperRegion(120, 60, 0.1, 0.8, 0, -25),
        ),
    ),
    "Monochromatic squeeze": ColorWarperPreset(
        name="Monochromatic squeeze",
        regions=(
            ColorWarperRegion(0, 180, 0.0, 0.3, 0, -50),
            ColorWarperRegion(0, 180, 0.3, 0.6, 0, -30),
        ),
    ),
    "Sunset spectrum enhance": ColorWarperPreset(
        name="Sunset spectrum enhance",
        regions=(
            ColorWarperRegion(0, 40, 0.15, 1.0, -5, 35),
            ColorWarperRegion(30, 40, 0.15, 1.0, 5, 40),
            ColorWarperRegion(55, 35, 0.1, 1.0, -5, 30),
            ColorWarperRegion(270, 50, 0.1, 1.0, 10, 20),
        ),
    ),
}

COLOR_WARPER_CUSTOM_PRESET = "Custom (manual)"
COLOR_WARPER_PRESET_NAMES = get_catalog_list("grading_options.json", "color_warper_presets")
if not COLOR_WARPER_PRESET_NAMES or COLOR_WARPER_PRESET_NAMES[0] != COLOR_WARPER_CUSTOM_PRESET:
    raise ValueError("Color warper presets must keep Custom (manual) as the first entry")
validate_catalog_entries(
    "color warper presets",
    COLOR_WARPER_PRESET_NAMES[1:],
    COLOR_WARPER_PRESETS.keys(),
)
COLOR_WARPER_PRESET_DEFAULT = validate_catalog_default(
    "color warper preset",
    get_catalog_default("grading_options.json", "color_warper_preset"),
    COLOR_WARPER_PRESET_NAMES,
)

SKIN_TONE_CUSTOM_PRESET = "Custom"
SKIN_TONE_PRESETS = {
    "Universal - all skin tones": SkinTonePreset("Universal - all skin tones", 25.0, 45.0, 0.08, 0.85, 0.10, 0.92),
    "Light / Fair skin": SkinTonePreset("Light / Fair skin", 20.0, 30.0, 0.10, 0.65, 0.40, 0.92),
    "Medium / Olive skin": SkinTonePreset("Medium / Olive skin", 25.0, 35.0, 0.12, 0.75, 0.25, 0.80),
    "Dark / Deep skin": SkinTonePreset("Dark / Deep skin", 22.0, 40.0, 0.10, 0.80, 0.08, 0.55),
    "Warm / Golden skin": SkinTonePreset("Warm / Golden skin", 30.0, 35.0, 0.15, 0.80, 0.20, 0.85),
    "Cool / Pink skin": SkinTonePreset("Cool / Pink skin", 12.0, 30.0, 0.10, 0.70, 0.30, 0.90),
}
SKIN_TONE_PRESET_NAMES = get_catalog_list("grading_options.json", "skin_tone_presets")
if not SKIN_TONE_PRESET_NAMES or SKIN_TONE_PRESET_NAMES[-1] != SKIN_TONE_CUSTOM_PRESET:
    raise ValueError("Skin tone presets must keep Custom as the final entry")
validate_catalog_entries(
    "skin tone presets",
    SKIN_TONE_PRESET_NAMES[:-1],
    SKIN_TONE_PRESETS.keys(),
)
SKIN_TONE_PRESET_DEFAULT = validate_catalog_default(
    "skin tone preset",
    get_catalog_default("grading_options.json", "skin_tone_preset"),
    SKIN_TONE_PRESET_NAMES,
)
