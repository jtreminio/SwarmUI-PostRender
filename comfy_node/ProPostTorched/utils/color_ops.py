import torch

EPSILON = 1e-7
_LUMA_WEIGHT_CACHE: dict[tuple[str, str], torch.Tensor] = {}


def _broadcast_rgb_vector(value, reference: torch.Tensor) -> torch.Tensor:
    vec = torch.as_tensor(value, device=reference.device, dtype=reference.dtype)
    shape = [1] * reference.dim()
    shape[-1] = vec.numel()
    return vec.reshape(shape)


def _coerce_like(value, reference: torch.Tensor) -> torch.Tensor:
    return torch.as_tensor(value, device=reference.device, dtype=reference.dtype)


def rec709_weights(device: torch.device, dtype: torch.dtype) -> torch.Tensor:
    key = (str(device), str(dtype))
    if key not in _LUMA_WEIGHT_CACHE:
        _LUMA_WEIGHT_CACHE[key] = torch.tensor(
            [0.2126, 0.7152, 0.0722],
            device=device,
            dtype=dtype,
        )
    return _LUMA_WEIGHT_CACHE[key]


def srgb_to_linear(image: torch.Tensor) -> torch.Tensor:
    image = image.clamp(0.0, 1.0)
    return torch.where(
        image <= 0.04045,
        image / 12.92,
        ((image + 0.055) / 1.055).pow(2.4),
    )


def linear_to_srgb(image: torch.Tensor) -> torch.Tensor:
    image = image.clamp(0.0, 1.0)
    return torch.where(
        image <= 0.0031308,
        image * 12.92,
        1.055 * image.pow(1.0 / 2.4) - 0.055,
    )


def blend(original: torch.Tensor, processed: torch.Tensor, strength: float | torch.Tensor) -> torch.Tensor:
    strength_t = _coerce_like(strength, original)
    return original + (processed - original) * strength_t


def luminance_rec709(image: torch.Tensor) -> torch.Tensor:
    weights = rec709_weights(image.device, image.dtype)
    shape = [1] * image.dim()
    shape[-1] = 3
    return (image * weights.reshape(shape)).sum(dim=-1)


def curve_params_from_channels(curves, device: torch.device, dtype: torch.dtype) -> tuple[torch.Tensor, ...]:
    toe = torch.tensor([curve.toe_power for curve in curves], device=device, dtype=dtype).view(1, 1, 1, -1)
    shoulder = torch.tensor([curve.shoulder_power for curve in curves], device=device, dtype=dtype).view(1, 1, 1, -1)
    slope = torch.tensor([curve.slope for curve in curves], device=device, dtype=dtype).view(1, 1, 1, -1)
    pivot_x = torch.tensor([curve.pivot_x for curve in curves], device=device, dtype=dtype).view(1, 1, 1, -1)
    pivot_y = torch.tensor([curve.pivot_y for curve in curves], device=device, dtype=dtype).view(1, 1, 1, -1)
    return toe, shoulder, slope, pivot_x, pivot_y


def characteristic_curve(
    x: torch.Tensor,
    toe_power: torch.Tensor | float,
    shoulder_power: torch.Tensor | float,
    slope: torch.Tensor | float,
    pivot_x: torch.Tensor | float = 0.18,
    pivot_y: torch.Tensor | float = 0.18,
) -> torch.Tensor:
    x = x.clamp(0.0, 1.0)
    toe_power_t = _coerce_like(toe_power, x)
    shoulder_power_t = _coerce_like(shoulder_power, x)
    slope_t = _coerce_like(slope, x)
    pivot_x_t = _coerce_like(pivot_x, x)
    pivot_y_t = _coerce_like(pivot_y, x)

    toe_t = x / (pivot_x_t + EPSILON)
    toe_curve = pivot_y_t * toe_t.clamp(min=0.0).pow(toe_power_t) * slope_t

    shoulder_t = (x - pivot_x_t) / (1.0 - pivot_x_t + EPSILON)
    shoulder_curve = 1.0 - (1.0 - shoulder_t).clamp(0.0, 1.0).pow(shoulder_power_t)
    shoulder_curve = pivot_y_t * slope_t + (1.0 - pivot_y_t * slope_t) * shoulder_curve

    return torch.where(x <= pivot_x_t, toe_curve, shoulder_curve).clamp(0.0, 1.0)


def apply_per_channel_curves(image: torch.Tensor, curve_params: tuple[torch.Tensor, ...]) -> torch.Tensor:
    toe_power, shoulder_power, slope, pivot_x, pivot_y = curve_params
    return characteristic_curve(image, toe_power, shoulder_power, slope, pivot_x, pivot_y)


def adjust_saturation(image: torch.Tensor, factor: float | torch.Tensor) -> torch.Tensor:
    factor_t = _coerce_like(factor, image)
    lum = luminance_rec709(image).unsqueeze(-1)
    return (lum + factor_t * (image - lum)).clamp(0.0, 1.0)


def split_tone(
    image: torch.Tensor,
    shadow_tint,
    highlight_tint,
    balance: float | torch.Tensor = 0.5,
) -> torch.Tensor:
    lum = luminance_rec709(image)
    balance_t = _coerce_like(balance, lum).clamp(min=1e-4, max=1.0 - 1e-4)
    shadow_weight = (1.0 - lum / (balance_t + EPSILON)).clamp(0.0, 1.0)
    highlight_weight = ((lum - balance_t) / (1.0 - balance_t + EPSILON)).clamp(0.0, 1.0)
    shadow_tint_t = _broadcast_rgb_vector(shadow_tint, image)
    highlight_tint_t = _broadcast_rgb_vector(highlight_tint, image)
    return (
        image
        + shadow_weight.unsqueeze(-1) * shadow_tint_t
        + highlight_weight.unsqueeze(-1) * highlight_tint_t
    ).clamp(0.0, 1.0)


def angular_distance(hue: torch.Tensor, center: float | torch.Tensor) -> torch.Tensor:
    center_t = _coerce_like(center, hue)
    diff = (hue - center_t).abs()
    return torch.minimum(diff, 360.0 - diff)


def circular_hue_difference(target_hue: torch.Tensor, source_hue: torch.Tensor) -> torch.Tensor:
    return torch.remainder(target_hue - source_hue + 180.0, 360.0) - 180.0


def rgb_to_hsl(image: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    r = image[..., 0]
    g = image[..., 1]
    b = image[..., 2]

    cmax = torch.maximum(torch.maximum(r, g), b)
    cmin = torch.minimum(torch.minimum(r, g), b)
    delta = cmax - cmin

    l = (cmax + cmin) * 0.5
    s = torch.zeros_like(l)
    chroma_mask = delta > EPSILON

    low_mask = chroma_mask & (l <= 0.5)
    high_mask = chroma_mask & (l > 0.5)
    s = torch.where(low_mask, delta / (cmax + cmin + EPSILON), s)
    s = torch.where(high_mask, delta / (2.0 - cmax - cmin + EPSILON), s)

    h = torch.zeros_like(l)
    max_is_r = chroma_mask & (cmax == r)
    max_is_g = chroma_mask & (cmax == g) & ~max_is_r
    max_is_b = chroma_mask & ~(max_is_r | max_is_g)

    h = torch.where(max_is_r, 60.0 * torch.remainder((g - b) / (delta + EPSILON), 6.0), h)
    h = torch.where(max_is_g, 60.0 * (((b - r) / (delta + EPSILON)) + 2.0), h)
    h = torch.where(max_is_b, 60.0 * (((r - g) / (delta + EPSILON)) + 4.0), h)
    return torch.remainder(h, 360.0), s.clamp(0.0, 1.0), l.clamp(0.0, 1.0)


def hsl_to_rgb(h: torch.Tensor, s: torch.Tensor, l: torch.Tensor) -> torch.Tensor:
    c = (1.0 - (2.0 * l - 1.0).abs()) * s
    h_prime = torch.remainder(h / 60.0, 6.0)
    x = c * (1.0 - torch.abs(torch.remainder(h_prime, 2.0) - 1.0))
    m = l - c * 0.5

    r = torch.zeros_like(h)
    g = torch.zeros_like(h)
    b = torch.zeros_like(h)

    mask = (h_prime >= 0.0) & (h_prime < 1.0)
    r = torch.where(mask, c, r)
    g = torch.where(mask, x, g)

    mask = (h_prime >= 1.0) & (h_prime < 2.0)
    r = torch.where(mask, x, r)
    g = torch.where(mask, c, g)

    mask = (h_prime >= 2.0) & (h_prime < 3.0)
    g = torch.where(mask, c, g)
    b = torch.where(mask, x, b)

    mask = (h_prime >= 3.0) & (h_prime < 4.0)
    g = torch.where(mask, x, g)
    b = torch.where(mask, c, b)

    mask = (h_prime >= 4.0) & (h_prime < 5.0)
    r = torch.where(mask, x, r)
    b = torch.where(mask, c, b)

    mask = (h_prime >= 5.0) & (h_prime < 6.0)
    r = torch.where(mask, c, r)
    b = torch.where(mask, x, b)

    return torch.stack([r + m, g + m, b + m], dim=-1).clamp(0.0, 1.0)


def hue_range_mask(
    hue: torch.Tensor,
    center: float | torch.Tensor,
    width: float | torch.Tensor = 45.0,
    softness: float | torch.Tensor = 0.5,
) -> torch.Tensor:
    width_t = _coerce_like(width, hue)
    softness_t = _coerce_like(softness, hue)
    effective_width = width_t * (0.5 + softness_t * 0.5)
    diff = angular_distance(hue, center)
    weight = ((1.0 + torch.cos(torch.pi * diff / effective_width.clamp(min=1.0))) * 0.5).clamp(0.0, 1.0)
    return torch.where(diff <= effective_width, weight, torch.zeros_like(weight))


def sat_range_weight(
    sat: torch.Tensor,
    sat_min: float | torch.Tensor,
    sat_max: float | torch.Tensor,
    softness: float | torch.Tensor = 0.1,
) -> torch.Tensor:
    soft_t = _coerce_like(softness, sat).clamp(min=0.01)
    sat_min_t = _coerce_like(sat_min, sat)
    sat_max_t = _coerce_like(sat_max, sat)
    low_weight = ((sat - sat_min_t + soft_t) / (2.0 * soft_t)).clamp(0.0, 1.0)
    high_weight = ((sat_max_t + soft_t - sat) / (2.0 * soft_t)).clamp(0.0, 1.0)
    return low_weight * high_weight


def soft_range_mask(
    value: torch.Tensor,
    min_value: float | torch.Tensor,
    max_value: float | torch.Tensor,
    feather: float | torch.Tensor,
) -> torch.Tensor:
    min_t = _coerce_like(min_value, value)
    max_t = _coerce_like(max_value, value)
    feather_t = _coerce_like(feather, value).clamp(min=EPSILON)
    low = ((value - min_t) / feather_t).clamp(0.0, 1.0)
    high = ((max_t - value) / feather_t).clamp(0.0, 1.0)
    return low * high


__all__ = [
    "EPSILON",
    "adjust_saturation",
    "angular_distance",
    "apply_per_channel_curves",
    "blend",
    "characteristic_curve",
    "circular_hue_difference",
    "curve_params_from_channels",
    "hsl_to_rgb",
    "hue_range_mask",
    "linear_to_srgb",
    "luminance_rec709",
    "rec709_weights",
    "rgb_to_hsl",
    "sat_range_weight",
    "soft_range_mask",
    "split_tone",
    "srgb_to_linear",
]
