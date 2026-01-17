/**
 * MSW (Mock Service Worker) server setup for tests.
 *
 * Source: https://mswjs.io/docs/getting-started
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Create the server with default handlers
export const server = setupServer(...handlers);
