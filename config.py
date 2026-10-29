import os


def get_database_url() -> str:
    """Retrieve and validate the DATABASE_URL environment variable.

    Returns:
        The database connection URL string.

    Raises:
        ValueError: If DATABASE_URL is missing, empty, or whitespace-only.
    """
    url = os.environ.get("DATABASE_URL")
    if url is None:
        raise ValueError("DATABASE_URL environment variable is missing")
    if not url.strip():
        raise ValueError("DATABASE_URL environment variable is empty or contains only spaces")
    return url


if __name__ == "__main__":
    # Test 1: Valid URL
    os.environ["DATABASE_URL"] = "postgresql://localhost:5432/mydb"

    assert get_database_url() == "postgresql://localhost:5432/mydb"

    # Test 2: Missing URL
    os.environ.pop("DATABASE_URL", None)

    try:
        get_database_url()
    except ValueError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("Expected ValueError when DATABASE_URL is missing")

    # Test 3: Empty URL
    os.environ["DATABASE_URL"] = ""

    try:
        get_database_url()
    except ValueError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("Expected ValueError when DATABASE_URL is empty")

    # Test 4: Whitespace-only URL
    os.environ["DATABASE_URL"] = "   "

    try:
        get_database_url()
    except ValueError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("Expected ValueError when DATABASE_URL contains only spaces")

    print("All tests passed!")
