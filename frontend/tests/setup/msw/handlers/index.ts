/**
 * MSW handlers index.
 *
 * Combines all API handlers for testing.
 */

import { authHandlers } from './auth.handlers';
import { casesHandlers } from './cases.handlers';
import { usersHandlers } from './users.handlers';
import { analyticsHandlers } from './analytics.handlers';

export const handlers = [
  ...authHandlers,
  ...casesHandlers,
  ...usersHandlers,
  ...analyticsHandlers,
];
