import os

import folder_paths
from comfy_api.latest import ComfyExtension, io

_MODEL_LUT_PATH = os.path.join(folder_paths.models_dir, "luts")
_REGISTERED_LUT_PATHS = folder_paths.folder_names_and_paths.get("luts")
if _REGISTERED_LUT_PATHS is None:
    folder_paths.folder_names_and_paths["luts"] = ([_MODEL_LUT_PATH], {".cube"})
else:
    lut_paths = list(_REGISTERED_LUT_PATHS[0])
    lut_extensions = set(_REGISTERED_LUT_PATHS[1])
    if _MODEL_LUT_PATH not in lut_paths:
        lut_paths.append(_MODEL_LUT_PATH)
    lut_extensions.add(".cube")
    folder_paths.folder_names_and_paths["luts"] = (lut_paths, lut_extensions)

from .nodes import (
    ProPostApplyLUT,
    ProPostChromaticAberration,
    ProPostColorWarper,
    ProPostDepthMapBlur,
    ProPostFilmGrain,
    ProPostFilmStockBW,
    ProPostFilmStockColor,
    ProPostLensDistortion,
    ProPostLensProfile,
    ProPostPrintStock,
    ProPostRadialBlur,
    ProPostSkinToneUniformity,
    ProPostVignette,
)

NODE_DEFINITIONS = [
    ("ProPostVignette", "ProPost Vignette", ProPostVignette),
    ("ProPostFilmGrain", "ProPost Film Grain", ProPostFilmGrain),
    ("ProPostRadialBlur", "ProPost Radial Blur", ProPostRadialBlur),
    ("ProPostDepthMapBlur", "ProPost Depth Map Blur", ProPostDepthMapBlur),
    ("ProPostApplyLUT", "ProPost Apply LUT", ProPostApplyLUT),
    ("ProPostPrintStock", "Print Stock", ProPostPrintStock),
    ("ProPostFilmStockBW", "Film Stock (B&W)", ProPostFilmStockBW),
    ("ProPostFilmStockColor", "Film Stock (Color)", ProPostFilmStockColor),
    ("ProPostLensDistortion", "Lens Distortion", ProPostLensDistortion),
    ("ProPostChromaticAberration", "Chromatic Aberration", ProPostChromaticAberration),
    ("ProPostLensProfile", "Lens Profile", ProPostLensProfile),
    ("ProPostColorWarper", "Color Warper", ProPostColorWarper),
    ("ProPostSkinToneUniformity", "Skin Tone Uniformity", ProPostSkinToneUniformity),
]


class ProPostTorchedExtension(ComfyExtension):
    async def get_node_list(self) -> list[type[io.ComfyNode]]:
        return [node_class for _, _, node_class in NODE_DEFINITIONS]


async def comfy_entrypoint() -> ComfyExtension:
    return ProPostTorchedExtension()


NODE_CLASS_MAPPINGS = {
    node_id: node_class
    for node_id, _, node_class in NODE_DEFINITIONS
}

NODE_DISPLAY_NAME_MAPPINGS = {
    node_id: display_name
    for node_id, display_name, _ in NODE_DEFINITIONS
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DEFINITIONS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "ProPostTorchedExtension",
    "comfy_entrypoint",
]
