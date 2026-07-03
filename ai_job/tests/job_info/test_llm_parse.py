from app.skills.job_info.llm_parse import RecomJsonParseError, parse_recom_json


def test_parse_fenced_json():
    text = "```json\n{\"isrecommend\":\"yes\",\"reason\":\"x\",\"recomList\":[]}\n```"
    assert parse_recom_json(text)["isrecommend"] == "yes"


def test_parse_trailing_comma():
    text = "{\"isrecommend\":\"yes\",\"reason\":\"x\",\"recomList\":[],}"
    assert parse_recom_json(text)["isrecommend"] == "yes"


def test_parse_with_prefix_suffix():
    text = "说明如下：{\"isrecommend\":\"no\",\"reason\":\"无\",\"recomList\":[]} 完毕"
    assert parse_recom_json(text)["isrecommend"] == "no"


def test_parse_invalid_raises():
    try:
        parse_recom_json("not json at all")
        assert False, "should raise"
    except RecomJsonParseError as e:
        assert e.raw_preview
