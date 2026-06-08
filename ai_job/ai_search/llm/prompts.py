"""LLM Prompt 模板。"""

MODE_ADVISOR_PROMPT = """你是网页采集模式调度器。根据任务信息输出唯一模式：drission、scrapy、hybrid。
- require_login=true 且无现成 session → hybrid
- 需要 JS 渲染且单页 → drission
- 公开静态多页 → scrapy

只输出一个英文单词，不要解释。

任务:
url={url}
require_login={require_login}
has_session={has_session}
prompt={prompt}
"""

SELECTOR_PROMPT = """根据页面文本摘要和用户采集需求，给出一个 CSS 选择器，用于选取「详情页或列表项」的 <a> 链接。
只输出一行 CSS，不要 markdown，不要解释。若无法判断输出 NONE。

用户需求: {prompt}

页面摘要:
{page_text}
"""

PARSE_PROMPT = """从以下网页正文中，按用户需求提取结构化 JSON。
只输出合法 JSON 对象或 JSON 数组，不要 markdown 代码块。

用户需求: {prompt}

正文:
{body}
"""
