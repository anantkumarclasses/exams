from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password):
    """
    Hash a plaintext password.
    :param password: Plaintext password
    :return: Hashed password
    """
    return generate_password_hash(password)

def verify_password(hashed_password, password):
    """
    Verify a plaintext password against its hash.
    :param password: Plaintext password
    :param hashed_password: Hashed password
    :return: True if match, else False
    """
    return check_password_hash(hashed_password, password)

