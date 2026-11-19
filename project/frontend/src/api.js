const API  = import.meta.env.VITE_API_URL   || "http://localhost:8000";
const PROXY = import.meta.env.VITE_PROXY_URL || "http://localhost:8001";

async function get(path) {
  const r = await fetch(`${API}${path}`);
  if (!r.ok) throw new Error(`API ${r.status}: ${path}`);
  return r.json();
}

export const api = {
  batches:      ()         => get("/batches/"),
  batch:        (id)       => get(`/batches/${id}`),
  topics:       (batchId)  => get(`/batches/${batchId}/topics`),
  videos:       (params)   => get(`/videos/?${new URLSearchParams(params)}`),
  video:        (id)       => get(`/videos/${id}`),
};

/** Build a proxied stream URL from a PW stream URL. */
export function proxyUrl(pwUrl) {
  if (!pwUrl) return null;
  const encoded = encodeURIComponent(pwUrl);
  if (pwUrl.includes(".m3u8")) {
    return `${PROXY}/m3u8?url=${encoded}`;
  }
  return `${PROXY}/stream?url=${encoded}`;
}
