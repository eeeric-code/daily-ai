// Cloudflare Pages Function: 中间件
// - 拦截 /example/* 返回 404
// - 2026-07-06 fix: 拦截 /archive (无尾斜杠) 直接 serve archive.html,避免 Cloudflare Pages 308 → SPA fallback → portal 首页的问题

export async function onRequest(context) {
  const url = new URL(context.request.url);

  // 拦截 /example/* 路径
  if (url.pathname.startsWith('/example/')) {
    return new Response('Not Found', {
      status: 404,
      headers: {
        'X-Robots-Tag': 'noindex, nofollow',
        'Cache-Control': 'no-store',
      },
    });
  }

  // 拦截 /archive (Cloudflare Pages 308 trailing-slash redirect 会把这个路径 fallback 到 /index.html)
  // 直接 serve /archive.html 内容
  if (url.pathname === '/archive' || url.pathname === '/archive/') {
    const archiveReq = await context.env.ASSETS
      ? context.env.ASSETS.fetch(new URL('/archive.html', url.origin))
      : fetch(new URL('/archive.html', url.origin));
    const body = await archiveReq.text();
    return new Response(body, {
      status: 200,
      headers: {
        'Content-Type': 'text/html; charset=utf-8',
        'Cache-Control': 'public, max-age=300',
      },
    });
  }

  // 其他请求放行
  return context.next();
}