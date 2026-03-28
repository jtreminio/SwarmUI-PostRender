import math

import torch
import torch.nn.functional as F

# Kernel cache: (kernel_size, device_str, dtype_str) -> [k] tensor
_kernel_cache: dict = {}
# Sigma kernel cache: (radius, sigma_key, device_str, dtype_str) -> [k] tensor
_sigma_kernel_cache: dict = {}


def bhwc_to_nchw(image: torch.Tensor) -> torch.Tensor:
    return image.permute(0, 3, 1, 2)


def nchw_to_bhwc(image_4d: torch.Tensor) -> torch.Tensor:
    return image_4d.permute(0, 2, 3, 1)


def _gaussian_kernel_1d(kernel_size: int, device: torch.device,
                        dtype: torch.dtype) -> torch.Tensor:
    """[k] Gaussian weights matching cv2.GaussianBlur(img, (k, k), 0) sigma."""
    key = (kernel_size, str(device), str(dtype))
    if key not in _kernel_cache:
        sigma = 0.3 * ((kernel_size - 1) * 0.5 - 1) + 0.8  # OpenCV sigma for sigmaX=0
        x = torch.arange(kernel_size, dtype=torch.float32, device=device) - kernel_size // 2
        g = torch.exp(-0.5 * (x / sigma) ** 2)
        g /= g.sum()
        _kernel_cache[key] = g.to(dtype=dtype)
    return _kernel_cache[key]


def _gaussian_kernel_1d_from_sigma(sigma: float, device: torch.device,
                                   dtype: torch.dtype) -> torch.Tensor:
    sigma = max(float(sigma), 1e-4)
    radius = max(1, int(math.ceil(sigma * 3.0)))
    sigma_key = round(sigma, 4)
    key = (radius, sigma_key, str(device), str(dtype))
    if key not in _sigma_kernel_cache:
        x = torch.arange(-radius, radius + 1, dtype=torch.float32, device=device)
        g = torch.exp(-0.5 * (x / sigma) ** 2)
        g /= g.sum()
        _sigma_kernel_cache[key] = g.to(dtype=dtype)
    return _sigma_kernel_cache[key]


def _safe_padding_mode(image_4d: torch.Tensor, pad: int, padding_mode: str) -> str:
    if padding_mode != "reflect":
        return padding_mode
    if image_4d.shape[2] <= pad or image_4d.shape[3] <= pad:
        return "replicate"
    return "reflect"


def _apply_separable_kernel(image_4d: torch.Tensor, kernel_1d: torch.Tensor,
                            padding_mode: str = "zeros") -> torch.Tensor:
    kernel_size = int(kernel_1d.shape[0])
    if kernel_size <= 1:
        return image_4d
    pad = kernel_size // 2
    channels = image_4d.shape[1]
    kernel_x = kernel_1d.view(1, 1, 1, kernel_size).expand(channels, 1, 1, kernel_size)
    kernel_y = kernel_1d.view(1, 1, kernel_size, 1).expand(channels, 1, kernel_size, 1)
    if padding_mode == "zeros":
        blurred = F.conv2d(image_4d, kernel_x, padding=(0, pad), groups=channels)
        return F.conv2d(blurred, kernel_y, padding=(pad, 0), groups=channels)
    safe_mode = _safe_padding_mode(image_4d, pad, padding_mode)
    padded = F.pad(image_4d, (pad, pad, 0, 0), mode=safe_mode)
    blurred = F.conv2d(padded, kernel_x, groups=channels)
    padded = F.pad(blurred, (0, 0, pad, pad), mode=safe_mode)
    return F.conv2d(padded, kernel_y, groups=channels)


def gaussian_blur(image_4d: torch.Tensor, kernel_size: int) -> torch.Tensor:
    """
    image_4d: [N, C, H, W] float32.
    Depthwise separable Gaussian blur - one kernel applied independently per channel.
    """
    if kernel_size <= 1:
        return image_4d
    kernel_1d = _gaussian_kernel_1d(kernel_size, image_4d.device, image_4d.dtype)
    return _apply_separable_kernel(image_4d, kernel_1d, padding_mode="zeros")


def gaussian_blur_sigma(image_4d: torch.Tensor, sigma: float,
                        padding_mode: str = "reflect") -> torch.Tensor:
    if sigma <= 0.01:
        return image_4d
    kernel_1d = _gaussian_kernel_1d_from_sigma(sigma, image_4d.device, image_4d.dtype)
    return _apply_separable_kernel(image_4d, kernel_1d, padding_mode=padding_mode)


def _downsample_factor_for_sigma(height: int, width: int, sigma: float,
                                 min_dim: int = 64) -> int:
    sigma = float(sigma)
    factor = 1
    while sigma / factor > 12.0 and min(height, width) // (factor * 2) >= min_dim:
        factor *= 2
    return factor


def gaussian_blur_auto(image_4d: torch.Tensor, sigma: float,
                       padding_mode: str = "reflect") -> torch.Tensor:
    if sigma <= 0.01:
        return image_4d
    _, _, height, width = image_4d.shape
    factor = _downsample_factor_for_sigma(height, width, sigma)
    if factor == 1:
        return gaussian_blur_sigma(image_4d, sigma, padding_mode=padding_mode)
    work_size = (max(1, height // factor), max(1, width // factor))
    down = F.interpolate(image_4d, size=work_size, mode="area")
    blurred = gaussian_blur_sigma(down, sigma / factor, padding_mode=padding_mode)
    return F.interpolate(blurred, size=(height, width), mode="bilinear", align_corners=False)


def gaussian_weighted_average(values_4d: torch.Tensor, weights_4d: torch.Tensor,
                              sigma: float, padding_mode: str = "reflect") -> tuple[torch.Tensor, torch.Tensor]:
    if sigma <= 0.01:
        return values_4d, weights_4d.clamp(min=1e-7)

    _, _, height, width = values_4d.shape
    factor = _downsample_factor_for_sigma(height, width, sigma)
    work_values = values_4d
    work_weights = weights_4d.clamp(min=0.0)
    work_sigma = float(sigma)

    if factor > 1:
        work_size = (max(1, height // factor), max(1, width // factor))
        work_values = F.interpolate(values_4d, size=work_size, mode="area")
        work_weights = F.interpolate(work_weights, size=work_size, mode="area")
        work_sigma /= factor

    blurred_values = gaussian_blur_sigma(work_values * work_weights, work_sigma, padding_mode=padding_mode)
    blurred_weights = gaussian_blur_sigma(work_weights, work_sigma, padding_mode=padding_mode).clamp(min=1e-7)
    averaged = blurred_values / blurred_weights

    if factor > 1:
        averaged = F.interpolate(averaged, size=(height, width), mode="bilinear", align_corners=False)
        blurred_weights = F.interpolate(blurred_weights, size=(height, width), mode="bilinear", align_corners=False)

    return averaged, blurred_weights.clamp(min=1e-7)


def generate_blurred_images(image_4d: torch.Tensor, blur_strength: float,
                            steps: int, focus_spread: float = 1.0) -> list:
    """image_4d: [B, C, H, W]. Returns list of `steps` blurred tensors."""
    blurred = []
    blurred_by_kernel = {}
    for step in range(1, steps + 1):
        blur_factor = (step / steps) ** focus_spread * blur_strength
        k = max(1, int(blur_factor))
        k = k if k % 2 == 1 else k + 1
        if k not in blurred_by_kernel:
            blurred_by_kernel[k] = gaussian_blur(image_4d, k)
        blurred.append(blurred_by_kernel[k])
    return blurred


def apply_blurred_images(image_4d: torch.Tensor, blurred_images: list,
                         mask_2d: torch.Tensor) -> torch.Tensor:
    """
    image_4d:       [B, C, H, W]
    blurred_images: list of [B, C, H, W]
    mask_2d:        [H, W], [B, H, W], or [B, 1, H, W] in [0, 1]
    Returns:        [B, C, H, W]
    """
    steps = len(blurred_images)
    step_size = 1.0 / steps

    if mask_2d.dim() == 2:
        mask = mask_2d.unsqueeze(0).unsqueeze(0)
    elif mask_2d.dim() == 3:
        mask = mask_2d.unsqueeze(1)
    else:
        mask = mask_2d

    final = torch.zeros_like(image_4d)

    for i, blurred in enumerate(blurred_images):
        current = ((mask - i * step_size) * steps).clamp(0.0, 1.0)
        nxt = ((mask - (i + 1) * step_size) * steps).clamp(0.0, 1.0)
        final += (current - nxt) * blurred

    final += (1.0 - (mask * steps).clamp(0.0, 1.0)) * image_4d
    return final


__all__ = [
    "apply_blurred_images",
    "bhwc_to_nchw",
    "gaussian_blur",
    "gaussian_blur_auto",
    "gaussian_blur_sigma",
    "gaussian_weighted_average",
    "generate_blurred_images",
    "nchw_to_bhwc",
]
