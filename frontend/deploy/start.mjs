if ((process.env.NEXTAUTH_SECRET ?? '').length < 32) {
  throw new Error('NEXTAUTH_SECRET must contain at least 32 characters.');
}

await import('./server.js');
