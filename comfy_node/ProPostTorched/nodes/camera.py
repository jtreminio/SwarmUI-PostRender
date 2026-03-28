import torch
from comfy_api.latest import io

from ..filmgrainer import filmgrainer


class ProPostVignette(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostVignette",
            display_name="ProPost Vignette",
            category="Pro Post/Camera Effects",
            inputs=[
                io.Image.Input("image"),
                io.Float.Input("intensity", default=1.0, min=0.0, max=10.0, step=0.01),
                io.Float.Input("center_x", default=0.5, min=0.0, max=1.0, step=0.01),
                io.Float.Input("center_y", default=0.5, min=0.0, max=1.0, step=0.01),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, intensity: float,
                center_x: float, center_y: float) -> io.NodeOutput:
        if intensity == 0:
            return io.NodeOutput(image)

        _, height, width, _ = image.shape
        device = image.device

        x = torch.linspace(-1, 1, width, device=device) - (2 * center_x - 1)
        y = torch.linspace(-1, 1, height, device=device) - (2 * center_y - 1)
        yy, xx = torch.meshgrid(y, x, indexing="ij")

        max_dist = max(
            (center_x ** 2 + center_y ** 2) ** 0.5,
            ((1 - center_x) ** 2 + center_y ** 2) ** 0.5,
            (center_x ** 2 + (1 - center_y) ** 2) ** 0.5,
            ((1 - center_x) ** 2 + (1 - center_y) ** 2) ** 0.5,
        )
        radius = (xx ** 2 + yy ** 2).sqrt() / (max_dist * 2 ** 0.5)
        opacity = min(intensity, 1.0)
        vignette = (1.0 - radius * opacity).clamp(0.0, 1.0)
        vignette = vignette.unsqueeze(0).unsqueeze(-1)

        return io.NodeOutput((image * vignette).clamp(0.0, 1.0))


class ProPostFilmGrain(io.ComfyNode):
    GRAIN_TYPES = ["Fine", "Fine Simple", "Coarse", "Coarser"]

    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostFilmGrain",
            display_name="ProPost Film Grain",
            category="Pro Post/Camera Effects",
            inputs=[
                io.Image.Input("image"),
                io.Boolean.Input("gray_scale", default=False),
                io.Combo.Input("grain_type", options=cls.GRAIN_TYPES, default=cls.GRAIN_TYPES[0]),
                io.Float.Input("grain_sat", default=0.5, min=0.0, max=1.0, step=0.01),
                io.Float.Input("grain_power", default=0.7, min=0.0, max=1.0, step=0.01),
                io.Float.Input("shadows", default=0.2, min=0.0, max=1.0, step=0.01),
                io.Float.Input("highs", default=0.2, min=0.0, max=1.0, step=0.01),
                io.Float.Input("scale", default=1.0, min=0.0, max=10.0, step=0.01),
                io.Int.Input("sharpen", default=0, min=0, max=10),
                io.Float.Input("src_gamma", default=1.0, min=0.0, max=10.0, step=0.01),
                io.Int.Input("seed", default=1, min=1, max=1000),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, gray_scale: bool, grain_type: str,
                grain_sat: float, grain_power: float, shadows: float,
                highs: float, scale: float, sharpen: int,
                src_gamma: float, seed: int) -> io.NodeOutput:
        grain_type_index = cls.GRAIN_TYPES.index(grain_type) + 1
        results = []
        for batch_idx in range(image.shape[0]):
            result = filmgrainer.process(
                image[batch_idx], scale, src_gamma, grain_power, shadows, highs,
                grain_type_index, grain_sat, gray_scale, sharpen, seed + batch_idx
            )
            results.append(result)
        return io.NodeOutput(torch.stack(results))


__all__ = [
    "ProPostFilmGrain",
    "ProPostVignette",
]
