// Cloudflare Pages Function: 中间件
// - 拦截 /example/* 返回 404

export async function onRequest(context) {
  const url = new URL(context.request.url);

  if (url.pathname.startsWith('/example/')) {
    return new Response('Not Found', {
      status: 404,
      headers: {
        'X-Robots-Tag': 'noindex, nofollow',
        'Cache-Control': 'no-store',
      },
    });
  }

  return context.next();
}