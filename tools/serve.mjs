// Minimal dependency-free static server for the browser port (web/).
// ES modules need HTTP, not file://; this is what F5 launches (.vscode/launch.json).
//
//   node tools/serve.mjs [--root web] [--port 8000]
//
// Prints "listening on http://localhost:<port>/" once bound — VS Code's
// serverReadyAction matches that line and opens the debug browser on it.

import { createServer } from 'node:http'
import { createReadStream } from 'node:fs'
import { stat } from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { join, normalize, extname, resolve, sep } from 'node:path'

const argv = process.argv.slice(2)
const arg = (name, fallback) => {
  const i = argv.indexOf(`--${name}`)
  return i >= 0 && argv[i + 1] !== undefined ? argv[i + 1] : fallback
}

const repoRoot = resolve(fileURLToPath(new URL('..', import.meta.url)))
const root = resolve(repoRoot, arg('root', 'web'))
const firstPort = Number(arg('port', 8000))
const maxTries = 10

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.gif': 'image/gif',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon',
  '.wasm': 'application/wasm',
  '.txt': 'text/plain; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8',
  '.rom': 'application/octet-stream',
  '.bin': 'application/octet-stream',
}

const send = (res, code, body) => {
  res.writeHead(code, { 'content-type': 'text/plain; charset=utf-8' })
  res.end(body)
}

const server = createServer(async (req, res) => {
  let pathname
  try {
    pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname)
  } catch {
    return send(res, 400, '400 bad request')
  }
  if (pathname.endsWith('/')) pathname += 'index.html'

  // Resolve inside root only — normalize kills ../ traversal.
  const filePath = join(root, normalize(pathname).replace(/^(\.\.[/\\])+/, ''))
  if (filePath !== root && !filePath.startsWith(root + sep)) {
    return send(res, 403, '403 forbidden')
  }

  let info
  try {
    info = await stat(filePath)
  } catch {
    return send(res, 404, `404 ${pathname}`)
  }
  if (info.isDirectory()) {
    res.writeHead(302, { location: pathname + '/' })
    return res.end()
  }

  res.writeHead(200, {
    'content-type': MIME[extname(filePath).toLowerCase()] ?? 'application/octet-stream',
    'content-length': info.size,
    // Always re-fetch: the port's JS and generated assets change under you.
    'cache-control': 'no-store',
  })
  createReadStream(filePath).pipe(res)
})

let port = firstPort
server.on('error', (err) => {
  if (err.code === 'EADDRINUSE' && port < firstPort + maxTries) {
    server.listen(++port, '127.0.0.1')
    return
  }
  console.error(err.message)
  process.exit(1)
})
server.on('listening', () => {
  console.log(`serving ${root}`)
  console.log(`listening on http://localhost:${port}/`)
})
server.listen(port, '127.0.0.1')

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => server.close(() => process.exit(0)))
}
