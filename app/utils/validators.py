import re

def is_valid_email(email):
    """
    Validate an email address.
    :param email: Email address to validate
    :return: True if valid, else False
    """
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email) is not None

def is_strong_password(password):
    """
    Check if a password is strong.
    A strong password has at least 8 characters, including an uppercase letter,
    a lowercase letter, a number, and a special character.
    :param password: Password to validate
    :return: True if strong, else False
    """
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

