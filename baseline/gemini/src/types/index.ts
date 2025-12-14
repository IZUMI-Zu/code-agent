export interface Author {
  name: string;
  affiliation?: string[];
}

export interface Paper {
  id: string;
  title: string;
  summary: string;
  authors: Author[];
  published: string;
  updated: string;
  categories: string[];
  links: {
    abs: string;
    pdf: string;
  };
}

export interface Category {
  id: string;
  name: string;
  description: string;
}

export const CS_CATEGORIES: Category[] = [
  { id: 'cs.AI', name: 'AI', description: 'Artificial Intelligence' },
  { id: 'cs.CL', name: 'Computation and Language', description: 'NLP, Linguistics' },
  { id: 'cs.CV', name: 'Computer Vision', description: 'Image Processing, Vision' },
  { id: 'cs.LG', name: 'Machine Learning', description: 'Deep Learning, ML' },
  { id: 'cs.SE', name: 'Software Engineering', description: 'Testing, Dev' },
  { id: 'cs.RO', name: 'Robotics', description: 'Robotics, Control' },
  { id: 'cs.CR', name: 'Cryptography and Security', description: 'Security' },
  { id: 'cs.DS', name: 'Data Structures and Algorithms', description: 'Algorithms' },
  { id: 'cs.DC', name: 'Distributed, Parallel, and Cluster Computing', description: 'Distributed Systems' },
  { id: 'cs.DB', name: 'Databases', description: 'Databases' },
  { id: 'cs.HC', name: 'Human-Computer Interaction', description: 'HCI' },
  { id: 'cs.NI', name: 'Networking and Internet Architecture', description: 'Networks' },
];
