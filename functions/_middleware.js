// Cloudflare Pages Function: 拦截 /example/* 返回 404
// 部署到 functions/_middleware.ts (或 functions/example/_middleware.ts)

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
  // 其他请求放行
  return context.next();
}