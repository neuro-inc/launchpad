export const safeError = (error: unknown) => {
  if (error instanceof Error) {
    return {
      name: error.name,
      message: error.message,
    };
  }

  return {
    message: String(error),
  };
};

export const safeUrlParts = (url: string) => {
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

export const logLaunchpadNet = (
  event: string,
  data: Record<string, unknown> = {},
) => {
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
