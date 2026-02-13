"""Tests for BoundSmith core boundary extraction and generation."""
import pytest

from boundsmith import (
    extract_boundaries, extract_test_values,
    find_uncovered, generate_test_file,
)



def test_extract_simple_gt():
    bounds = extract_boundaries("if x > 3: pass")
    b = next(b for b in bounds if b.variable == "x")
    assert b.operator == ">"
    assert b.value == 3
    assert b.triplet == (2, 3, 4)


def test_extract_all_operators():
    code = (
        "if a >= 10: pass\n"
        "if b < 0: pass\n"
        "if c == 5: pass\n"
        "if d != -1: pass\n"
    )
    bounds = extract_boundaries(code)
    ops = {b.variable: b.operator for b in bounds
           if b.variable in {"a", "b", "c", "d"}}
    assert ops["a"] == ">="
    assert ops["b"] == "<"
    assert ops["c"] == "=="
    assert ops["d"] == "!="


def test_extract_chained_comparison():
    bounds = extract_boundaries("if 0 < x < 100: pass")
    x_vals = {b.value for b in bounds if b.variable == "x"}
    assert 0 in x_vals
    assert 100 in x_vals


def test_extract_len_call():
    bounds = extract_boundaries("if len(items) == 0: pass")
    b = next(b for b in bounds if "len" in b.variable)
    assert b.value == 0
    assert b.triplet == (-1, 0, 1)


def test_extract_negative_literal():
    bounds = extract_boundaries("if temp <= -10: pass")
    b = next(b for b in bounds if b.variable == "temp")
    assert b.value == -10
    assert b.triplet == (-11, -10, -9)


def test_extract_test_values():
    code = "def test_x():\n    assert f(0) == True\n    assert f(42) == False\n"
    vals = extract_test_values(code)
    assert {0, 42}.issubset(vals)


def test_find_uncovered_detects_gap():
    bounds = extract_boundaries("if retry > 3: pass")
    uncovered = find_uncovered(bounds, {0, 10})
    assert len(uncovered) >= 1
    assert uncovered[0].value == 3


def test_find_covered_returns_empty():
    bounds = extract_boundaries("if x > 3: pass")
    uncovered = find_uncovered(bounds, {2, 3, 4})
    assert len(uncovered) == 0


def test_generate_test_file_output():
    bounds = extract_boundaries("if count >= 5: pass")
    output = generate_test_file(bounds)
    assert "import pytest" in output
    assert "parametrize" in output
    assert "4" in output
    assert "5" in output
    assert "6" in output
    assert "def test_boundary_count_0" in output


def test_no_boundaries_in_plain_code():
    bounds = extract_boundaries("x = 1\ny = x + 2\nprint(y)\n")
    assert len(bounds) == 0


def test_float_boundary():
    bounds = extract_boundaries("if ratio > 0.5: pass")
    assert abs(b.triplet[2] - 0.6) < 0.01


# ---------------------------------------------------------------------------
# Chained comparisons
# ---------------------------------------------------------------------------

def test_extract_chained_comparison_operators():
    """Chained comparison 0 < x < 100 should yield correct operators."""
    bounds = extract_boundaries("if 0 < x < 100: pass")
    x_bounds = {b.value: b.operator for b in bounds if b.variable == "x"}
    assert x_bounds[0] == ">"
    assert x_bounds[100] == "<"


def test_extract_chained_comparison_three_parts():
    """1 <= x <= 10 should extract both endpoints."""
    bounds = extract_boundaries("if 1 <= x <= 10: pass")
    x_vals = {b.value for b in bounds if b.variable == "x"}
    assert 1 in x_vals
    assert 10 in x_vals


def test_extract_chained_comparison_mixed_ops():
    """Mixed operators in chained comparison: 0 < x <= 50."""
    bounds = extract_boundaries("if 0 < x <= 50: pass")
    x_bounds = {b.value: b.operator for b in bounds if b.variable == "x"}
    assert x_bounds[0] == ">"
    assert x_bounds[50] == "<="


# ---------------------------------------------------------------------------
# len() checks
# ---------------------------------------------------------------------------

def test_extract_len_ge():
    """len(s) >= 3 should extract boundary 3 with >= operator."""
    bounds = extract_boundaries("if len(s) >= 3: pass")
    b = next(b for b in bounds if "len" in b.variable)
    assert b.value == 3
    assert b.operator == ">="
    assert b.triplet == (2, 3, 4)


def test_extract_len_lt():
    """len(data) < 10 should extract boundary 10."""
    bounds = extract_boundaries("if len(data) < 10: pass")
    b = next(b for b in bounds if "len" in b.variable)
    assert b.value == 10
    assert b.operator == "<"


# ---------------------------------------------------------------------------
# None checks  (not yet implemented → xfail)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_extract_none_is():
    """if val is None should extract boundary [None]."""
    bounds = extract_boundaries("if val is None: pass")
    b = next(b for b in bounds if b.variable == "val")
    assert b.value is None
    assert b.operator == "is"


@pytest.mark.xfail(reason="not yet implemented")
def test_extract_none_is_not():
    """if val is not None should extract boundary [None]."""
    bounds = extract_boundaries("if val is not None: pass")
    b = next(b for b in bounds if b.variable == "val")
    assert b.value is None
    assert b.operator == "is not"


# ---------------------------------------------------------------------------
# Boolean combinations (and / or)
# ---------------------------------------------------------------------------

def test_extract_bool_and():
    """if x > 0 and x < 10 should extract boundaries [0, 10]."""
    bounds = extract_boundaries("if x > 0 and x < 10: pass")
    x_vals = {b.value for b in bounds if b.variable == "x"}
    assert 0 in x_vals
    assert 10 in x_vals


def test_extract_bool_or():
    """if x < 0 or x > 100 should extract boundaries [0, 100]."""
    bounds = extract_boundaries("if x < 0 or x > 100: pass")
    x_vals = {b.value for b in bounds if b.variable == "x"}
    assert 0 in x_vals
    assert 100 in x_vals


def test_extract_bool_and_operators():
    """Boolean AND preserves correct operators for each comparison."""
    bounds = extract_boundaries("if x > 0 and x < 10: pass")
    x_bounds = {b.value: b.operator for b in bounds if b.variable == "x"}
    assert x_bounds[0] == ">"
    assert x_bounds[10] == "<"


def test_extract_bool_and_different_vars():
    """Boolean AND with different variables extracts all boundaries."""
    bounds = extract_boundaries("if age >= 18 and score < 100: pass")
    var_vals = {b.variable: b.value for b in bounds
                if b.variable in {"age", "score"}}
    assert var_vals["age"] == 18
    assert var_vals["score"] == 100


# ---------------------------------------------------------------------------
# Nested conditionals
# ---------------------------------------------------------------------------

def test_extract_nested_if():
    """Nested if statements should extract boundaries from both levels."""
    code = (
        "if x > 5:\n"
        "    if y < 20:\n"
        "        pass\n"
    )
    bounds = extract_boundaries(code)
    var_vals = {b.variable: b.value for b in bounds
                if b.variable in {"x", "y"}}
    assert var_vals["x"] == 5
    assert var_vals["y"] == 20


def test_extract_nested_if_line_numbers():
    """Nested ifs should report correct line numbers."""
    code = (
        "if x > 5:\n"
        "    if y < 20:\n"
        "        pass\n"
    )
    bounds = extract_boundaries(code)
    lines = {b.variable: b.line for b in bounds
             if b.variable in {"x", "y"}}
    assert lines["x"] == 1
    assert lines["y"] == 2


def test_extract_nested_if_three_levels():
    """Three levels of nesting should extract all boundaries."""
    code = (
        "if a >= 1:\n"
        "    if b <= 50:\n"
        "        if c == 7:\n"
        "            pass\n"
    )
    bounds = extract_boundaries(code)
    var_vals = {b.variable: b.value for b in bounds
                if b.variable in {"a", "b", "c"}}
    assert var_vals["a"] == 1
    assert var_vals["b"] == 50
    assert var_vals["c"] == 7


# ---------------------------------------------------------------------------
# Walrus operator  (not yet implemented → xfail)
# ---------------------------------------------------------------------------

@pytest.mark.xfail(reason="not yet implemented")
def test_extract_walrus_operator():
    """if (n := len(data)) > 0 should extract boundary [0]."""
    bounds = extract_boundaries("if (n := len(data)) > 0: pass")
    vals = {b.value for b in bounds}
    assert 0 in vals


@pytest.mark.xfail(reason="not yet implemented")
def test_extract_walrus_comparison_ge():
    """if (count := get_count()) >= 5 should extract boundary [5]."""
    bounds = extract_boundaries("if (count := get_count()) >= 5: pass")
    vals = {b.value for b in bounds}
    assert 5 in vals


# ---------------------------------------------------------------------------
# match/case
# ---------------------------------------------------------------------------

def test_extract_match_case_guard():
    """Match/case guard with comparison should extract boundary."""
    code = (
        "match command:\n"
        "    case x if x > 10:\n"
        "        pass\n"
    )
    bounds = extract_boundaries(code)
    vals = {b.value for b in bounds}
    assert 10 in vals


@pytest.mark.xfail(reason="not yet implemented")
def test_extract_match_case_literal_values():
    """Match/case literal patterns should be extracted as boundaries."""
    code = (
        "match status:\n"
        "    case 200:\n"
        "        pass\n"
        "    case 404:\n"
        "        pass\n"
        "    case 500:\n"
        "        pass\n"
    )
    bounds = extract_boundaries(code)
    vals = {b.value for b in bounds}
    assert 200 in vals
    assert 404 in vals
    assert 500 in vals

    assert b.value == 0.5
    assert abs(b.triplet[0] - 0.4) < 0.01
    assert abs(b.triplet[2] - 0.6) < 0.01
