/**
 * 行业分类树本地搜索：按名称、编码、ID、关键词、描述过滤。
 */

/** 参与匹配的字段 */
const MATCH_FIELDS = ["category_name", "category_code", "category_id", "intent_keywords", "description"];

/**
 * 判断单个节点是否命中关键词。
 * @param {Record<string, unknown>} node
 * @param {string} keyword 已 normalize 的小写关键词
 */
function nodeMatches(node, keyword) {
  if (!keyword) return true;
  for (const field of MATCH_FIELDS) {
    const text = String(node[field] ?? "").toLowerCase();
    if (text.includes(keyword)) return true;
  }
  return false;
}

/**
 * 过滤树形行业列表。
 * @param {Array} tree 原始一级树
 * @param {string} keyword 用户输入
 * @returns {{ items: Array, expandIds: string[], matchCount: number }}
 */
export function filterIndustryCategoryTree(tree, keyword) {
  const kw = String(keyword ?? "").trim().toLowerCase();
  const source = tree || [];

  if (!kw) {
    return { items: source, expandIds: [], matchCount: 0 };
  }

  const items = [];
  const expandIds = [];

  for (const l1 of source) {
    const l1Hit = nodeMatches(l1, kw);
    const children = l1.children || [];
    const matchedChildren = l1Hit ? children : children.filter((c) => nodeMatches(c, kw));

    if (!l1Hit && !matchedChildren.length) continue;

    if (!l1Hit && matchedChildren.length) {
      expandIds.push(l1.category_id);
    }

    items.push({
      ...l1,
      children: l1Hit ? children : matchedChildren
    });
  }

  let matchCount = 0;
  for (const l1 of source) {
    if (nodeMatches(l1, kw)) matchCount += 1;
    for (const c of l1.children || []) {
      if (nodeMatches(c, kw)) matchCount += 1;
    }
  }

  return { items, expandIds, matchCount };
}

/**
 * 统计树中一、二级节点总数。
 * @param {Array} tree
 */
export function countIndustryCategoryTree(tree) {
  const list = tree || [];
  const l1 = list.length;
  const l2 = list.reduce((n, x) => n + (x.children?.length || 0), 0);
  return { l1, l2, total: l1 + l2 };
}
