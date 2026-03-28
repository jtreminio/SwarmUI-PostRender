import torch
from comfy_api.latest import io

from ..data.grading_presets import (
    COLOR_WARPER_CUSTOM_PRESET,
    COLOR_WARPER_PRESETS,
    COLOR_WARPER_PRESET_DEFAULT,
    COLOR_WARPER_PRESET_NAMES,
    SKIN_TONE_PRESETS,
    SKIN_TONE_PRESET_DEFAULT,
    SKIN_TONE_PRESET_NAMES,
)
from ..utils import processing as processing_utils
from ..utils.color_ops import (
    blend,
    circular_hue_difference,
    hsl_to_rgb,
    hue_range_mask,
    linear_to_srgb,
    rgb_to_hsl,
    sat_range_weight,
    soft_range_mask,
    srgb_to_linear,
)

def _image_to_linear_hsl(image: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    # Keep both grading nodes in the same linear-light HSL working space.
    linear = srgb_to_linear(image)
    hue, sat, lum = rgb_to_hsl(linear)
    return linear, hue, sat, lum


class ProPostColorWarper(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostColorWarper",
            display_name="Color Warper",
            category="Pro Post/Color Grading",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("preset", options=COLOR_WARPER_PRESET_NAMES, default=COLOR_WARPER_PRESET_DEFAULT),
                io.Float.Input("source_hue", default=0.0, min=0.0, max=360.0, step=1.0),
                io.Float.Input("source_hue_width", default=60.0, min=10.0, max=180.0, step=1.0),
                io.Float.Input("source_sat_min", default=0.0, min=0.0, max=1.0, step=0.01),
                io.Float.Input("source_sat_max", default=1.0, min=0.0, max=1.0, step=0.01),
                io.Float.Input("hue_shift", default=0.0, min=-180.0, max=180.0, step=1.0),
                io.Float.Input("sat_shift", default=0.0, min=-100.0, max=100.0, step=1.0),
                io.Float.Input("feather", default=0.5, min=0.1, max=1.0, step=0.05),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.05),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    def _apply_region(cls, hue: torch.Tensor, sat: torch.Tensor, src_hue: float,
                      src_hue_width: float, src_sat_min: float, src_sat_max: float,
                      hue_shift: float, sat_shift: float, feather: float) -> tuple[torch.Tensor, torch.Tensor]:
        hue_mask = hue_range_mask(hue, src_hue, width=src_hue_width, softness=feather)
        sat_mask = sat_range_weight(sat, src_sat_min, src_sat_max, softness=0.05 + feather * 0.1)
        combined_mask = hue_mask * sat_mask

        if abs(hue_shift) > 0.1:
            hue = torch.remainder(hue + combined_mask * hue_shift, 360.0)
        if abs(sat_shift) > 0.5:
            sat = (sat * (1.0 + combined_mask * (sat_shift / 100.0))).clamp(0.0, 1.0)
        return hue, sat

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, preset: str, source_hue: float,
                source_hue_width: float, source_sat_min: float, source_sat_max: float,
                hue_shift: float, sat_shift: float, feather: float,
                strength: float) -> io.NodeOutput:
        if strength <= 0.0:
            return io.NodeOutput(image)

        use_preset = preset != COLOR_WARPER_CUSTOM_PRESET and preset in COLOR_WARPER_PRESETS
        if not use_preset and abs(hue_shift) < 0.1 and abs(sat_shift) < 0.5:
            return io.NodeOutput(image)

        _, hue, sat, lum = _image_to_linear_hsl(image)

        if use_preset:
            for region in COLOR_WARPER_PRESETS[preset].regions:
                hue, sat = cls._apply_region(
                    hue,
                    sat,
                    region.src_hue,
                    region.src_hue_width,
                    region.src_sat_min,
                    region.src_sat_max,
                    region.hue_shift,
                    region.sat_shift,
                    feather,
                )
            if abs(hue_shift) > 0.1 or abs(sat_shift) > 0.5:
                hue, sat = cls._apply_region(
                    hue,
                    sat,
                    source_hue,
                    source_hue_width,
                    source_sat_min,
                    source_sat_max,
                    hue_shift,
                    sat_shift,
                    feather,
                )
        else:
            hue, sat = cls._apply_region(
                hue,
                sat,
                source_hue,
                source_hue_width,
                source_sat_min,
                source_sat_max,
                hue_shift,
                sat_shift,
                feather,
            )

        result = linear_to_srgb(hsl_to_rgb(hue, sat, lum))
        return io.NodeOutput(blend(image, result, strength).clamp(0.0, 1.0))


class ProPostSkinToneUniformity(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostSkinToneUniformity",
            display_name="Skin Tone Uniformity",
            category="Pro Post/Color Grading",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("preset", options=SKIN_TONE_PRESET_NAMES, default=SKIN_TONE_PRESET_DEFAULT),
                io.Float.Input("amount", default=60.0, min=0.0, max=100.0, step=1.0),
                io.Float.Input("smoothing_radius", default=60.0, min=10.0, max=100.0, step=1.0),
                io.Float.Input("hue_center", default=25.0, min=0.0, max=360.0, step=1.0),
                io.Float.Input("hue_width", default=45.0, min=10.0, max=90.0, step=1.0),
                io.Float.Input("saturation_min", default=0.08, min=0.0, max=0.5, step=0.01),
                io.Float.Input("saturation_max", default=0.85, min=0.3, max=1.0, step=0.01),
                io.Float.Input("luminance_min", default=0.10, min=0.0, max=0.5, step=0.01),
                io.Float.Input("luminance_max", default=0.92, min=0.5, max=1.0, step=0.01),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.05),
            ],
            outputs=[
                io.Image.Output("image"),
                io.Image.Output("mask_preview"),
            ],
        )

    @classmethod
    def _skin_mask(cls, hue: torch.Tensor, sat: torch.Tensor, lum: torch.Tensor,
                   hue_center: float, hue_width: float, sat_min: float, sat_max: float,
                   lum_min: float, lum_max: float) -> torch.Tensor:
        hue_weight = hue_range_mask(hue, hue_center, width=hue_width, softness=1.0)
        sat_weight = soft_range_mask(sat, sat_min, sat_max, 0.08)
        lum_weight = soft_range_mask(lum, lum_min, lum_max, 0.10)
        return hue_weight * sat_weight * lum_weight

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, preset: str, amount: float, smoothing_radius: float,
                hue_center: float, hue_width: float, saturation_min: float,
                saturation_max: float, luminance_min: float, luminance_max: float,
                strength: float) -> io.NodeOutput:
        preset_values = SKIN_TONE_PRESETS.get(preset)
        if preset_values is not None:
            hue_center = preset_values.hue_center
            hue_width = preset_values.hue_width
            saturation_min = preset_values.saturation_min
            saturation_max = preset_values.saturation_max
            luminance_min = preset_values.luminance_min
            luminance_max = preset_values.luminance_max

        batch_size, height, width, _ = image.shape
        _, hue, sat, lum = _image_to_linear_hsl(image)
        mask = cls._skin_mask(
            hue,
            sat,
            lum,
            hue_center,
            hue_width,
            saturation_min,
            saturation_max,
            luminance_min,
            luminance_max,
        )

        mask_4d = mask.unsqueeze(1)
        edge_sigma = max(height, width) * 0.015
        mask_smooth = processing_utils.gaussian_blur_auto(mask_4d, edge_sigma, padding_mode="reflect").clamp(0.0, 1.0)
        mask_smooth_2d = mask_smooth.squeeze(1)
        mask_preview = mask_smooth_2d.unsqueeze(-1).expand(batch_size, height, width, 3)

        if strength <= 0.0 or amount < 0.5:
            return io.NodeOutput(image, mask_preview.clamp(0.0, 1.0))

        scale = max(height, width) / 1024.0
        target_sigma = (smoothing_radius / 100.0) * 40.0 * scale

        hue_radians = hue * (torch.pi / 180.0)
        values = torch.stack([
            torch.sin(hue_radians),
            torch.cos(hue_radians),
            sat,
        ], dim=1)
        averages, _ = processing_utils.gaussian_weighted_average(
            values,
            mask_smooth,
            target_sigma,
            padding_mode="reflect",
        )

        target_hue = torch.remainder(torch.atan2(averages[:, 0], averages[:, 1]) * (180.0 / torch.pi), 360.0)
        target_sat = averages[:, 2].clamp(0.0, 1.0)

        pull = amount / 100.0
        hue_delta = circular_hue_difference(target_hue, hue)
        hue_new = torch.remainder(hue + mask_smooth_2d * pull * hue_delta, 360.0)
        sat_new = (sat + mask_smooth_2d * pull * (target_sat - sat)).clamp(0.0, 1.0)

        result = linear_to_srgb(hsl_to_rgb(hue_new, sat_new, lum)).clamp(0.0, 1.0)
        return io.NodeOutput(
            blend(image, result, strength).clamp(0.0, 1.0),
            mask_preview.clamp(0.0, 1.0),
        )


__all__ = [
    "ProPostColorWarper",
    "ProPostSkinToneUniformity",
]
