import { isArray } from './typeof';

export const ensureArray = <T = string>(input: T | T[]): T[] =>
  isArray(input) ? (input as T[]) : [input as T];
