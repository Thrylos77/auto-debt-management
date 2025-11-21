from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

phone_validator = RegexValidator(
    regex=r'^\+?\d{7,15}$',
    message='Enter a valid phone number (7 to 15 digits, optional leading +).'
)   
