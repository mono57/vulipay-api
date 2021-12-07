from django.db import models
from django.db.models import Q
from django.conf import settings

import string, random

def generate_code(
        Model: models.Model,
        lookup_field="key",
        unique=True,
        sequence=string.digits,
        length=settings.CONFIRMATION_CODE_LENGTH
    ) -> str:

    code_exists, key = True, ''

    while code_exists and unique:
        key = random.choices(sequence, k=length)
        kwargs =  { lookup_field: key }
        code_exists = Model.objects.filter(**kwargs).exists()

    return "".join(key)