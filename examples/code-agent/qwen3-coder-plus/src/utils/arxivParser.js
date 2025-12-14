/**
 * Parses arXiv XML response into JavaScript objects
 * @param {string} xmlText - The raw XML text from arXiv API
 * @returns {Array} - Array of paper objects
 */
export const parseArxivPapers = (xmlText) => {
  // Create a temporary DOM parser
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
  
  // Check for parser errors
  const parserError = xmlDoc.querySelector('parsererror');
  if (parserError) {
    throw new Error('Invalid XML format');
  }
  
  // Extract papers from the XML
  const entries = xmlDoc.querySelectorAll('entry');
  const papers = [];
  
  entries.forEach(entry => {
    const id = entry.querySelector('id')?.textContent || '';
    const title = entry.querySelector('title')?.textContent || '';
    const summary = entry.querySelector('summary')?.textContent || '';
    const published = entry.querySelector('published')?.textContent || '';
    const updated = entry.querySelector('updated')?.textContent || '';
    
    // Extract authors
    const authors = Array.from(entry.querySelectorAll('author name'))
      .map(author => author.textContent);
    
    // Extract categories
    const categories = Array.from(entry.querySelectorAll('category'))
      .map(category => category.getAttribute('term'));
    
    // Extract links
    const links = Array.from(entry.querySelectorAll('link'))
      .map(link => ({
        href: link.getAttribute('href'),
        rel: link.getAttribute('rel'),
        type: link.getAttribute('type')
      }));
    
    papers.push({
      id,
      title,
      summary,
      published,
      updated,
      authors,
      categories,
      links
    });
  });
  
  return papers;
};

/**
 * Formats a paper object for display
 * @param {Object} paper - The paper object to format
 * @returns {Object} - Formatted paper object
 */
export const formatPaper = (paper) => {
  return {
    ...paper,
    // Format dates
    publishedFormatted: new Date(paper.published).toLocaleDateString(),
    updatedFormatted: new Date(paper.updated).toLocaleDateString(),
    
    // Get primary category
    primaryCategory: paper.categories[0] || 'cs',
    
    // Get abstract link
    abstractLink: paper.links.find(link => link.rel === 'alternate')?.href || '',
    
    // Get PDF link
    pdfLink: paper.links.find(link => link.type === 'application/pdf')?.href || ''
  };
};