export interface ArxivCategory {
  id: string;
  name: string;
  description: string;
  subcategories?: ArxivCategory[];
}

export const ARXIV_CS_CATEGORIES: ArxivCategory[] = [
  {
    id: 'cs.AI',
    name: 'Artificial Intelligence',
    description: 'Artificial Intelligence, including machine learning, natural language processing, computer vision, robotics, knowledge representation, and automated reasoning.',
    subcategories: [
      { id: 'cs.AI', name: 'General AI', description: 'General artificial intelligence topics' },
      { id: 'cs.LG', name: 'Machine Learning', description: 'Machine learning algorithms and theory' },
      { id: 'cs.CL', name: 'Computation and Language', description: 'Natural language processing and computational linguistics' },
      { id: 'cs.CV', name: 'Computer Vision', description: 'Computer vision and pattern recognition' },
      { id: 'cs.RO', name: 'Robotics', description: 'Robotics and automation' },
      { id: 'cs.NE', name: 'Neural and Evolutionary Computing', description: 'Neural networks, genetic algorithms, and evolutionary computation' },
    ]
  },
  {
    id: 'cs.TH',
    name: 'Theoretical Computer Science',
    description: 'Theoretical aspects of computer science, including algorithms, complexity theory, cryptography, logic, and formal methods.',
    subcategories: [
      { id: 'cs.DS', name: 'Data Structures and Algorithms', description: 'Data structures and algorithms' },
      { id: 'cs.CC', name: 'Computational Complexity', description: 'Computational complexity theory' },
      { id: 'cs.DM', name: 'Discrete Mathematics', description: 'Discrete mathematics and combinatorics' },
      { id: 'cs.IT', name: 'Information Theory', description: 'Information theory and coding' },
      { id: 'cs.CR', name: 'Cryptography and Security', description: 'Cryptography and computer security' },
      { id: 'cs.LO', name: 'Logic in Computer Science', description: 'Logic in computer science' },
    ]
  },
  {
    id: 'cs.SY',
    name: 'Systems and Control',
    description: 'Systems theory, control theory, and related areas including embedded systems, real-time systems, and cyber-physical systems.',
    subcategories: [
      { id: 'cs.SY', name: 'Systems and Control', description: 'General systems and control theory' },
      { id: 'cs.ET', name: 'Emerging Technologies', description: 'Emerging technologies' },
      { id: 'cs.AR', name: 'Hardware Architecture', description: 'Computer architecture and hardware design' },
      { id: 'cs.EM', name: 'Embedded Systems', description: 'Embedded systems and real-time computing' },
    ]
  },
  {
    id: 'cs.SE',
    name: 'Software Engineering',
    description: 'Software engineering, including software design, development methodologies, testing, maintenance, and empirical software engineering.',
    subcategories: [
      { id: 'cs.SE', name: 'Software Engineering', description: 'General software engineering topics' },
      { id: 'cs.PL', name: 'Programming Languages', description: 'Programming languages and compilers' },
      { id: 'cs.SD', name: 'Sound and Music Computing', description: 'Sound and music computing' },
    ]
  },
  {
    id: 'cs.DC',
    name: 'Distributed, Parallel, and Cluster Computing',
    description: 'Distributed systems, parallel computing, cluster computing, grid computing, and cloud computing.',
    subcategories: [
      { id: 'cs.DC', name: 'Distributed, Parallel, and Cluster Computing', description: 'General distributed and parallel computing' },
      { id: 'cs.NI', name: 'Networking and Internet Architecture', description: 'Computer networks and internet architecture' },
      { id: 'cs.PF', name: 'Performance', description: 'Performance evaluation and measurement' },
    ]
  },
  {
    id: 'cs.DB',
    name: 'Databases',
    description: 'Database systems, data management, data mining, information retrieval, and knowledge discovery.',
    subcategories: [
      { id: 'cs.DB', name: 'Databases', description: 'Database systems and data management' },
      { id: 'cs.IR', name: 'Information Retrieval', description: 'Information retrieval and search engines' },
      { id: 'cs.DL', name: 'Digital Libraries', description: 'Digital libraries and archives' },
    ]
  },
  {
    id: 'cs.CY',
    name: 'Computers and Society',
    description: 'Social and ethical aspects of computing, including privacy, security, accessibility, and the impact of computing on society.',
    subcategories: [
      { id: 'cs.CY', name: 'Computers and Society', description: 'Computers and society' },
      { id: 'cs.HC', name: 'Human-Computer Interaction', description: 'Human-computer interaction and user interfaces' },
    ]
  },
  {
    id: 'cs.MM',
    name: 'Multimedia',
    description: 'Multimedia computing, including graphics, image processing, video processing, audio processing, and multimedia systems.',
    subcategories: [
      { id: 'cs.MM', name: 'Multimedia', description: 'Multimedia computing' },
      { id: 'cs.GR', name: 'Graphics', description: 'Computer graphics and visualization' },
    ]
  },
  {
    id: 'cs.OH',
    name: 'Other Computer Science',
    description: 'Other computer science topics not covered by the main categories.',
    subcategories: [
      { id: 'cs.OH', name: 'Other Computer Science', description: 'Other computer science topics' },
      { id: 'cs.CE', name: 'Computational Engineering, Finance, and Science', description: 'Computational science and engineering' },
      { id: 'cs.FL', name: 'Formal Languages and Automata Theory', description: 'Formal languages and automata theory' },
      { id: 'cs.GT', name: 'Computer Science and Game Theory', description: 'Computer science and game theory' },
      { id: 'cs.MS', name: 'Mathematical Software', description: 'Mathematical software and numerical analysis' },
      { id: 'cs.NA', name: 'Numerical Analysis', description: 'Numerical analysis and scientific computing' },
      { id: 'cs.SC', name: 'Symbolic Computation', description: 'Symbolic computation and computer algebra' },
    ]
  }
];

export const ALL_CS_CATEGORIES: string[] = [
  'cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.RO', 'cs.NE',
  'cs.TH', 'cs.DS', 'cs.CC', 'cs.DM', 'cs.IT', 'cs.CR', 'cs.LO',
  'cs.SY', 'cs.ET', 'cs.AR', 'cs.EM',
  'cs.SE', 'cs.PL', 'cs.SD',
  'cs.DC', 'cs.NI', 'cs.PF',
  'cs.DB', 'cs.IR', 'cs.DL',
  'cs.CY', 'cs.HC',
  'cs.MM', 'cs.GR',
  'cs.OH', 'cs.CE', 'cs.FL', 'cs.GT', 'cs.MS', 'cs.NA', 'cs.SC'
];

export function getCategoryById(id: string): ArxivCategory | undefined {
  for (const category of ARXIV_CS_CATEGORIES) {
    if (category.id === id) return category;
    if (category.subcategories) {
      const subcategory = category.subcategories.find(sub => sub.id === id);
      if (subcategory) return subcategory;
    }
  }
  return undefined;
}

export function getCategoryName(id: string): string {
  const category = getCategoryById(id);
  return category ? category.name : id;
}

export function getCategoryDescription(id: string): string {
  const category = getCategoryById(id);
  return category ? category.description : 'No description available';
}

export function getMainCategory(id: string): ArxivCategory | undefined {
  for (const category of ARXIV_CS_CATEGORIES) {
    if (category.id === id) return category;
    if (category.subcategories?.some(sub => sub.id === id)) return category;
  }
  return undefined;
}