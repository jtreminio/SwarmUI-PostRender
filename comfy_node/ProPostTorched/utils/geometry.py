import torch
import torch.nn.functional as F

_GRID_CACHE: dict[tuple[int, int, str, str], dict[str, torch.Tensor | float]] = {}


def _expand_param(param, device: torch.device, dtype: torch.dtype, batch_size: int) -> torch.Tensor:
    value = torch.as_tensor(param, device=device, dtype=dtype)
    if value.ndim == 0:
        value = value.expand(batch_size)
    return value.reshape(batch_size, 1, 1)


def _radial_distortion_factor(base: dict[str, torch.Tensor | float], k1_t: torch.Tensor,
                              k2_t: torch.Tensor) -> torch.Tensor:
    return 1.0 + k1_t * base["r2"] + k2_t * base["r4"]


def get_centered_grid(height: int, width: int, device: torch.device, dtype: torch.dtype) -> dict[str, torch.Tensor | float]:
    key = (height, width, str(device), str(dtype))
    if key not in _GRID_CACHE:
        yy, xx = torch.meshgrid(
            torch.arange(height, device=device, dtype=dtype),
            torch.arange(width, device=device, dtype=dtype),
            indexing="ij",
        )
        cy = height / 2.0
        cx = width / 2.0
        dx = xx - cx
        dy = yy - cy
        nx = dx / cx
        ny = dy / cy
        r2 = nx * nx + ny * ny
        r = torch.sqrt(r2)
        max_r = (cx * cx + cy * cy) ** 0.5
        radius_norm = torch.sqrt(dx * dx + dy * dy) / max_r
        _GRID_CACHE[key] = {
            "x": xx.unsqueeze(0),
            "y": yy.unsqueeze(0),
            "dx": dx.unsqueeze(0),
            "dy": dy.unsqueeze(0),
            "nx": nx.unsqueeze(0),
            "ny": ny.unsqueeze(0),
            "r": r.unsqueeze(0),
            "r2": r2.unsqueeze(0),
            "r4": (r2 * r2).unsqueeze(0),
            "radius_norm": radius_norm.unsqueeze(0),
            "cx": cx,
            "cy": cy,
            "max_r": max_r,
        }
    return _GRID_CACHE[key]


def pixel_to_normalized_grid(
    src_x: torch.Tensor,
    src_y: torch.Tensor,
    width: int,
    height: int,
    align_corners: bool = False,
) -> torch.Tensor:
    if align_corners:
        x = (src_x / max(width - 1, 1)) * 2.0 - 1.0
        y = (src_y / max(height - 1, 1)) * 2.0 - 1.0
    else:
        x = ((src_x + 0.5) / width) * 2.0 - 1.0
        y = ((src_y + 0.5) / height) * 2.0 - 1.0
    return torch.stack([x, y], dim=-1)


def sample_nchw(
    image_4d: torch.Tensor,
    grid: torch.Tensor,
    mode: str = "bilinear",
    padding_mode: str = "zeros",
    align_corners: bool = False,
) -> torch.Tensor:
    return F.grid_sample(
        image_4d,
        grid,
        mode=mode,
        padding_mode=padding_mode,
        align_corners=align_corners,
    )


def sample_bhwc(
    image: torch.Tensor,
    grid: torch.Tensor,
    mode: str = "bilinear",
    padding_mode: str = "zeros",
    align_corners: bool = False,
) -> torch.Tensor:
    image_4d = image.permute(0, 3, 1, 2)
    sampled = sample_nchw(image_4d, grid, mode=mode, padding_mode=padding_mode, align_corners=align_corners)
    return sampled.permute(0, 2, 3, 1)


def build_distortion_grid(
    height: int,
    width: int,
    k1,
    k2,
    device: torch.device,
    dtype: torch.dtype,
    batch_size: int = 1,
    align_corners: bool = False,
) -> torch.Tensor:
    base = get_centered_grid(height, width, device, dtype)
    k1_t = _expand_param(k1, device, dtype, batch_size)
    k2_t = _expand_param(k2, device, dtype, batch_size)
    distort = _radial_distortion_factor(base, k1_t, k2_t)
    src_x = base["nx"] * distort * base["cx"] + base["cx"]
    src_y = base["ny"] * distort * base["cy"] + base["cy"]
    return pixel_to_normalized_grid(src_x, src_y, width, height, align_corners=align_corners)


def build_lateral_ca_grid(
    height: int,
    width: int,
    shift_pixels,
    device: torch.device,
    dtype: torch.dtype,
    batch_size: int = 1,
    align_corners: bool = False,
) -> torch.Tensor:
    base = get_centered_grid(height, width, device, dtype)
    shift_t = _expand_param(shift_pixels, device, dtype, batch_size)
    scale = 1.0 + (shift_t / base["max_r"]) * base["radius_norm"]
    src_x = base["dx"] * scale + base["cx"]
    src_y = base["dy"] * scale + base["cy"]
    return pixel_to_normalized_grid(src_x, src_y, width, height, align_corners=align_corners)


def build_lens_profile_channel_grid(
    height: int,
    width: int,
    k1,
    k2,
    ca_shift,
    device: torch.device,
    dtype: torch.dtype,
    batch_size: int = 1,
    align_corners: bool = False,
) -> torch.Tensor:
    base = get_centered_grid(height, width, device, dtype)
    k1_t = _expand_param(k1, device, dtype, batch_size)
    k2_t = _expand_param(k2, device, dtype, batch_size)
    ca_t = _expand_param(ca_shift, device, dtype, batch_size)
    distort = _radial_distortion_factor(base, k1_t, k2_t)
    ca_factor = 1.0 + (ca_t / base["max_r"]) * base["r"]
    total = distort * ca_factor
    src_x = base["nx"] * total * base["cx"] + base["cx"]
    src_y = base["ny"] * total * base["cy"] + base["cy"]
    return pixel_to_normalized_grid(src_x, src_y, width, height, align_corners=align_corners)


__all__ = [
    "build_distortion_grid",
    "build_lateral_ca_grid",
    "build_lens_profile_channel_grid",
    "get_centered_grid",
    "pixel_to_normalized_grid",
    "sample_bhwc",
    "sample_nchw",
]
