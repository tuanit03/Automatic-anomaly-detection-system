// Mock the EventSource browser API for tests
global.EventSource = class EventSource {
  constructor() {
    this.addEventListener = jest.fn();
    this.removeEventListener = jest.fn();
    this.close = jest.fn();
  }
};

// Mock fetch
global.fetch = jest.fn(() => 
  Promise.resolve({
    json: () => Promise.resolve({}),
    text: () => Promise.resolve(''),
    ok: true
  })
);

// Mock other browser APIs as needed
if (typeof window !== 'undefined') {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: jest.fn().mockImplementation(query => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    })),
  });
}