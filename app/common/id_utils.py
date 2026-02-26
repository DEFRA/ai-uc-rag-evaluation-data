import secrets
import string


def generate_random_id(prefix: str, length: int = 12) -> str:
    """Generate a random ID with a custom prefix.

    Args:
        prefix: The prefix to use (e.g., 'kg', 'user', 'doc')
        length: Length of the random part (default 12)

    Returns:
        A string like '{prefix}_{randomString}'
    """
    alphabet = string.ascii_lowercase + string.digits
    random_part = "".join(secrets.choice(alphabet) for _ in range(length))

    return f"{prefix}_{random_part}"
