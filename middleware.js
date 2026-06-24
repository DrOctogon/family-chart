// Vercel Edge Middleware — HTTP Basic Auth for the whole site.
// No `config.matcher` export => default catch-all (^/.*$), so this guards
// index.html, assets, and /gramps.json alike.
//
// Set SITE_PASSWORD in Vercel: Settings -> Environment Variables, then redeploy.
// Login user is "family"; password is SITE_PASSWORD.
export default function middleware(req) {
  const password = process.env.SITE_PASSWORD
  const auth = req.headers.get('authorization')
  const expected = password ? 'Basic ' + btoa('family:' + password) : null

  // Fail closed: if no password is configured, deny everything.
  if (!expected || auth !== expected) {
    return new Response('Authentication required', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="Krebs Family Tree"' },
    })
  }
  // Authenticated: return nothing so the request continues to the static site.
}
