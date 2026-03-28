import numpy as np
import torch
import folder_paths

from . import loading as loading_utils

_DEFAULT_DOMAIN = np.array([[0.0, 0.0, 0.0], [1.0, 1.0, 1.0]], dtype=np.float32)
_LUT_FILE_CACHE: dict[str, tuple[loading_utils.CubeLUT, bool]] = {}
_LUT_TABLE_CACHE: dict[tuple[str, str, str], torch.Tensor] = {}
_LUT_DOMAIN_CACHE: dict[tuple[str, str, str], tuple[torch.Tensor, torch.Tensor]] = {}


def resolve_lut_path(lut_name: str) -> str:
    lut_path = folder_paths.get_full_path("luts", lut_name)
    if not lut_path:
        raise FileNotFoundError(f"LUT not found: {lut_name}")
    return lut_path


def load_lut(lut_name: str) -> tuple[str, loading_utils.CubeLUT, bool]:
    lut_path = resolve_lut_path(lut_name)
    if lut_path not in _LUT_FILE_CACHE:
        lut = loading_utils.read_lut(lut_path, clip=True)
        _LUT_FILE_CACHE[lut_path] = (lut, bool(np.array_equal(lut.domain, _DEFAULT_DOMAIN)))
    lut, has_default_domain = _LUT_FILE_CACHE[lut_path]
    return lut_path, lut, has_default_domain


def lut_table_tensor(lut_path: str, table: np.ndarray, device: torch.device,
                     dtype: torch.dtype) -> torch.Tensor:
    key = (lut_path, str(device), str(dtype))
    if key not in _LUT_TABLE_CACHE:
        _LUT_TABLE_CACHE[key] = torch.from_numpy(table).to(device=device, dtype=dtype)
    return _LUT_TABLE_CACHE[key]


def lut_domain_tensors(lut_path: str, lut, device: torch.device,
                       dtype: torch.dtype) -> tuple[torch.Tensor, torch.Tensor]:
    key = (lut_path, str(device), str(dtype))
    if key not in _LUT_DOMAIN_CACHE:
        dom_min = torch.from_numpy(lut.domain[0].copy()).to(device=device, dtype=dtype)
        dom_scale = torch.from_numpy((lut.domain[1] - lut.domain[0]).copy()).to(device=device, dtype=dtype)
        _LUT_DOMAIN_CACHE[key] = (dom_min, dom_scale)
    return _LUT_DOMAIN_CACHE[key]


def apply_3d_lut(image: torch.Tensor, lut_t: torch.Tensor) -> torch.Tensor:
    """
    Torch trilinear interpolation for 3D LUTs.
    image: [..., 3] float in [0, 1]
    lut_t: [N, N, N, 3] torch tensor
    """
    size = lut_t.shape[0]

    coords = (image * (size - 1)).clamp(0, size - 1)
    low = coords.floor().long().clamp(0, size - 2)
    high = (low + 1).clamp(0, size - 1)
    weights = (coords - low.float()).clamp(0.0, 1.0)

    r0, g0, b0 = low[..., 0], low[..., 1], low[..., 2]
    r1, g1, b1 = high[..., 0], high[..., 1], high[..., 2]
    wr, wg, wb = weights[..., 0:1], weights[..., 1:2], weights[..., 2:3]

    c000 = lut_t[r0, g0, b0]
    c100 = lut_t[r1, g0, b0]
    c010 = lut_t[r0, g1, b0]
    c110 = lut_t[r1, g1, b0]
    c001 = lut_t[r0, g0, b1]
    c101 = lut_t[r1, g0, b1]
    c011 = lut_t[r0, g1, b1]
    c111 = lut_t[r1, g1, b1]

    c00 = c000 + wr * (c100 - c000)
    c01 = c001 + wr * (c101 - c001)
    c10 = c010 + wr * (c110 - c010)
    c11 = c011 + wr * (c111 - c011)
    c0 = c00 + wg * (c10 - c00)
    c1 = c01 + wg * (c11 - c01)
    return (c0 + wb * (c1 - c0)).clamp(0.0, 1.0)


def apply_1d_lut(image: torch.Tensor, lut_t: torch.Tensor) -> torch.Tensor:
    """Per-channel linear interpolation for LUT3x1D."""
    size = lut_t.shape[0]

    coords = (image * (size - 1)).clamp(0, size - 1)
    low = coords.floor().long().clamp(0, size - 2)
    high = (low + 1).clamp(0, size - 1)
    weights = (coords - low.float()).clamp(0.0, 1.0)

    result = torch.stack([
        lut_t[low[..., channel], channel]
        + weights[..., channel] * (lut_t[high[..., channel], channel] - lut_t[low[..., channel], channel])
        for channel in range(3)
    ], dim=-1)
    return result.clamp(0.0, 1.0)


def apply_lut(image: torch.Tensor, lut_name: str, log: bool) -> torch.Tensor:
    lut_path, lut, has_default_domain = load_lut(lut_name)
    lut_t = lut_table_tensor(lut_path, lut.table, image.device, image.dtype)

    frame = image
    dom_min = None
    dom_scale = None
    if not has_default_domain:
        dom_min, dom_scale = lut_domain_tensors(lut_path, lut, image.device, image.dtype)
        frame = frame * dom_scale + dom_min

    if log:
        frame = frame.clamp(min=1e-7).pow(1.0 / 2.2)

    if len(lut.table.shape) == 2:
        lut_out = apply_1d_lut(frame, lut_t)
    else:
        lut_out = apply_3d_lut(frame, lut_t)

    if log:
        lut_out = lut_out.clamp(min=1e-7).pow(2.2)
    if not has_default_domain:
        lut_out = ((lut_out - dom_min) / dom_scale).clamp(0.0, 1.0)

    return lut_out


__all__ = [
    "apply_1d_lut",
    "apply_3d_lut",
    "apply_lut",
    "load_lut",
    "lut_domain_tensors",
    "lut_table_tensor",
    "resolve_lut_path",
]
