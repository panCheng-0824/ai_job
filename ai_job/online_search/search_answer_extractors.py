from ai_search.scrapy_engine.extractors import extract_body_text as _extract_body_text


def extract_body_text(response, logger) -> str:
    """
    详情页正文提取（实现位于 ai_search，此处保持兼容导入）。
    """
    return _extract_body_text(response, logger)
