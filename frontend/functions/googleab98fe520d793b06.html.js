// Google Search Console site-verification file. Served via a Pages Function
// (not a static asset) because Cloudflare Pages 308-redirects .html static
// assets to their extensionless URL, which breaks Google's verifier — it
// requires the exact .html URL to return 200 directly.
export async function onRequestGet() {
  return new Response("google-site-verification: googleab98fe520d793b06.html", {
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });
}
