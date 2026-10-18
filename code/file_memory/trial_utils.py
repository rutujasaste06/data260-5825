def format_trial_label(title: str, phase: str) -> str:
    """Return a short label like 'Metformin for Diabetes (phase2)'."""
    return f"{title.strip()[:100]} ({phase.strip().lower()})"