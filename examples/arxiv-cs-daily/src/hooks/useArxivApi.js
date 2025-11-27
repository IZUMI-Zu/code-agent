import { useState, useEffect } from 'react';

/**
 * Custom hook for fetching data from the arXiv API
 * @param {string} url - The API endpoint to fetch data from
 * @returns {Object} - Object containing data, loading state, and error state
 */
export const useArxivApi = (url) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!url) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(url);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch data: ${response.status}`);
        }
        
        const text = await response.text();
        setData(text);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [url]);

  return { data, loading, error };
};