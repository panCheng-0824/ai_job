# `search_answer_spider.py` 代码解释文档

本文档对应文件：`online_search/search_answer_spider.py`  
目标：帮助你快速理解爬虫代码的设计思路、执行流程、日志含义与常见问题排查方式。

---

## 1. 代码整体目标

该爬虫用于根据用户问题进行网页检索，并抓取结果详情页正文，最终输出结构化 JSON 数据。核心能力如下：

- 输入问题（`query`）
- 选择搜索引擎（`baidu` / `duckduckgo`）
- 抓取前 `topk` 条搜索结果
- 提取详情页正文内容（优先主内容提取，失败时回退段落拼接）
- 输出 JSON 文件（便于后续问答摘要或知识加工）

---

## 2. 输入与输出

## 输入参数（命令行）

- `--query`：搜索问题文本
- `--demo`：内置测试问题编号（当 `query` 为空时生效）
- `--engine`：搜索引擎，支持 `baidu` 和 `duckduckgo`
- `--topk`：最多抓取多少条结果
- `--output`：输出 JSON 文件路径

## 输出字段（每条 item）

- `query`：原始问题
- `rank`：结果排名（按入队顺序）
- `title`：搜索结果标题
- `url`：结果链接
- `snippet`：搜索摘要（若有）
- `body`：详情页正文（已截断到 8000 字符）

---

## 3. 核心结构说明

## 3.1 关键成员变量

- `self.query`：当前问题
- `self.engine`：搜索引擎类型
- `self.topk`：抓取上限
- `self.collected`：已“成功入队详情页请求”的数量
- `self.seen_urls`：URL 去重集合
- `self.item_count`：已输出 item 数量

## 3.2 关键函数

- `_build_search_url()`  
  根据引擎和关键词拼接入口搜索 URL。

- `_build_search_request(url)`  
  统一构造入口请求，设置 `User-Agent`，减少被识别为脚本请求的概率。

- `start()`（Scrapy 2.13+ 推荐）  
  新版入口，发起搜索页请求。

- `start_requests()`（兼容旧版本）  
  保留旧入口，兼容 Scrapy 2.12 及以下。

- `parse_search(response)`  
  解析搜索结果页，提取候选链接并派发详情页请求。

- `parse_detail(response)`  
  解析详情页正文，输出结构化 item。

- `closed(reason)`  
  爬虫结束时打印总览统计日志。

---

## 4. 执行流程（对应日志 STEP）

代码中的日志采用 `STEP` 编号，便于定位阶段：

- `STEP 1`：构造入口请求并访问搜索页
- `STEP 2`：解析搜索页并入队详情页请求
- `STEP 3`：解析详情页正文并输出 item
- `STEP FINAL`：结束统计

## 4.1 STEP 1（入口阶段）

在 `start()` / `start_requests()` 中：

1. 校验 `query` 不为空
2. 通过 `_build_search_url()` 生成搜索页 URL
3. 打印入口日志（引擎、关键词、topk、URL）
4. 发起请求到 `parse_search`

## 4.2 STEP 2（搜索页解析阶段）

在 `parse_search()` 中：

1. 打印搜索页状态码和地址
2. 根据引擎选择解析策略  
   - `baidu`：优先按多组容器选择器提取  
   - `duckduckgo`：按 `a.result__a` 提取
3. 对 URL 做过滤与去重  
   - URL 为空跳过  
   - 非 `http` 链接跳过  
   - 已抓过链接跳过
4. 为每条结果派发详情页请求（回调 `parse_detail`）
5. 若百度主解析命中为 0，启用 `h3 a` 兜底解析
6. 打印入队完成统计

## 4.3 STEP 3（详情页解析阶段）

在 `parse_detail()` 中：

1. 读取 `meta` 传入的 `rank/title/url/snippet`
2. 优先使用 `readability` 提取正文主干
3. 若提取失败，回退为 `article p` 与 `p` 文本拼接
4. 将正文截断为 8000 字符
5. 打印输出日志（第几条、排名、正文长度）
6. `yield` 结构化结果

## 4.4 STEP FINAL（结束阶段）

在 `closed()` 中汇总打印：

- 结束原因 `reason`
- 入队详情页总数 `queued_details`
- 实际输出条数 `emitted_items`
- 去重后的 URL 数

---

## 5. 解析策略设计原因

## 5.1 为什么要有双入口（`start` + `start_requests`）

- `start` 是 Scrapy 2.13+ 推荐方式
- `start_requests` 保持旧版本兼容
- 两者都走统一请求构造，减少重复与维护成本

## 5.2 为什么要多套选择器 + 兜底

搜索引擎页面结构经常变化，单一选择器容易失效。当前方案采用：

- 主容器多选择器匹配
- 命中为 0 时启用兜底解析

这样可以显著降低“页面结构轻微变化导致 0 结果”的风险。

## 5.3 为什么正文提取要先主提取再回退

- `readability` 对新闻/文章页正文提取效果通常更好
- 部分网页结构复杂或异常时，`readability` 可能失败
- 回退到段落拼接能保证尽量产出内容，提升鲁棒性

---

## 6. 日志阅读指南（快速排查）

当你发现输出为 0 条，可按顺序看日志：

1. 是否看到 `STEP 1`（确认入口请求已发出）
2. `STEP 2` 的状态码是否正常（例如 200）
3. `STEP 2.1` 候选区块命中是否大于 0
4. 是否出现 `STEP 2.2` / `STEP 2.5`（是否有详情页入队）
5. 是否出现 `STEP 3`（详情页回调是否执行）
6. 看 `STEP FINAL` 中 `入队详情页` 与 `输出结果` 是否一致

---

## 7. 常见问题与处理建议

## 7.1 现象：`0 items` 且请求失败

常见原因：本地代理导致连接隧道失败（例如 `CONNECT tunnel ... 403`）。

建议：

- 检查运行环境是否设置了 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`
- 在终端临时取消代理后重试
- 排查本地代理软件是否拦截当前请求

## 7.2 现象：搜索页成功但无详情页入队

常见原因：搜索页结构变化，选择器未命中。

建议：

- 查看 `STEP 2.1` 的命中数量
- 观察是否触发了 `STEP 2.4` 兜底
- 使用浏览器开发者工具更新选择器规则

## 7.3 现象：有详情页但正文为空

常见原因：

- 目标页大量脚本渲染（静态 HTML 文本少）
- 正文在非标准结构中

建议：

- 增加更多正文选择器
- 引入可渲染 JS 的抓取方案（若业务需要）

---

## 8. 运行示例

```bash
/Users/a1234/PycharmProjects/ai_job/.venv/bin/python \
  /Users/a1234/PycharmProjects/ai_job/online_search/search_answer_spider.py \
  --query "人工智能就业趋势" \
  --engine baidu \
  --topk 5 \
  --output output.json
```

---

## 9. 后续可迭代方向

- 增加“日志详细级别开关”（例如 `--verbose-steps`）
- 增加域名级去重（避免同站点结果过多）
- 对 `body` 增加最小长度阈值与清洗规则
- 将搜索页 HTML 快照落盘（便于结构变化时回放调试）
- 增加单元测试（URL 构造、选择器回退、正文提取回退）

---

如果你希望，我可以下一步再给这份文档补一版“流程图（Mermaid）”，让你在 PR 或汇报里直接引用。
