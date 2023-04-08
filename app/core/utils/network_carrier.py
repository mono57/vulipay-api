import phonenumbers
from phonenumbers import carrier

NO_CARRIER = 'Unknown'

def get_carrier(phone_number, country_iso_code):
    p = phonenumbers.parse(phone_number, country_iso_code)
    _carrier = carrier.name_for_number(p, lang='en')

    if _carrier == '':
        return NO_CARRIER

    formated_carrier = f"{country_iso_code}_{'_'.join(_carrier.split(' '))}"

    return formated_carrier