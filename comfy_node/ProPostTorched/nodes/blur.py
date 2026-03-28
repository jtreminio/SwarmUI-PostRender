import torch
import torch.nn.functional as F
from comfy_api.latest import io

from ..utils import processing as processing_utils
from ..utils.color_ops import rec709_weights


class ProPostRadialBlur(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostRadialBlur",
            display_name="ProPost Radial Blur",
            category="Pro Post/Blur Effects",
            inputs=[
                io.Image.Input("image"),
                io.Float.Input("blur_strength", default=64.0, min=0.0, max=256.0, step=1.0),
                io.Float.Input("center_x", default=0.5, min=0.0, max=1.0, step=0.01),
                io.Float.Input("center_y", default=0.5, min=0.0, max=1.0, step=0.01),
                io.Float.Input("focus_spread", default=1.0, min=0.1, max=8.0, step=0.1),
                io.Int.Input("steps", default=5, min=1, max=32),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, blur_strength: float,
                center_x: float, center_y: float,
                focus_spread: float, steps: int) -> io.NodeOutput:
        _, height, width, _ = image.shape
        device = image.device

        center_x_px = width * center_x
        center_y_px = height * center_y
        xs = torch.arange(width, dtype=torch.float32, device=device) - center_x_px
        ys = torch.arange(height, dtype=torch.float32, device=device) - center_y_px
        yy, xx = torch.meshgrid(ys, xs, indexing="ij")
        max_dist = max(
            (center_x_px ** 2 + center_y_px ** 2) ** 0.5,
            ((width - center_x_px) ** 2 + center_y_px ** 2) ** 0.5,
            (center_x_px ** 2 + (height - center_y_px) ** 2) ** 0.5,
            ((width - center_x_px) ** 2 + (height - center_y_px) ** 2) ** 0.5,
        )
        radial_mask = ((xx ** 2 + yy ** 2).sqrt() / max_dist).clamp(0.0, 1.0)

        image_4d = processing_utils.bhwc_to_nchw(image)
        blurred = processing_utils.generate_blurred_images(
            image_4d, blur_strength, steps, focus_spread)
        result = processing_utils.apply_blurred_images(image_4d, blurred, radial_mask)
        return io.NodeOutput(processing_utils.nchw_to_bhwc(result).clamp(0.0, 1.0))


class ProPostDepthMapBlur(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostDepthMapBlur",
            display_name="ProPost Depth Map Blur",
            category="Pro Post/Blur Effects",
            description=(
                "Applies blur based on a depth map while returning both the blurred image "
                "and the generated blur mask."
            ),
            inputs=[
                io.Image.Input("image"),
                io.Image.Input("depth_map"),
                io.Float.Input("blur_strength", default=64.0, min=0.0, max=256.0, step=1.0),
                io.Float.Input("focal_depth", default=1.0, min=0.0, max=1.0, step=0.01),
                io.Float.Input("focus_spread", default=1.0, min=1.0, max=8.0, step=0.1),
                io.Int.Input("steps", default=5, min=1, max=32),
                io.Float.Input("focal_range", default=0.0, min=0.0, max=1.0, step=0.01),
                io.Int.Input("mask_blur", default=1, min=1, max=127, step=2),
            ],
            outputs=[
                io.Image.Output("image"),
                io.Mask.Output("mask"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, depth_map: torch.Tensor,
                blur_strength: float, focal_depth: float,
                focus_spread: float, steps: int,
                focal_range: float, mask_blur: int) -> io.NodeOutput:
        _, height, width, _ = image.shape
        device = image.device

        image_4d = processing_utils.bhwc_to_nchw(image)
        depth_4d = processing_utils.bhwc_to_nchw(depth_map)
        if depth_4d.shape[2:] != (height, width):
            depth_4d = F.interpolate(
                depth_4d.float(), size=(height, width), mode="bilinear", align_corners=False)

        if depth_4d.shape[1] >= 3:
            depth_channels = depth_4d[:, :3].float()
            luma_weights = rec709_weights(device, depth_channels.dtype).view(1, 3, 1, 1)
            depth_gray = (depth_channels * luma_weights).sum(dim=1, keepdim=True)
        else:
            depth_gray = depth_4d[:, :1].float()

        depth_mask = (depth_gray - focal_depth).abs()
        mask_max = depth_mask.amax(dim=(2, 3), keepdim=True).clamp(min=1e-7)
        depth_mask = (depth_mask / mask_max).clamp(0.0, 1.0)

        depth_mask = torch.where(
            depth_mask < focal_range,
            torch.zeros_like(depth_mask),
            (depth_mask - focal_range) / (1.0 - focal_range + 1e-7)
        ).clamp(0.0, 1.0)

        if mask_blur > 1:
            kernel_size = mask_blur if mask_blur % 2 == 1 else mask_blur + 1
            depth_mask = processing_utils.gaussian_blur(depth_mask, kernel_size).clamp(0.0, 1.0)

        blurred = processing_utils.generate_blurred_images(
            image_4d, blur_strength, steps, focus_spread)
        result = processing_utils.apply_blurred_images(image_4d, blurred, depth_mask)

        output_images = processing_utils.nchw_to_bhwc(result).clamp(0.0, 1.0)
        output_masks = depth_mask.squeeze(1)
        return io.NodeOutput(output_images, output_masks)


__all__ = [
    "ProPostDepthMapBlur",
    "ProPostRadialBlur",
]
