export default {
  async fetch(request, env) {
    if (!env.ORIGIN_AUTH_TOKEN) {
      return Response.json(
        { detail: "API gateway configuration is unavailable" },
        { status: 503, headers: { "Cache-Control": "no-store" } },
      );
    }

    const incomingUrl = new URL(request.url);
    const originUrl = new URL(env.ORIGIN_URL);
    originUrl.pathname = incomingUrl.pathname;
    originUrl.search = incomingUrl.search;

    const outboundRequest = new Request(originUrl.toString(), request);
    outboundRequest.headers.set("X-Forwarded-Host", incomingUrl.host);
    outboundRequest.headers.set("X-Forwarded-Proto", "https");
    outboundRequest.headers.set("X-Fintrack-Origin-Auth", env.ORIGIN_AUTH_TOKEN);

    try {
      const originResponse = await fetch(outboundRequest, { redirect: "manual" });
      const response = new Response(originResponse.body, originResponse);
      response.headers.set("Strict-Transport-Security", "max-age=31536000");
      response.headers.set("X-Content-Type-Options", "nosniff");
      return response;
    } catch (error) {
      console.error(JSON.stringify({
        event: "railway_origin_fetch_failed",
        errorType: error instanceof Error ? error.name : "UnknownError",
      }));
      return Response.json(
        { detail: "API origin is temporarily unavailable" },
        { status: 502, headers: { "Cache-Control": "no-store" } },
      );
    }
  },
};
