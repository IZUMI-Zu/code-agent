import { CS_CATEGORIES } from '../types';
import type { Paper, Author } from '../types';

const BASE_URL = '/api/query';

export const fetchPapers = async (category: string, start = 0, maxResults = 20): Promise<Paper[]> => {
  let catQuery = '';
  if (category === 'cs') {
    catQuery = CS_CATEGORIES.map(c => `cat:${c.id}`).join('+OR+');
    catQuery = `(${catQuery})`;
  } else {
    catQuery = `cat:${category}`;
  }

  const query = `search_query=${catQuery}&sortBy=submittedDate&sortOrder=descending&start=${start}&max_results=${maxResults}`;
  const response = await fetch(`${BASE_URL}?${query}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch papers: ${response.statusText}`);
  }

  const text = await response.text();
  return parseArxivResponse(text);
};

export const fetchPaperById = async (id: string): Promise<Paper | null> => {
  // ID might be a URL or just the id part. arXiv API expects just the id part often, or id_list.
  // If we have "2310.12345", we can use id_list.
  // The id passed from the router might be "2310.12345v1" or similar.
  
  // Clean the ID if it's a full URL (though we likely pass the short ID)
  const cleanId = id.replace(/^http:\/\/arxiv\.org\/abs\//, '').replace(/^https:\/\/arxiv\.org\/abs\//, '');

  const query = `id_list=${cleanId}`;
  const response = await fetch(`${BASE_URL}?${query}`);
  
  if (!response.ok) {
    throw new Error(`Failed to fetch paper: ${response.statusText}`);
  }

  const text = await response.text();
  const papers = parseArxivResponse(text);
  return papers.length > 0 ? papers[0] : null;
};

const parseArxivResponse = (xmlText: string): Paper[] => {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
  const entries = xmlDoc.getElementsByTagName('entry');
  
  const papers: Paper[] = [];

  for (let i = 0; i < entries.length; i++) {
    const entry = entries[i];
    
    const id = entry.getElementsByTagName('id')[0]?.textContent || '';
    // arXiv ID is usually the last part of the URL in the ID tag
    // e.g. http://arxiv.org/abs/2310.00000
    // We want to keep the full URL for linking, but maybe extract a short ID for routing.
    // For routing, we'll extract the versioned ID.
    
    const title = entry.getElementsByTagName('title')[0]?.textContent?.replace(/\s+/g, ' ').trim() || '';
    const summary = entry.getElementsByTagName('summary')[0]?.textContent?.trim() || '';
    const published = entry.getElementsByTagName('published')[0]?.textContent || '';
    const updated = entry.getElementsByTagName('updated')[0]?.textContent || '';

    const authorTags = entry.getElementsByTagName('author');
    const authors: Author[] = [];
    for (let j = 0; j < authorTags.length; j++) {
      const name = authorTags[j].getElementsByTagName('name')[0]?.textContent || '';
      // Affiliation is sometimes present but not always exposed easily in simple Atom without parsing extensions.
      // We'll stick to name for now.
      authors.push({ name });
    }

    const categoryTags = entry.getElementsByTagName('category');
    const categories: string[] = [];
    for (let j = 0; j < categoryTags.length; j++) {
      const term = categoryTags[j].getAttribute('term');
      if (term) categories.push(term);
    }

    const linkTags = entry.getElementsByTagName('link');
    let pdfLink = '';
    let absLink = id; // Default to ID which is usually the abs link

    for (let j = 0; j < linkTags.length; j++) {
      const rel = linkTags[j].getAttribute('rel');
      const href = linkTags[j].getAttribute('href');
      const titleAttr = linkTags[j].getAttribute('title');
      
      if (rel === 'alternate' && !titleAttr) {
        absLink = href || '';
      } else if (titleAttr === 'pdf') {
        pdfLink = href || '';
      }
    }

    papers.push({
      id,
      title,
      summary,
      authors,
      published,
      updated,
      categories,
      links: {
        abs: absLink,
        pdf: pdfLink
      }
    });
  }

  return papers;
};
