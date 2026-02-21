def sanitize_name(name: str) -> str:
    """
    Converts a human-readable problem name into a filesystem-safe slug.
    e.g. "Two Sum" -> "two-sum", "A/B Split" -> "a-b-split"
    """
    return name.lower().replace(" ", "-").replace("/", "-")
