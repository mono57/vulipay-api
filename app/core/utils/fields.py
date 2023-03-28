from django.db import models


class AppCharField(models.CharField):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.null:
            self.default = None