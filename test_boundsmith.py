"""Tests for BoundSmith core boundary extraction and generation."""
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
    b = next(b for b in bounds if b.variable == "ratio")
    assert b.value == 0.5
    assert abs(b.triplet[0] - 0.4) < 0.01
    assert abs(b.triplet[2] - 0.6) < 0.01



def test_empty_source_returns_no_boundaries():
    """Empty input must not crash and must return an empty list."""
    bounds = extract_boundaries("")
    assert bounds == []


def test_malformed_python_does_not_crash():
    """Malformed input must not raise an unhandled exception."""
    try:
        bounds = extract_boundaries("if x > : pass")
    except SyntaxError:
        pass  # acceptable — as long as it doesn't produce a traceback
    else:
        assert isinstance(bounds, list)


def test_le_operator_triplet():
    bounds = extract_boundaries("if x <= 5: pass")
    b = next(b for b in bounds if b.variable == "x")
    assert b.operator == "<="
    assert b.value == 5
    assert b.triplet == (4, 5, 6)


def test_multiple_conditions_on_same_line():
    """Compound boolean conditions must each produce a boundary."""
    bounds = extract_boundaries("if x > 0 and y < 10: pass")
    vars_found = {b.variable for b in bounds}
    assert "x" in vars_found
    assert "y" in vars_found


def test_find_uncovered_with_empty_test_values():
    """When no test values are provided, all boundaries are uncovered."""
    bounds = extract_boundaries("if x > 3: pass")
    uncovered = find_uncovered(bounds, set())
    assert len(uncovered) == len(bounds)
