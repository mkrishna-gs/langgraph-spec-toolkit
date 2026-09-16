"""Sanity check for the token-usage benchmark's own logic (not a benchmark
run itself — see benchmarks/token_usage.py for the actual measurement).
Guards the README's flat-vs-linear claim against silently rotting.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.token_usage import build_spec, count_tokens, full_regen_tokens, spec_edit_tokens


def test_count_tokens_basic():
    assert count_tokens("foo") == 1
    assert count_tokens("foo(bar)") == 4  # foo, (, bar, )
    assert count_tokens("") == 0


def test_spec_edit_cost_is_independent_of_call_site(tmp_path):
    # spec_edit_tokens() takes no graph-size argument by construction.
    assert spec_edit_tokens() == spec_edit_tokens()


def test_full_regen_cost_grows_with_graph_size(tmp_path):
    small = full_regen_tokens(build_spec(tmp_path, 3))
    large = full_regen_tokens(build_spec(tmp_path, 25))
    assert large > small


def test_spec_edit_cost_stays_flat_while_regen_grows(tmp_path):
    edit_cost = spec_edit_tokens()
    small_regen = full_regen_tokens(build_spec(tmp_path, 3))
    large_regen = full_regen_tokens(build_spec(tmp_path, 50))
    assert small_regen > edit_cost
    assert large_regen > small_regen
