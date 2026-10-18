from trial_utils import format_trial_label


def test_format_trial_label_basic() -> None:
    """The label joins the trimmed title and the lowercase phase."""
    assert format_trial_label(" Metformin for Diabetes ", "PHASE2") == "Metformin for Diabetes (phase2)"