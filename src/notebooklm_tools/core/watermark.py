#!/usr/bin/env python3
"""
NotebookLM Watermark Remover

Removes the NotebookLM logo watermark from downloaded infographics.

The NotebookLM logo is transparent — just dark pixels (icon + text) overlaid
on whatever background is underneath, including shadows and gradients.

Approach:
  1. Scan the bottom-right corner for dark pixel clusters (the logo)
  2. Expand to include anti-aliased neighbor pixels
  3. For each logo pixel, sample colors from surrounding non-logo pixels
  4. Replace only those pixels, preserving underlying content

This preserves shadows and gradients that may be underneath the watermark,
unlike naive rectangle-fill approaches.

Requires: Pillow (PIL)
Optional: OpenCV (cv2) for template-based matching (more robust)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np

    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False


def _find_logo_dark_pixels(
    img: Image.Image,
    search_width: int = 200,
    search_height: int = 40,
    dark_threshold: int = 120,
) -> tuple[int, int, int, int] | None:
    """Find the logo bounding box by scanning for dark pixel clusters.

    Scans the bottom-right corner of the image for clusters of dark pixels
    that form the NotebookLM logo text and icon.

    Args:
        img: PIL Image in RGB mode.
        search_width: Width of the search region from the right edge.
        search_height: Height of the search region from the bottom edge.
        dark_threshold: Maximum brightness (0-255) to consider a pixel "dark".

    Returns:
        Bounding box (left, top, right, bottom) or None if no logo found.
    """
    width, height = img.size

    left_bound = width - search_width
    top_bound = height - search_height

    dark_pixels = []
    for x in range(left_bound, width):
        for y in range(top_bound, height):
            pixel = img.getpixel((x, y))
            brightness = sum(pixel[:3]) / 3
            if brightness < dark_threshold:
                dark_pixels.append((x, y))

    if not dark_pixels:
        return None

    # Bounding box with small padding
    min_x = min(p[0] for p in dark_pixels) - 2
    max_x = max(p[0] for p in dark_pixels) + 2
    min_y = min(p[1] for p in dark_pixels) - 2
    max_y = max(p[1] for p in dark_pixels) + 2

    return (min_x, min_y, max_x, max_y)


def _find_logo_template(
    img: Image.Image,
    template_path: Path,
    threshold: float = 0.6,
) -> tuple[int, int, int, int] | None:
    """Find the logo using OpenCV template matching.

    Args:
        img: PIL Image in RGB mode.
        template_path: Path to a PNG template of the logo.
        threshold: Minimum match confidence (0.0-1.0).

    Returns:
        Bounding box (left, top, right, bottom) or None if no match.
    """
    if not HAS_OPENCV or not template_path.exists():
        return None

    img_array = np.array(img)
    template = np.array(Image.open(template_path))

    img_gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    tmpl_gray = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)

    h, w = tmpl_gray.shape
    result = cv2.matchTemplate(img_gray, tmpl_gray, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    if max_val >= threshold:
        x, y = max_loc
        logger.debug("Template match at (%d, %d) confidence %.1f%%", x, y, max_val * 100)
        return (x, y, x + w, y + h)

    return None


def _replace_logo_pixels(img: Image.Image, logo_box: tuple[int, int, int, int]) -> int:
    """Replace logo pixels with colors sampled from surrounding non-logo pixels.

    Two-pass approach:
      Pass 1: Identify core dark pixels (brightness < 150)
      Pass 2: Expand to anti-aliased neighbors (brightness < 220, within 2px)
    Then replace each logo pixel with the average of nearby non-logo pixels.

    Args:
        img: PIL Image in RGB mode (modified in-place).
        logo_box: Bounding box (left, top, right, bottom).

    Returns:
        Number of pixels replaced.
    """
    left, top, right, bottom = logo_box
    width, height = img.size

    # Pass 1: core logo pixels
    core_pixels: set[tuple[int, int]] = set()
    for x in range(left, right + 1):
        for y in range(top, bottom + 1):
            if 0 <= x < width and 0 <= y < height:
                pixel = img.getpixel((x, y))
                if sum(pixel[:3]) / 3 < 150:
                    core_pixels.add((x, y))

    # Pass 2: anti-aliased neighbors
    logo_pixels = set(core_pixels)
    for x, y in core_pixels:
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in logo_pixels:
                    pixel = img.getpixel((nx, ny))
                    if sum(pixel[:3]) / 3 < 220:
                        logo_pixels.add((nx, ny))

    logger.debug(
        "Found %d core + %d anti-aliased = %d total logo pixels",
        len(core_pixels),
        len(logo_pixels) - len(core_pixels),
        len(logo_pixels),
    )

    # Replace each logo pixel with average of surrounding non-logo pixels
    for x, y in logo_pixels:
        samples: list[tuple[int, ...]] = []
        for radius in range(1, 15):
            for dx in range(-radius, radius + 1):
                for dy in range(-radius, radius + 1):
                    if abs(dx) == radius or abs(dy) == radius:
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in logo_pixels:
                            samples.append(img.getpixel((nx, ny))[:3])
            if len(samples) >= 8:
                break

        if samples:
            new_color = tuple(sum(c[i] for c in samples) // len(samples) for i in range(3))
        else:
            new_color = (227, 230, 231)

        img.putpixel((x, y), new_color)

    return len(logo_pixels)


def remove_watermark(
    input_path: str | Path,
    output_path: str | Path | None = None,
    *,
    template_path: str | Path | None = None,
    verify: bool = True,
) -> Path:
    """Remove the NotebookLM watermark from an infographic image.

    Args:
        input_path: Path to the input PNG image.
        output_path: Path for the output image. If None, appends '_clean'
            to the input filename.
        template_path: Optional path to a logo template PNG for OpenCV
            template matching (more robust detection).
        verify: If True, verify no dark pixels remain after removal.

    Returns:
        Path to the cleaned output image.

    Raises:
        FileNotFoundError: If input_path does not exist.
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Image not found: {input_path}")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
    else:
        output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load and normalize to RGB
    img = Image.open(input_path)
    if img.mode == "RGBA":
        rgb = Image.new("RGB", img.size, (255, 255, 255))
        rgb.paste(img, mask=img.split()[3])
        img = rgb
    elif img.mode != "RGB":
        img = img.convert("RGB")

    width, height = img.size

    # Try template matching first (if available)
    logo_box = None
    if template_path is not None:
        logo_box = _find_logo_template(img, Path(template_path))

    # Fall back to dark pixel detection
    if logo_box is None:
        logo_box = _find_logo_dark_pixels(img)

    if logo_box is None:
        logger.info("No watermark detected in %s", input_path.name)
        img.save(output_path)
        return output_path

    logger.info("Logo detected at %s", logo_box)

    # Replace logo pixels
    replaced = _replace_logo_pixels(img, logo_box)
    logger.info("Replaced %d pixels", replaced)

    # Optional verification pass
    if verify:
        check = (width - 200, height - 40, width, height)
        dark_remaining = 0
        for x in range(check[0], check[2]):
            for y in range(check[1], check[3]):
                if 0 <= x < width and 0 <= y < height:
                    pixel = img.getpixel((x, y))
                    if sum(pixel[:3]) / 3 < 180:
                        dark_remaining += 1

        if dark_remaining > 0:
            logger.debug("Second pass: %d dark pixels remain, cleaning up", dark_remaining)
            for x in range(check[0], check[2]):
                for y in range(check[1], check[3]):
                    if 0 <= x < width and 0 <= y < height:
                        pixel = img.getpixel((x, y))
                        if sum(pixel[:3]) / 3 < 140:
                            # Sample background
                            samples = []
                            for ddx in range(-10, 11):
                                for ddy in range(-10, 11):
                                    nnx, nny = x + ddx, y + ddy
                                    if 0 <= nnx < width and 0 <= nny < height:
                                        p = img.getpixel((nnx, nny))
                                        if sum(p[:3]) / 3 > 180:
                                            samples.append(p[:3])
                            if samples:
                                bg = tuple(sum(c[i] for c in samples) // len(samples) for i in range(3))
                            else:
                                bg = (215, 219, 222)
                            img.putpixel((x, y), bg)

    img.save(output_path)
    return output_path


def remove_watermark_batch(
    folder_path: str | Path,
    output_folder: str | Path | None = None,
    *,
    template_path: str | Path | None = None,
) -> list[Path]:
    """Remove watermarks from all PNG images in a folder.

    Args:
        folder_path: Directory containing PNG images.
        output_folder: Output directory. Defaults to '{folder}_clean'.
        template_path: Optional logo template for OpenCV matching.

    Returns:
        List of output paths for successfully processed images.
    """
    folder_path = Path(folder_path)
    if output_folder is None:
        output_folder = folder_path.parent / f"{folder_path.name}_clean"
    else:
        output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    images = sorted(folder_path.glob("*.png")) + sorted(folder_path.glob("*.PNG"))
    results: list[Path] = []

    for img_path in images:
        try:
            out = remove_watermark(
                img_path,
                output_folder / img_path.name,
                template_path=template_path,
            )
            results.append(out)
            logger.info("Cleaned: %s", img_path.name)
        except Exception as e:
            logger.error("Failed to process %s: %s", img_path.name, e)

    return results
