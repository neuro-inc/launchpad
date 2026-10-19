export const as = <T = any>(source: any, defaultSource: any): T =>
  (source ?? defaultSource) as T;

/**
 * As any object
 */
as.o = <T = any>(source: any): T => as(source, {});

/**
 * As any array
 */
as.a = <T = any>(source: any): T => as(source, []);
