import folder_paths
import torch
from comfy_api.latest import io

from ..utils import lut_ops


class ProPostApplyLUT(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostApplyLUT",
            display_name="ProPost Apply LUT",
            category="Pro Post/Color Grading",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("lut_name", options=folder_paths.get_filename_list("luts")),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.01),
                io.Boolean.Input("log", default=False),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, lut_name: str, strength: float, log: bool) -> io.NodeOutput:
        if strength == 0:
            return io.NodeOutput(image)

        lut_out = lut_ops.apply_lut(image, lut_name, log)
        return io.NodeOutput((image + strength * (lut_out - image)).clamp(0.0, 1.0))


__all__ = [
    "ProPostApplyLUT",
]
