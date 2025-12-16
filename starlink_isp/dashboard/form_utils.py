def set_arabic_error_messages(form):
    for field in form.fields.values():
        field.error_messages = {
            "required": "هذا الحقل مطلوب",
            "invalid": "القيمة المدخلة غير صحيحة",
            "max_length": "النص طويل جدًا",
            "min_length": "النص قصير جدًا",
        }
