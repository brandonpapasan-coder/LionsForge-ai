# Frontend Testing

The frontend uses Vitest with jsdom and Testing Library.

## Commands

- `npm test` runs the suite once.
- `npm run test:watch` runs tests interactively.
- `npm run test:coverage` generates text, JSON, and HTML coverage reports.

Frontend CI installs dependencies, runs the test suite, type-checks the project, builds the Next.js application, and builds the production container.

Tests should cover successful, loading, empty, unauthorized, not-found, and failed API states where those states exist. Assertions must not rely on color alone for status meaning.
