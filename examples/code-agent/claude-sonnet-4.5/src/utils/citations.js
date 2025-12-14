/**
 * Generate BibTeX citation for a paper
 * @param {Object} paper - Paper object from arXiv API
 * @returns {string} BibTeX formatted citation
 */
export const generateBibTeX = (paper) => {
  const year = new Date(paper.published).getFullYear();
  const authorList = paper.authors.map(a => a.name).join(' and ');
  const cleanTitle = paper.title.replace(/[{}]/g, '');
  
  // Create a citation key from first author's last name and year
  const firstAuthor = paper.authors[0]?.name || 'Unknown';
  const lastName = firstAuthor.split(' ').pop().toLowerCase();
  const citationKey = `${lastName}${year}${paper.id.split('.')[1] || ''}`;

  return `@article{${citationKey},
  title={${cleanTitle}},
  author={${authorList}},
  journal={arXiv preprint arXiv:${paper.id}},
  year={${year}},
  url={https://arxiv.org/abs/${paper.id}}
}`;
};

/**
 * Generate standard academic citation (APA-style)
 * @param {Object} paper - Paper object from arXiv API
 * @returns {string} Standard formatted citation
 */
export const generateStandardCitation = (paper) => {
  const year = new Date(paper.published).getFullYear();
  
  // Format authors
  let authorText = '';
  if (paper.authors.length === 1) {
    authorText = paper.authors[0].name;
  } else if (paper.authors.length === 2) {
    authorText = `${paper.authors[0].name} & ${paper.authors[1].name}`;
  } else if (paper.authors.length > 2) {
    authorText = `${paper.authors[0].name}, et al.`;
  }

  return `${authorText} (${year}). ${paper.title}. arXiv preprint arXiv:${paper.id}. https://arxiv.org/abs/${paper.id}`;
};

/**
 * Copy text to clipboard
 * @param {string} text - Text to copy
 * @returns {Promise<boolean>} Success status
 */
export const copyToClipboard = async (text) => {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    } else {
      // Fallback for older browsers
      const textArea = document.createElement('textarea');
      textArea.value = text;
      textArea.style.position = 'fixed';
      textArea.style.left = '-999999px';
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      
      try {
        document.execCommand('copy');
        document.body.removeChild(textArea);
        return true;
      } catch (err) {
        document.body.removeChild(textArea);
        return false;
      }
    }
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};
