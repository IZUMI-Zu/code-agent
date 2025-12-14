/**
 * Generate BibTeX citation from paper data
 * @param {Object} paper - Paper object with title, authors, id, published, abstract
 * @returns {string} BibTeX formatted citation
 */
export function generateBibtex(paper) {
  const authors = paper.authors?.map(author => {
    const names = author.split(' ');
    const lastName = names.pop();
    const firstName = names.join(' ');
    return `${lastName}, ${firstName}`;
  }).join(' and ') || 'Unknown';

  const year = paper.published ? new Date(paper.published).getFullYear() : 'N.d.';
  const title = paper.title || 'Untitled';
  const identifier = paper.id?.split('/').pop() || 'unknown';

  return `@article{${identifier},
  title={${title}},
  author={${authors}},
  journal={arXiv preprint},
  year={${year}},
  url={https://arxiv.org/abs/${paper.id}}
}`;
}

/**
 * Generate APA style citation from paper data
 * @param {Object} paper - Paper object with title, authors, id, published, abstract
 * @returns {string} APA formatted citation
 */
export function generateAPA(paper) {
  const authors = paper.authors?.map((author) => {
    const names = author.split(' ');
    if (names.length === 1) return names[0];
    const lastName = names.pop();
    const initials = names.map(name => name.charAt(0).toUpperCase()).join('. ');
    return `${lastName}, ${initials}.`;
  }).join(', ') || 'Unknown';

  const year = paper.published ? new Date(paper.published).getFullYear() : 'N.d.';
  const title = paper.title || 'Untitled';

  return `${authors} (${year}). ${title}. arXiv preprint. https://arxiv.org/abs/${paper.id}`;
}

/**
 * Generate MLA style citation from paper data
 * @param {Object} paper - Paper object with title, authors, id, published, abstract
 * @returns {string} MLA formatted citation
 */
export function generateMLA(paper) {
  const authors = paper.authors?.map((author) => {
    const names = author.split(' ');
    if (names.length === 1) return names[0];
    const lastName = names.pop();
    const firstName = names.join(' ');
    return `${firstName} ${lastName}`;
  }).join(', ') || 'Unknown';

  const title = paper.title || 'Untitled';

  return `${authors}. "${title}." arXiv preprint, ${paper.id}.`;
}