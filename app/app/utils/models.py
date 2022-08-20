import string
from typing import Union

from django.db import models

from .timestamp import TimestampModel

class CommonCode(TimestampModel):
    class Meta:
        app_label = 'banking'
    name = models.CharField(max_length=255, blank=True, null=True)
    code = models.CharField(max_length=255, unique=True)
    enabled = models.BooleanField(default=True)
    parent = models.ForeignKey(
        "CommonCode",
        null=True,
        related_name='childrens',
        on_delete=models.SET_NULL)

    def __str__(self):
        return self.name

    @classmethod
    def get_or_create(cls, parent_code: string, code: string, name: Union[str, None]):
        if not code:
            raise ValueError("Code should not be null")

        if not parent_code:
            raise ValueError("Parent Code should not be null")

        parent = cls.objects.get_or_create(code=parent_code)

        return cls.objects.get_or_create(
            parent=parent,
            code=code,
            name=name
        )



