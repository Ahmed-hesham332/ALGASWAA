from django.core.exceptions import ValidationError
from PIL import Image

def validate_image(file):
    try:
        Image.open(file).verify()
    except Exception:
        raise ValidationError("الملف الذي تم رفعه ليس صورة صالحة.")

def validate_image_size(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise ValidationError("حجم الصورة أكبر من 5MB.")