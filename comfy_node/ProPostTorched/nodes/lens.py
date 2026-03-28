import torch
from comfy_api.latest import io

from ..data.lens_profiles import LENS_PROFILES_FLAT, LENS_PROFILE_NAMES
from ..utils import geometry as geometry_utils
from ..utils import processing as processing_utils

_LENS_WITH_CUSTOM = ["Custom"] + LENS_PROFILE_NAMES


def _sample_reflection_channel(image_4d: torch.Tensor, channel_index: int,
                               grid: torch.Tensor | None) -> torch.Tensor:
    channel = image_4d[:, channel_index:channel_index + 1]
    if grid is None:
        return channel
    return geometry_utils.sample_nchw(
        channel,
        grid,
        mode="bilinear",
        padding_mode="reflection",
        align_corners=False,
    )


class ProPostLensDistortion(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostLensDistortion",
            display_name="Lens Distortion",
            category="Pro Post/Lens",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("lens", options=_LENS_WITH_CUSTOM, default="Custom"),
                io.Float.Input("strength", default=1.0, min=-2.0, max=2.0, step=0.1),
                io.Float.Input("k1", default=0.0, min=-1.0, max=1.0, step=0.01),
                io.Float.Input("k2", default=0.0, min=-0.5, max=0.5, step=0.01),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, lens: str, strength: float,
                k1: float, k2: float) -> io.NodeOutput:
        if lens != "Custom" and lens in LENS_PROFILES_FLAT:
            profile = LENS_PROFILES_FLAT[lens]
            k1 = profile.k1
            k2 = profile.k2

        k1 *= strength
        k2 *= strength
        if abs(k1) < 0.001 and abs(k2) < 0.001:
            return io.NodeOutput(image)

        _, height, width, _ = image.shape
        grid = geometry_utils.build_distortion_grid(
            height,
            width,
            k1,
            k2,
            image.device,
            image.dtype,
            batch_size=image.shape[0],
            align_corners=False,
        )
        result = geometry_utils.sample_bhwc(
            image,
            grid,
            mode="bilinear",
            padding_mode="zeros",
            align_corners=False,
        )
        return io.NodeOutput(result.clamp(0.0, 1.0))


class ProPostChromaticAberration(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostChromaticAberration",
            display_name="Chromatic Aberration",
            category="Pro Post/Lens",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("lens", options=_LENS_WITH_CUSTOM, default="Custom"),
                io.Float.Input("strength", default=1.0, min=0.0, max=3.0, step=0.1),
                io.Float.Input("shift_r", default=-1.0, min=-5.0, max=5.0, step=0.1),
                io.Float.Input("shift_b", default=1.0, min=-5.0, max=5.0, step=0.1),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, lens: str, strength: float,
                shift_r: float, shift_b: float) -> io.NodeOutput:
        if strength <= 0.0:
            return io.NodeOutput(image)

        if lens != "Custom" and lens in LENS_PROFILES_FLAT:
            profile = LENS_PROFILES_FLAT[lens]
            shift_r = profile.ca_r
            shift_b = profile.ca_b

        _, height, width, _ = image.shape
        scale = min(height, width) / 1024.0
        shift_r = shift_r * strength * scale
        shift_b = shift_b * strength * scale
        if abs(shift_r) < 0.01 and abs(shift_b) < 0.01:
            return io.NodeOutput(image)

        image_4d = processing_utils.bhwc_to_nchw(image)
        channels = [image_4d[:, 0:1], image_4d[:, 1:2], image_4d[:, 2:3]]

        for channel_index, shift in ((0, shift_r), (2, shift_b)):
            if abs(shift) < 0.01:
                continue
            grid = geometry_utils.build_lateral_ca_grid(
                height,
                width,
                shift,
                image.device,
                image.dtype,
                batch_size=image.shape[0],
                align_corners=False,
            )
            channels[channel_index] = _sample_reflection_channel(image_4d, channel_index, grid)

        result = torch.cat(channels, dim=1)
        return io.NodeOutput(processing_utils.nchw_to_bhwc(result).clamp(0.0, 1.0))


class ProPostLensProfile(io.ComfyNode):
    _PROFILE_MODES = ["Add Aberrations", "Correct Aberrations"]

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostLensProfile",
            display_name="Lens Profile",
            category="Pro Post/Lens",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("lens", options=LENS_PROFILE_NAMES, default=LENS_PROFILE_NAMES[0]),
                io.Combo.Input("mode", options=cls._PROFILE_MODES, default=cls._PROFILE_MODES[0]),
                io.Float.Input("strength", default=1.0, min=0.0, max=2.0, step=0.1),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, lens: str, mode: str,
                strength: float) -> io.NodeOutput:
        if strength < 0.01 or lens not in LENS_PROFILES_FLAT:
            return io.NodeOutput(image)

        profile = LENS_PROFILES_FLAT[lens]
        sign = 1.0 if mode == "Add Aberrations" else -1.0
        k1 = profile.k1 * strength * sign
        k2 = profile.k2 * strength * sign
        ca_r = profile.ca_r * strength * sign
        ca_b = profile.ca_b * strength * sign
        vig_strength = profile.vig_strength * strength
        vig_midpoint = profile.vig_midpoint

        batch_size, height, width, _ = image.shape
        scale = min(height, width) / 1024.0
        image_4d = processing_utils.bhwc_to_nchw(image)

        distortion_grid = geometry_utils.build_distortion_grid(
            height,
            width,
            k1,
            k2,
            image.device,
            image.dtype,
            batch_size=batch_size,
            align_corners=False,
        )
        distorted = geometry_utils.sample_nchw(
            image_4d,
            distortion_grid,
            mode="bilinear",
            padding_mode="reflection",
            align_corners=False,
        )

        channels = [distorted[:, 0:1], distorted[:, 1:2], distorted[:, 2:3]]

        ca_r_scaled = ca_r * scale
        ca_b_scaled = ca_b * scale

        for channel_index, shift in ((0, ca_r_scaled), (2, ca_b_scaled)):
            if abs(shift) < 0.01:
                continue
            grid = geometry_utils.build_lens_profile_channel_grid(
                height,
                width,
                k1,
                k2,
                shift,
                image.device,
                image.dtype,
                batch_size=batch_size,
                align_corners=False,
            )
            channels[channel_index] = _sample_reflection_channel(image_4d, channel_index, grid)

        result = torch.cat(channels, dim=1)

        if vig_strength > 0.01:
            base = geometry_utils.get_centered_grid(height, width, image.device, image.dtype)
            cos_theta = 1.0 / torch.sqrt(1.0 + base["r2"])
            falloff = cos_theta.pow(4.0)
            transition = ((base["r"] - vig_midpoint * 0.8) / 0.4).clamp(0.0, 1.0)
            if mode == "Add Aberrations":
                mask = 1.0 - transition * (1.0 - falloff) * vig_strength * 2.0
                result = result * mask.clamp(0.0, 1.0).unsqueeze(1)
            else:
                correction = 1.0 + transition * (1.0 / falloff.clamp(0.3, 1.0) - 1.0) * vig_strength
                result = result * correction.unsqueeze(1)

        return io.NodeOutput(processing_utils.nchw_to_bhwc(result).clamp(0.0, 1.0))


__all__ = [
    "ProPostChromaticAberration",
    "ProPostLensDistortion",
    "ProPostLensProfile",
]
