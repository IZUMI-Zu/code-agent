import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ThemeToggle from '../ThemeToggle';

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value.toString();
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

describe('ThemeToggle', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
    
    // Reset document class
    document.documentElement.classList.remove('dark');
  });

  it('renders the theme toggle button', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button', { name: /switch to (light|dark) mode/i });
    expect(button).toBeInTheDocument();
  });

  it('shows moon icon when in light mode', () => {
    // Mock light mode
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: false,
      })),
    });
    
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    // Check for moon icon (dark mode icon)
    expect(button.innerHTML).toContain('M20.354');
  });

  it('shows sun icon when in dark mode', () => {
    // Mock dark mode from localStorage
    localStorageMock.getItem.mockReturnValue('dark');
    
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    // Check for sun icon (light mode icon)
    expect(button.innerHTML).toContain('M12 3v1m0 16v1m9-9h-1');
  });

  it('toggles theme when clicked', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    
    // Initial state should be light mode (no dark class)
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    
    // Click to toggle to dark mode
    fireEvent.click(button);
    
    // Should add dark class
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    
    // Should save to localStorage
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
  });

  it('uses localStorage theme preference', () => {
    // Set dark mode in localStorage
    localStorageMock.getItem.mockReturnValue('dark');
    
    render(<ThemeToggle />);
    
    // Should have dark class from localStorage
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('uses system preference when no localStorage setting', () => {
    // Mock system dark mode preference
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation(() => ({
        matches: true, // System prefers dark mode
      })),
    });
    
    render(<ThemeToggle />);
    
    // Should have dark class from system preference
    expect(document.documentElement.classList.contains('dark')).toBe(true);
  });

  it('toggles between light and dark mode', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    
    // Start in light mode
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    
    // First click: light -> dark
    fireEvent.click(button);
    expect(document.documentElement.classList.contains('dark')).toBe(true);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'dark');
    
    // Second click: dark -> light
    fireEvent.click(button);
    expect(document.documentElement.classList.contains('dark')).toBe(false);
    expect(localStorageMock.setItem).toHaveBeenCalledWith('theme', 'light');
  });

  it('has proper accessibility attributes', () => {
    render(<ThemeToggle />);
    const button = screen.getByRole('button');
    
    expect(button).toHaveAttribute('aria-label');
    const ariaLabel = button.getAttribute('aria-label');
    expect(ariaLabel).toMatch(/switch to (light|dark) mode/i);
  });
});