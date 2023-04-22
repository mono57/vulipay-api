import hashlib

from django.conf import settings

class PassCodeGenerator(object):
    def __init__(self, code=None):
        self.code: str = code

    @classmethod
    def from_code(cls, code):
        return cls(code=code)

    def is_valid(self):
        return self.code.isdigit() and len(self.code) == settings.PASS_CODE_LENGTH

class Hasher:
    @classmethod
    def hash(cls, str_to_hash):
        hash_object = hashlib.sha256()
        hash_object.update(str_to_hash.encode('utf-8'))

        hex_dig = hash_object.hexdigest()

        return hex_dig
