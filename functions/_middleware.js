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

  // 2026-07-06 fix removed: /archive 物理文件 archive/index.html 已存在,Cloudflare Pages
  // 优先 serve 物理文件 > SPA fallback,不再需要 middleware 拦截

  // 其他请求放行
  return context.next();
}