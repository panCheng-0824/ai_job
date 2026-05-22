/**
 * @typedef {Object} ResumeContent
 * @property {Record<string, string>} basic
 * @property {{ targetJobs: string, targetCompanies: string }} intent
 * @property {Record<string, string | Array<{ id: string, title?: string, body: string }>>} sections
 * @property {string} extraNotes
 */

/**
 * @typedef {Object} ResumeRecord
 * @property {string} id
 * @property {string} templateId
 * @property {string} displayName
 * @property {ResumeContent} content
 * @property {number} createdAt
 * @property {number} updatedAt
 * @property {boolean} [isDefault] 对话/规划师引用的全局默认
 * @property {boolean} [isSeriesDefault] 该简历线下的默认副本
 * @property {string} [seriesId] 同一逻辑简历多版本分组 id
 */

export {};
