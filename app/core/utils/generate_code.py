import random
import string

from django.conf import settings
from django.db import models
from django.db.models import Q


def generate_code(
    Model: models.Model,
    lookup_field="code",
    unique=True,
    sequence=string.digits,
    length=settings.VERIFICATION_CODE_LENGTH,
) -> str:

    code_exists, code = True, ""

    while code_exists and unique:
        code = random.choices(sequence, k=length)
        kwargs = {lookup_field: code}
        code_exists = Model.objects.filter(**kwargs).exists()

    return "".join(code)
