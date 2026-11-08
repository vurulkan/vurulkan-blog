import http from 'node:http';
import fs from 'node:fs/promises';
import path from 'node:path';

const root = path.resolve('_site');
const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'application/javascript', '.json': 'application/json', '.woff2': 'font/woff2', '.png': 'image/png', '.svg': 'image/svg+xml', '.txt': 'text/plain' };
http.createServer(async (request, response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    let file = path.resolve(root, '.' + pathname);
    if (!file.startsWith(root + path.sep) && file !== root) throw new Error('Invalid path');
    if (pathname === '/__social-preview/') file = path.resolve('tools/site-review/social-preview.html');
    else if ((await fs.stat(file).catch(() => null))?.isDirectory()) {
      if (!pathname.endsWith('/')) { response.writeHead(301, { Location: pathname + '/' }).end(); return; }
      file = path.join(file, 'index.html');
    }
    let data = await fs.readFile(file).catch(() => null);
    if (!data) { response.statusCode = 404; file = path.join(root, '404.html'); data = await fs.readFile(file); }
    response.setHeader('Content-Type', types[path.extname(file)] || 'application/octet-stream');
    response.end(data);
  } catch { response.writeHead(400).end('Bad request'); }
}).listen(4173, '127.0.0.1', () => console.log('Review server: http://127.0.0.1:4173'));
