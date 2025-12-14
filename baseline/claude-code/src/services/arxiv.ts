// ============================================================
// arXiv API 集成层
// 设计原则：单一职责 - 只负责数据获取和转换
// ============================================================

import type { Paper, CategoryKey, Author } from '../types';

// ============================================================
// CORS 代理配置
// arXiv API 不支持浏览器直接跨域请求，需要通过代理
// ============================================================

const ARXIV_API_BASE = '/api/arxiv';

// ============================================================
// 核心函数：获取每日论文
// ============================================================

/**
 * 获取指定分类的最新论文
 * @param category - CS 分类（如 'cs.AI'）
 * @param maxResults - 最大结果数（默认 50）
 */
export async function fetchPapers(
  category: CategoryKey,
  maxResults = 50
): Promise<Paper[]> {
  const params = new URLSearchParams({
    search_query: `cat:${category}`,
    sortBy: 'submittedDate',
    sortOrder: 'descending',
    max_results: maxResults.toString(),
  });

  const response = await fetch(`${ARXIV_API_BASE}?${params}`);
  const text = await response.text();

  return parseArxivResponse(text);
}

/**
 * 通过 arXiv ID 获取单篇论文详情
 */
export async function fetchPaperById(arxivId: string): Promise<Paper | null> {
  const params = new URLSearchParams({
    id_list: arxivId,
  });

  const response = await fetch(`${ARXIV_API_BASE}?${params}`);
  const text = await response.text();

  const papers = parseArxivResponse(text);
  return papers[0] || null;
}

// ============================================================
// 内部辅助函数：XML 解析
// ============================================================

/**
 * 解析 arXiv API 的 Atom XML 响应
 * 采用原生 DOMParser - 无外部依赖，简洁直白
 */
function parseArxivResponse(xmlText: string): Paper[] {
  const parser = new DOMParser();
  const doc = parser.parseFromString(xmlText, 'text/xml');
  const entries = doc.querySelectorAll('entry');

  const papers: Paper[] = [];

  entries.forEach(entry => {
    const paper = parseEntry(entry);
    if (paper) papers.push(paper);
  });

  return papers;
}

/**
 * 解析单个 entry 节点
 * 设计原则：提取信息，转换格式，无副作用
 */
function parseEntry(entry: Element): Paper | null {
  const id = extractText(entry, 'id');
  const title = extractText(entry, 'title').replace(/\s+/g, ' ').trim();
  const abstract = extractText(entry, 'summary').replace(/\s+/g, ' ').trim();

  if (!id || !title) return null;

  // 提取 arXiv ID (从 URL 中)
  const arxivId = id.split('/abs/')[1] || '';

  // 提取作者
  const authors = Array.from(entry.querySelectorAll('author')).map(author => ({
    name: extractText(author, 'name'),
  }));

  // 提取分类
  const categories = Array.from(entry.querySelectorAll('category'))
    .map(cat => cat.getAttribute('term'))
    .filter(term => term?.startsWith('cs.')) as CategoryKey[];

  const primaryCategory = entry.querySelector('arxiv\\:primary_category, primary_category')
    ?.getAttribute('term') as CategoryKey || categories[0];

  // 提取日期
  const published = new Date(extractText(entry, 'published'));
  const updated = new Date(extractText(entry, 'updated'));

  // 构建 URL
  const pdfUrl = `https://arxiv.org/pdf/${arxivId}.pdf`;
  const arxivUrl = `https://arxiv.org/abs/${arxivId}`;

  return {
    id: arxivId,
    title,
    authors,
    abstract,
    categories,
    primaryCategory,
    published,
    updated,
    pdfUrl,
    arxivUrl,
  };
}

/**
 * 提取 XML 节点文本内容
 */
function extractText(element: Element, tagName: string): string {
  return element.querySelector(tagName)?.textContent?.trim() || '';
}

// ============================================================
// 引用生成工具
// ============================================================

/**
 * 生成 BibTeX 引用
 */
export function generateBibtex(paper: Paper): string {
  const year = paper.published.getFullYear();
  const authors = paper.authors.map(a => a.name).join(' and ');
  const citationKey = `${paper.authors[0]?.name.split(' ').pop()}${year}`;

  return `@article{${citationKey},
  title={${paper.title}},
  author={${authors}},
  journal={arXiv preprint arXiv:${paper.id}},
  year={${year}}
}`;
}

/**
 * 生成标准学术引用格式（APA 风格）
 */
export function generateCitation(paper: Paper): string {
  const year = paper.published.getFullYear();
  const authorsStr = formatAuthors(paper.authors);

  return `${authorsStr} (${year}). ${paper.title}. arXiv preprint arXiv:${paper.id}.`;
}

/**
 * 格式化作者列表
 */
function formatAuthors(authors: Author[]): string {
  if (authors.length === 0) return '';
  if (authors.length === 1) return authors[0].name;
  if (authors.length === 2) return `${authors[0].name} & ${authors[1].name}`;

  const firstAuthors = authors.slice(0, -1).map(a => a.name).join(', ');
  const lastAuthor = authors[authors.length - 1].name;
  return `${firstAuthors}, & ${lastAuthor}`;
}
