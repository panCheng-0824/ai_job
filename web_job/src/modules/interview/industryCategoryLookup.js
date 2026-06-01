/**
 * 行业分类树节点查找（纯逻辑）。
 */

/**
 * 在树中查找分类节点。
 * @param {Array} tree
 * @param {string} categoryId
 * @returns {{ category_id: string, category_name: string, level: number, path: string } | null}
 */
export function findIndustryCategory(tree, categoryId) {
  if (!categoryId) return null;
  for (const l1 of tree || []) {
    if (l1.category_id === categoryId) {
      return {
        category_id: l1.category_id,
        category_name: l1.category_name,
        level: 1,
        path: l1.category_name
      };
    }
    for (const l2 of l1.children || []) {
      if (l2.category_id === categoryId) {
        return {
          category_id: l2.category_id,
          category_name: l2.category_name,
          level: 2,
          path: `${l1.category_name} / ${l2.category_name}`
        };
      }
    }
  }
  return null;
}
