/* eslint-disable @typescript-eslint/no-unused-vars */
// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Mock IntersectionObserver
(window as unknown as { [key: string]: unknown }).IntersectionObserver = class IntersectionObserver {
  constructor(..._args: unknown[]) {
    // Mock constructor
  }
  
  disconnect(): void {
    // Mock disconnect - no operation needed in tests
  }
  
  observe(..._args: unknown[]): void {
    // Mock observe - no operation needed in tests
  }
  
  unobserve(..._args: unknown[]): void {
    // Mock unobserve - no operation needed in tests
  }
};

// Mock ResizeObserver
(window as unknown as { [key: string]: unknown }).ResizeObserver = class ResizeObserver {
  constructor(..._args: unknown[]) {
    // Mock constructor
  }
  
  disconnect(): void {
    // Mock disconnect - no operation needed in tests
  }
  
  observe(..._args: unknown[]): void {
    // Mock observe - no operation needed in tests
  }
  
  unobserve(..._args: unknown[]): void {
    // Mock unobserve - no operation needed in tests
  }
};

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(), // deprecated
    removeListener: jest.fn(), // deprecated
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
});

// Mock window.URL.createObjectURL
Object.defineProperty(window.URL, 'createObjectURL', {
  writable: true,
  value: jest.fn(() => 'mocked-url'),
});

// Mock window.URL.revokeObjectURL
Object.defineProperty(window.URL, 'revokeObjectURL', {
  writable: true,
  value: jest.fn(),
});

// Mock navigator.clipboard
Object.defineProperty(navigator, 'clipboard', {
  writable: true,
  value: {
    writeText: jest.fn(),
    readText: jest.fn(),
  },
});

// Mock console methods to reduce noise in tests
const originalError = console.error;
const originalWarn = console.warn;

beforeAll(() => {
  console.error = (...args: Parameters<typeof console.error>) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return;
    }
    originalError.call(console, ...args);
  };

  console.warn = (...args: Parameters<typeof console.warn>) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('Warning: componentWillReceiveProps') ||
       args[0].includes('Warning: componentWillUpdate'))
    ) {
      return;
    }
    originalWarn.call(console, ...args);
  };
});

afterAll(() => {
  console.error = originalError;
  console.warn = originalWarn;
});

// Mock fetch for API calls
(globalThis as typeof globalThis & { fetch: jest.Mock }).fetch = jest.fn();

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
(globalThis as typeof globalThis & { localStorage: typeof localStorageMock }).localStorage = localStorageMock;

// Mock sessionStorage
const sessionStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
  length: 0,
  key: jest.fn(),
};
(globalThis as typeof globalThis & { sessionStorage: typeof sessionStorageMock }).sessionStorage = sessionStorageMock;