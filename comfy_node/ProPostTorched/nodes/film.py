import torch
from comfy_api.latest import io

from ..data.film_stocks import (
    BW_STOCKS,
    BW_STOCK_NAMES,
    COLOR_FILTERS,
    COLOR_STOCKS,
    COLOR_STOCK_NAMES,
    FILTER_NAMES,
    CurveParams,
)
from ..data.print_stocks import PRINT_STOCKS, PRINT_STOCK_NAMES
from ..utils.color_ops import (
    adjust_saturation,
    apply_per_channel_curves,
    blend,
    characteristic_curve,
    curve_params_from_channels,
    linear_to_srgb,
    split_tone,
    srgb_to_linear,
)

_PRINT_CURVE_CACHE: dict[tuple[str, str, str], tuple[torch.Tensor, ...]] = {}
_COLOR_CURVE_CACHE: dict[tuple[str, str, str], tuple[torch.Tensor, ...]] = {}
_BW_WEIGHT_CACHE: dict[tuple[str, str, str, str], torch.Tensor] = {}


def _cached_curve_params(cache: dict, cache_name: str, curves, device: torch.device,
                         dtype: torch.dtype) -> tuple[torch.Tensor, ...]:
    key = (cache_name, str(device), str(dtype))
    if key not in cache:
        cache[key] = curve_params_from_channels(curves, device, dtype)
    return cache[key]


def _bw_weights(film_stock: str, color_filter: str, device: torch.device,
                dtype: torch.dtype) -> torch.Tensor:
    key = (film_stock, color_filter, str(device), str(dtype))
    if key not in _BW_WEIGHT_CACHE:
        stock = BW_STOCKS[film_stock]
        filter_mult = COLOR_FILTERS[color_filter]
        weights = torch.tensor(
            [
                stock.red_weight * filter_mult[0],
                stock.green_weight * filter_mult[1],
                stock.blue_weight * filter_mult[2],
            ],
            device=device,
            dtype=dtype,
        )
        weights = weights / weights.sum().clamp(min=1e-7)
        _BW_WEIGHT_CACHE[key] = weights.view(1, 1, 1, 3)
    return _BW_WEIGHT_CACHE[key]


class ProPostPrintStock(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostPrintStock",
            display_name="Print Stock",
            category="Pro Post/Film",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("print_stock", options=PRINT_STOCK_NAMES, default="Kodak 2383"),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.05),
                io.Float.Input("contrast_boost", default=0.0, min=0.0, max=1.0, step=0.05),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, print_stock: str, strength: float,
                contrast_boost: float) -> io.NodeOutput:
        if strength <= 0.0:
            return io.NodeOutput(image)

        stock = PRINT_STOCKS[print_stock]
        linear = srgb_to_linear(image)
        curve_params = _cached_curve_params(
            _PRINT_CURVE_CACHE,
            print_stock,
            (stock.r_curve, stock.g_curve, stock.b_curve),
            image.device,
            image.dtype,
        )
        printed = apply_per_channel_curves(linear, curve_params)
        if abs(stock.saturation - 1.0) > 0.001:
            printed = adjust_saturation(printed, stock.saturation)
        if stock.black_density > 0.0:
            printed = printed * (1.0 - stock.black_density) + stock.black_density
        if contrast_boost > 0.01:
            midpoint = torch.tensor(0.18, device=image.device, dtype=image.dtype)
            boost = 1.0 + contrast_boost * 0.5
            printed = torch.where(
                printed > midpoint,
                midpoint + (printed - midpoint) * boost,
                midpoint - (midpoint - printed) * boost,
            ).clamp(0.0, 1.0)
        result = linear_to_srgb(printed)
        return io.NodeOutput(blend(image, result, strength).clamp(0.0, 1.0))


class ProPostFilmStockBW(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostFilmStockBW",
            display_name="Film Stock (B&W)",
            category="Pro Post/Film",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("film_stock", options=BW_STOCK_NAMES, default="Ilford HP5 Plus 400"),
                io.Combo.Input("color_filter", options=FILTER_NAMES, default="None"),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.05),
                io.Float.Input("contrast", default=0.0, min=-1.0, max=1.0, step=0.05),
                io.Float.Input("exposure_shift", default=0.0, min=-3.0, max=3.0, step=0.25),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, film_stock: str, color_filter: str,
                strength: float, contrast: float, exposure_shift: float) -> io.NodeOutput:
        if strength <= 0.0:
            return io.NodeOutput(image)

        stock = BW_STOCKS[film_stock]
        curve = stock.contrast_curve
        if abs(contrast) > 0.01:
            slope = max(curve.slope + contrast * 0.3, 0.3)
            toe = max(curve.toe_power + contrast * 0.2, 0.5)
            shoulder = max(curve.shoulder_power - contrast * 0.15, 0.5)
        else:
            slope = curve.slope
            toe = curve.toe_power
            shoulder = curve.shoulder_power

        linear = srgb_to_linear(image)
        weights = _bw_weights(film_stock, color_filter, image.device, image.dtype)
        bw = (linear * weights).sum(dim=-1)
        if abs(exposure_shift) > 0.01:
            bw = (bw * (2.0 ** exposure_shift)).clamp(0.0, 1.0)
        bw = characteristic_curve(bw, toe, shoulder, slope, curve.pivot_x, curve.pivot_y)
        if stock.base_fog > 0.0:
            bw = bw * (1.0 - stock.base_fog) + stock.base_fog
        bw = linear_to_srgb(bw)
        result = bw.unsqueeze(-1).expand(-1, -1, -1, 3)
        return io.NodeOutput(blend(image, result, strength).clamp(0.0, 1.0))


class ProPostFilmStockColor(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="ProPostFilmStockColor",
            display_name="Film Stock (Color)",
            category="Pro Post/Film",
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input("film_stock", options=COLOR_STOCK_NAMES, default="Neg / Kodak Portra 400"),
                io.Float.Input("strength", default=1.0, min=0.0, max=1.0, step=0.05),
                io.Float.Input("override_toe", default=-1.0, min=-1.0, max=5.0, step=0.1),
                io.Float.Input("override_shoulder", default=-1.0, min=-1.0, max=5.0, step=0.1),
                io.Float.Input("override_gamma", default=-1.0, min=-1.0, max=3.0, step=0.05),
            ],
            outputs=[
                io.Image.Output("image"),
            ],
        )

    @classmethod
    def _apply_overrides(cls, curve: CurveParams, override_toe: float,
                         override_shoulder: float, override_gamma: float) -> CurveParams:
        toe = override_toe if override_toe > -0.5 else curve.toe_power
        shoulder = override_shoulder if override_shoulder > -0.5 else curve.shoulder_power
        slope = override_gamma if override_gamma > -0.5 else curve.slope
        return CurveParams(toe, shoulder, slope, curve.pivot_x, curve.pivot_y)

    @classmethod
    @torch.inference_mode()
    def execute(cls, image: torch.Tensor, film_stock: str, strength: float,
                override_toe: float, override_shoulder: float,
                override_gamma: float) -> io.NodeOutput:
        if strength <= 0.0:
            return io.NodeOutput(image)

        stock = COLOR_STOCKS[film_stock]
        linear = srgb_to_linear(image)

        if override_toe <= -0.5 and override_shoulder <= -0.5 and override_gamma <= -0.5:
            curve_params = _cached_curve_params(
                _COLOR_CURVE_CACHE,
                film_stock,
                (stock.r_curve, stock.g_curve, stock.b_curve),
                image.device,
                image.dtype,
            )
        else:
            curve_params = curve_params_from_channels(
                (
                    cls._apply_overrides(stock.r_curve, override_toe, override_shoulder, override_gamma),
                    cls._apply_overrides(stock.g_curve, override_toe, override_shoulder, override_gamma),
                    cls._apply_overrides(stock.b_curve, override_toe, override_shoulder, override_gamma),
                ),
                image.device,
                image.dtype,
            )

        curved = apply_per_channel_curves(linear, curve_params)
        if abs(stock.saturation - 1.0) > 0.001:
            curved = adjust_saturation(curved, stock.saturation)
        if any(abs(value) > 0.001 for value in stock.shadow_tint) or any(abs(value) > 0.001 for value in stock.highlight_tint):
            curved = split_tone(curved, stock.shadow_tint, stock.highlight_tint)

        result = linear_to_srgb(curved)
        return io.NodeOutput(blend(image, result, strength).clamp(0.0, 1.0))


__all__ = [
    "ProPostFilmStockBW",
    "ProPostFilmStockColor",
    "ProPostPrintStock",
]
