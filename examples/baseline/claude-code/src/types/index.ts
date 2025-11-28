// ============================================================
// 核心类型定义 - 统一的数据结构，消除特殊情况
// ============================================================

/**
 * arXiv 主要计算机科学领域
 * 通过统一的类型系统，所有领域都遵循相同的处理逻辑
 */
export const CS_CATEGORIES = {
  'cs.AI': '人工智能',
  'cs.CV': '计算机视觉与模式识别',
  'cs.CL': '计算与语言',
  'cs.LG': '机器学习',
  'cs.NE': '神经与进化计算',
  'cs.RO': '机器人学',
  'cs.CR': '密码学与安全',
  'cs.DC': '分布式、并行与集群计算',
  'cs.DS': '数据结构与算法',
  'cs.DB': '数据库',
  'cs.SE': '软件工程',
  'cs.PL': '编程语言',
  'cs.AR': '硬件架构',
  'cs.NI': '网络与互联网架构',
  'cs.SY': '系统与控制',
} as const;

export type CategoryKey = keyof typeof CS_CATEGORIES;

/**
 * 作者信息
 */
export interface Author {
  name: string;
  affiliation?: string;
}

/**
 * 论文核心数据结构
 * 设计原则：单一数据源，所有信息集中管理
 */
export interface Paper {
  id: string;              // arXiv ID (e.g., "2501.12345")
  title: string;
  authors: Author[];
  abstract: string;
  categories: CategoryKey[];  // 主分类和次级分类
  primaryCategory: CategoryKey;
  published: Date;
  updated: Date;
  pdfUrl: string;
  arxivUrl: string;
}

/**
 * arXiv API 响应条目（原始格式）
 */
export interface ArxivEntry {
  id: string;
  title: string;
  summary: string;
  author: Array<{ name: string }>;
  published: string;
  updated: string;
  category?: Array<{ term: string }>;
  'arxiv:primary_category'?: { term: string };
  link: Array<{ href: string; rel?: string; type?: string }>;
}
