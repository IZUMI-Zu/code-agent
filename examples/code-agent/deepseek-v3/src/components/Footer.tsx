import React from 'react';
import { Link } from 'react-router-dom';

const Footer: React.FC = () => {
  const currentYear = new Date().getFullYear();

  return (
    <footer className="bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Brand and description */}
          <div className="md:col-span-2">
            <div className="flex items-center space-x-2 mb-4">
              <div className="h-8 w-8 bg-blue-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">arXiv</span>
              </div>
              <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                arXiv CS Daily
              </h3>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              A streamlined interface for tracking daily computer science preprints from arXiv.org. 
              Stay updated with the latest research in AI, theory, systems, and more.
            </p>
            <div className="flex items-center space-x-4">
              <a
                href="https://arxiv.org"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium"
              >
                arXiv.org
              </a>
              <a
                href="https://arxiv.org/help/api"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-300 text-sm"
              >
                API Documentation
              </a>
            </div>
          </div>

          {/* Quick links */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
              Quick Links
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  to="/"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Latest Papers
                </Link>
              </li>
              <li>
                <a
                  href="https://arxiv.org/list/cs/recent"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  arXiv CS Recent
                </a>
              </li>
              <li>
                <a
                  href="https://arxiv.org/help/submit"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Submit to arXiv
                </a>
              </li>
              <li>
                <a
                  href="https://arxiv.org/help"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Help & Support
                </a>
              </li>
            </ul>
          </div>

          {/* Categories */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-white uppercase tracking-wider mb-4">
              Top Categories
            </h4>
            <ul className="space-y-2">
              <li>
                <Link
                  to="/?category=cs.AI"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Artificial Intelligence
                </Link>
              </li>
              <li>
                <Link
                  to="/?category=cs.LG"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Machine Learning
                </Link>
              </li>
              <li>
                <Link
                  to="/?category=cs.CV"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Computer Vision
                </Link>
              </li>
              <li>
                <Link
                  to="/?category=cs.TH"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Theory
                </Link>
              </li>
              <li>
                <Link
                  to="/?category=cs.SY"
                  className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 text-sm"
                >
                  Systems
                </Link>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-8 pt-8 border-t border-gray-200 dark:border-gray-800">
          <div className="flex flex-col md:flex-row justify-between items-center space-y-4 md:space-y-0">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              © {currentYear} arXiv CS Daily. This service is not affiliated with arXiv.org.
            </div>
            <div className="flex items-center space-x-6">
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Data sourced from{' '}
                <a
                  href="https://arxiv.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 dark:text-blue-400 hover:underline"
                >
                  arXiv.org
                </a>
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400">
                Built with React, TypeScript & Tailwind CSS
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="mt-4 text-xs text-gray-500 dark:text-gray-500 text-center">
            <p>
              arXiv is a trademark of Cornell University. This interface provides enhanced access to 
              publicly available arXiv data. All papers are copyright of their respective authors.
            </p>
            <p className="mt-1">
              Papers are updated daily. Please cite papers according to their arXiv identifiers.
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;