"""Tests for MCP tools coerce_list utility."""

from notebooklm_tools.mcp.tools._utils import coerce_list


class TestCoerceList:
    """Test coerce_list helper for MCP client compatibility."""

    def test_none_returns_none(self):
        assert coerce_list(None) is None

    def test_empty_string_returns_none(self):
        assert coerce_list("") is None
        assert coerce_list("   ") is None

    def test_actual_list_passthrough(self):
        assert coerce_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_json_string_list(self):
        assert coerce_list('["abc-123", "def-456"]') == ["abc-123", "def-456"]

    def test_comma_separated_string(self):
        assert coerce_list("abc-123,def-456") == ["abc-123", "def-456"]

    def test_comma_separated_with_spaces(self):
        assert coerce_list("abc-123, def-456, ghi-789") == ["abc-123", "def-456", "ghi-789"]

    def test_single_bare_value(self):
        assert coerce_list("abc-123") == ["abc-123"]

    def test_int_item_type(self):
        assert coerce_list("[0, 2, 5]", item_type=int) == [0, 2, 5]
        assert coerce_list("0,2,5", item_type=int) == [0, 2, 5]

    def test_int_list_passthrough(self):
        assert coerce_list([0, 2, 5], item_type=int) == [0, 2, 5]

    def test_single_int(self):
        assert coerce_list(3, item_type=int) == [3]

    def test_list_of_strings_cast_to_int(self):
        assert coerce_list(["1", "2", "3"], item_type=int) == [1, 2, 3]

    def test_empty_list_returns_empty(self):
        assert coerce_list([]) == []

    def test_malformed_json_falls_back_to_comma(self):
        # Starts with [ but isn't valid JSON
        assert coerce_list("[abc, def]") == ["[abc", "def]"]
