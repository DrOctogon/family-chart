// Vercel Edge Middleware — HTTP Basic Auth for the whole site.
// No `config.matcher` export => default catch-all (^/.*$), so this guards
// index.html, assets, and /gramps.json alike.
//
// Toggle protection with AUTH_ENABLED:
//   AUTH_ENABLED=true  -> site requires the password
//   AUTH_ENABLED unset/anything-else -> site is public (no prompt)
// The password itself stays in SITE_PASSWORD, so you can flip protection
// on/off without re-entering it.
//
// Set both in Vercel: Settings -> Environment Variables, then redeploy.
// Login user is "family"; password is SITE_PASSWORD.
export default function middleware(req) {
  // Protection off -> let every request through.
  if (process.env.AUTH_ENABLED !== 'true') return

  const password = process.env.SITE_PASSWORD
  const auth = req.headers.get('authorization')
  const expected = password ? 'Basic ' + btoa('family:' + password) : null

  // Fail closed: protection on but no password configured -> deny everything.
  if (!expected || auth !== expected) {
    return new Response('Authentication required', {
      status: 401,
      headers: { 'WWW-Authenticate': 'Basic realm="Krebs Family Tree"' },
    })
  }
  // Authenticated: return nothing so the request continues to the static site.
}
