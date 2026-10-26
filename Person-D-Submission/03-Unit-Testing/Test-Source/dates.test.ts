import { expect, it } from 'vitest';
import { todayInZone } from '../../src/frontend/utilities/dates';

it('uses the account calendar date instead of the UTC or browser date', () => {
  const clock = new Date('2026-10-26T01:00:00Z');
  expect(todayInZone('America/New_York', clock)).toBe('2026-10-25');
  expect(todayInZone('Asia/Tokyo', clock)).toBe('2026-10-26');
});
