"""One declared model policy shared by the interface and numeric acceptance."""

DEFAULT_MODE = 'unified'
POLICY_VERSION = 'original_three_stable_20261117'


def initial_mode(saved_mode=None):
    return saved_mode if saved_mode in ('unified', 'current') else DEFAULT_MODE
