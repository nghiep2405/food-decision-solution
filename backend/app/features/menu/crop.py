"""Validate an optional rectangle in original, EXIF-oriented image pixels."""
import json
from io import BytesIO

from PIL import Image, ImageOps


def prepare_ocr_image(image_bytes: bytes, crop_json: str | None):
    if crop_json is None:
        return image_bytes, None
    crop = json.loads(crop_json)
    keys = ('x', 'y', 'width', 'height')
    if not isinstance(crop, dict) or set(crop) != set(keys):
        raise ValueError('Crop cần x, y, width, height.')
    if any(type(crop[key]) is not int for key in keys):
        raise ValueError('Tọa độ crop phải là số nguyên.')
    x, y, width, height = (crop[key] for key in keys)
    with Image.open(BytesIO(image_bytes)) as original:
        image = ImageOps.exif_transpose(original)
        if x < 0 or y < 0 or width <= 0 or height <= 0 or x + width > image.width or y + height > image.height:
            raise ValueError('Vùng crop nằm ngoài ảnh hoặc có kích thước không hợp lệ.')
        output = BytesIO()
        image.crop((x, y, x + width, y + height)).convert('RGB').save(output, format='PNG')
        return output.getvalue(), {**crop, 'imageWidth': image.width, 'imageHeight': image.height}
