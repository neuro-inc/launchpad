import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, readFile, rm, copyFile, writeFile } from 'node:fs/promises';
import { request } from 'node:http';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { test } from 'node:test';

test('the container accepts large authentication headers and rejects oversized headers', { timeout: 10000 }, async (t) => {
  const directory = await mkdtemp(join(tmpdir(), 'launchpad-frontend-'));
  t.after(() => rm(directory, { recursive: true, force: true }));
  await copyFile(new URL('./start.mjs', import.meta.url), join(directory, 'start.mjs'));
  await writeFile(join(directory, 'server.js'), `
    const { createServer } = require('node:http');
    const server = createServer((req, res) => res.end('{}'));
    server.listen(0, '127.0.0.1', () => console.log(server.address().port));
  `);
  const dockerfile = await readFile(new URL('../Dockerfile', import.meta.url), 'utf8');
  const command = JSON.parse(dockerfile.match(/^CMD (.+)$/m)[1]);
  assert.equal(command[0], 'node');
  const child = spawn(process.execPath, command.slice(1), {
    cwd: directory,
    env: { ...process.env, NEXTAUTH_SECRET: 'test-session-secret'.repeat(2) },
    stdio: ['ignore', 'pipe', 'inherit'],
  });
  t.after(async () => {
    if (child.exitCode === null && child.signalCode === null) {
      child.kill();
      await once(child, 'exit');
    }
  });
  const [output] = await Promise.race([
    once(child.stdout, 'data'),
    once(child, 'exit').then(([code]) => {
      throw new Error(`The frontend exited before listening: ${code}`);
    }),
  ]);
  const port = Number(output.toString().trim());
  assert.ok(port > 0);

  async function sessionStatus(cookieBytes) {
    return new Promise((resolve, reject) => {
      const req = request({
        hostname: '127.0.0.1', port, path: '/api/auth/session',
        headers: { Cookie: `diagnostic=${'a'.repeat(cookieBytes)}` },
      }, (res) => {
        res.resume();
        res.on('end', () => resolve(res.statusCode));
      });
      req.on('error', reject);
      req.end();
    });
  }

  assert.equal(await sessionStatus(32 * 1024), 200);
  assert.equal(await sessionStatus(80 * 1024), 431);
});
