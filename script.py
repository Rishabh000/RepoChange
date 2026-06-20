"""A small data processing utility."""


def normalize(records):
    """Lowercase and strip whitespace from string fields."""
    cleaned = []
    for record in records:
        cleaned.append({k: (v.strip().lower() if isinstance(v, str) else v)
                        for k, v in record.items()})
    return cleaned


def summarize(records):
    """Return basic counts about the records."""
    return {"count": len(records)}


if __name__ == "__main__":
    sample = [{"name": "  Alice  "}, {"name": "BOB"}]
    print(normalize(sample))
    print(summarize(sample))
