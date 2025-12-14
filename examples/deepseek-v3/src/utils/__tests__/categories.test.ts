import { describe, it, expect } from 'vitest';
import {
  ARXIV_CS_CATEGORIES,
  ALL_CS_CATEGORIES,
  getCategoryById,
  getCategoryName,
  getCategoryDescription,
  getMainCategory,
} from '../categories';

describe('arXiv CS Categories', () => {
  it('should have all major CS categories', () => {
    expect(ARXIV_CS_CATEGORIES).toBeDefined();
    expect(ARXIV_CS_CATEGORIES.length).toBeGreaterThan(0);
    
    // Check for some major categories
    const categoryIds = ARXIV_CS_CATEGORIES.map(cat => cat.id);
    expect(categoryIds).toContain('cs.AI');
    expect(categoryIds).toContain('cs.TH');
    expect(categoryIds).toContain('cs.SY');
    expect(categoryIds).toContain('cs.SE');
  });

  it('should have all CS categories in ALL_CS_CATEGORIES', () => {
    expect(ALL_CS_CATEGORIES).toBeDefined();
    expect(ALL_CS_CATEGORIES.length).toBeGreaterThan(30); // Should have many CS categories
    
    // Check for some specific categories
    expect(ALL_CS_CATEGORIES).toContain('cs.AI');
    expect(ALL_CS_CATEGORIES).toContain('cs.LG');
    expect(ALL_CS_CATEGORIES).toContain('cs.CV');
    expect(ALL_CS_CATEGORIES).toContain('cs.TH');
  });

  describe('getCategoryById', () => {
    it('should return category for valid ID', () => {
      const category = getCategoryById('cs.AI');
      expect(category).toBeDefined();
      expect(category?.id).toBe('cs.AI');
      expect(category?.name).toBe('Artificial Intelligence');
    });

    it('should return subcategory for valid subcategory ID', () => {
      const category = getCategoryById('cs.LG');
      expect(category).toBeDefined();
      expect(category?.id).toBe('cs.LG');
      expect(category?.name).toBe('Machine Learning');
    });

    it('should return undefined for invalid ID', () => {
      const category = getCategoryById('invalid.category');
      expect(category).toBeUndefined();
    });
  });

  describe('getCategoryName', () => {
    it('should return name for valid category ID', () => {
      expect(getCategoryName('cs.AI')).toBe('Artificial Intelligence');
      expect(getCategoryName('cs.CV')).toBe('Computer Vision');
    });

    it('should return ID for unknown category', () => {
      expect(getCategoryName('unknown.category')).toBe('unknown.category');
    });
  });

  describe('getCategoryDescription', () => {
    it('should return description for valid category ID', () => {
      const description = getCategoryDescription('cs.AI');
      expect(description).toBeDefined();
      expect(description.length).toBeGreaterThan(0);
    });

    it('should return default message for unknown category', () => {
      expect(getCategoryDescription('unknown.category')).toBe('No description available');
    });
  });

  describe('getMainCategory', () => {
    it('should return main category for subcategory', () => {
      const mainCategory = getMainCategory('cs.LG');
      expect(mainCategory).toBeDefined();
      expect(mainCategory?.id).toBe('cs.AI'); // cs.LG is a subcategory of cs.AI
    });

    it('should return same category for main category', () => {
      const mainCategory = getMainCategory('cs.AI');
      expect(mainCategory).toBeDefined();
      expect(mainCategory?.id).toBe('cs.AI');
    });

    it('should return undefined for unknown category', () => {
      const mainCategory = getMainCategory('unknown.category');
      expect(mainCategory).toBeUndefined();
    });
  });

  describe('category structure', () => {
    it('should have valid category objects', () => {
      ARXIV_CS_CATEGORIES.forEach(category => {
        expect(category.id).toBeDefined();
        expect(category.name).toBeDefined();
        expect(category.description).toBeDefined();
        expect(typeof category.id).toBe('string');
        expect(typeof category.name).toBe('string');
        expect(typeof category.description).toBe('string');
        
        // Check subcategories if they exist
        if (category.subcategories) {
          category.subcategories.forEach(subcategory => {
            expect(subcategory.id).toBeDefined();
            expect(subcategory.name).toBeDefined();
            expect(subcategory.description).toBeDefined();
          });
        }
      });
    });
  });
});