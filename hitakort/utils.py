def sel(text: str) -> str:
    """Strip each line

    Args:
        text (str): Text to be stripped

    Returns:
        str: Stripped text
    """
    return "\n".join(line.strip() for line in text.splitlines())
