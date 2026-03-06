import pytest

from maestro.tmps.parser import ParseError, parse_tmps, split_with_escape


BASE_TMPS = "\n".join(
    [
        "V 2.4|sid|run|1",
        "A 1111|9999|P|good",
        "B 1:imp|do one",
        "B 2:tst|do two",
        "B 3:doc|do three",
        "C A|1|2|*",
    ]
)


def test_split_with_escape_pipe():
    assert split_with_escape(r"a\|b|c") == ["a|b", "c"]


def test_parse_canonical():
    rec = parse_tmps(BASE_TMPS)
    assert rec.v.ver == "2.4"
    assert rec.c.decision == "A"


def test_tmps_parser_strict_rejects_blank_lines_and_missing_v():
    with pytest.raises(ParseError, match="blank line"):
        parse_tmps(BASE_TMPS.replace("\nA ", "\n\nA "), strict=True)

    with pytest.raises(ParseError, match="missing V"):
        parse_tmps(BASE_TMPS.split("\n", 1)[1], strict=True)


def test_tmps_parser_strict_rejects_invalid_agent_and_pri_range():
    bad_agent = BASE_TMPS.replace("B 1:imp|do one", "B 1:IMPL|do one")
    with pytest.raises(ParseError, match="B agent"):
        parse_tmps(bad_agent, strict=True)

    bad_pri = BASE_TMPS.replace("B 1:imp|do one", "B 8:imp|do one")
    with pytest.raises(ParseError, match="B pri range"):
        parse_tmps(bad_pri, strict=True)


def test_rejects_unescaped_pipe_in_b_action():
    raw = BASE_TMPS.replace("B 1:imp|do one", "B 1:imp|do|one")
    with pytest.raises(ParseError, match="B action"):
        parse_tmps(raw, strict=True)
