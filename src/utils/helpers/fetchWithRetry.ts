// Retry-enabled fetch for server-side use.
// Short per-attempt timeouts prevent server-side network hangs from consuming
// the full Netlify function budget.
const getSafeUrlInfo = (url: string) => {
  try {
    const parsed = new URL(url);
    return {
      host: parsed.host,
      pathname: parsed.pathname,
    };
  } catch {
    return {
      host: 'unknown',
      pathname: 'unknown',
    };
  }
};

const logFetchRetry = (event: string, data: Record<string, unknown>) => {
  if (process.env.LAUNCHPAD_DEBUG_LOGS !== 'true') {
    return;
  }

  console.error(
    JSON.stringify({
      scope: 'launchpad-net',
      event,
      ts: new Date().toISOString(),
      ...data,
    }),
  );
};

export async function fetchWithRetry(
  url: string,
  options: RequestInit = {},
  maxRetries = 5,
): Promise<Response> {
  let lastErr: unknown;
  const safeUrl = getSafeUrlInfo(url);

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const timeoutMs = Math.min(3_000 * 1.5 ** attempt, 15_000);
    const startedAt = Date.now();

    try {
      const response = await fetch(url, {
        ...options,
        signal: AbortSignal.timeout(timeoutMs),
      });

      return response;
    } catch (err) {
      logFetchRetry('fetch-attempt-error', {
        ...safeUrl,
        attempt: attempt + 1,
        maxRetries,
        durationMs: Date.now() - startedAt,
        timeoutMs,
        error:
          err instanceof Error
            ? { name: err.name, message: err.message }
            : { message: String(err) },
      });

      if (
        err instanceof Error &&
        err.name === 'TimeoutError' &&
        attempt < maxRetries - 1
      ) {
        lastErr = err;
        continue;
      }
      throw err;
    }
  }

  throw new Error(
    `[fetchWithRetry] all ${maxRetries} attempts failed: ${url}`,
    {
      cause: lastErr,
    },
  );
}
