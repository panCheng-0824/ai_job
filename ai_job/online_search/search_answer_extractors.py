from bs4 import BeautifulSoup
from readability import Document


def extract_body_text(response, logger) -> str:
    """
    详情页正文提取：
    1) 优先使用 readability
    2) 失败则回退到段落拼接
    """
    body = ""
    try:
        doc = Document(response.text)
        html = doc.summary(html_partial=True)
        body = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    except Exception as exc:
        logger.info("[STEP 3.1] readability 提取失败: %s", exc)

    if not body:
        body = " ".join(response.css("article p::text, p::text").getall()).strip()

    return body[:8000]
