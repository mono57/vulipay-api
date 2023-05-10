import hashlib

from django.conf import settings

class PassCodeGenerator(object):
    def __init__(self, code=None):
        self.code: str = code

    @classmethod
    def from_code(cls, code):
        return cls(code=code)

    def is_valid(self):
        return self.code.isdigit() and len(self.code) == settings.PASSCODE_LENGTH