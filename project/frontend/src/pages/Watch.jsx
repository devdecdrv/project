import { useEffect, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import Hls from "hls.js";
import { api, proxyUrl } from "../api";
import styles from "./Watch.module.css";

export default function Watch() {
  const { videoId } = useParams();
  const videoRef = useRef(null);
  const hlsRef   = useRef(null);

  const [video,   setVideo]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);

  useEffect(() => {
    api.video(videoId)
      .then(setVideo)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [videoId]);

  useEffect(() => {
    if (!video?.pw_url || !videoRef.current) return;

    const src = proxyUrl(video.pw_url);
    const el  = videoRef.current;

    if (video.pw_url.includes(".m3u8")) {
      if (Hls.isSupported()) {
        if (hlsRef.current) hlsRef.current.destroy();
        const hls = new Hls({ enableWorker: true });
        hls.loadSource(src);
        hls.attachMedia(el);
        hls.on(Hls.Events.MANIFEST_PARSED, () => el.play().catch(() => {}));
        hlsRef.current = hls;
      } else if (el.canPlayType("application/vnd.apple.mpegurl")) {
        // Safari native HLS
        el.src = src;
        el.play().catch(() => {});
      }
    } else {
      // Direct mp4 / stream
      el.src = src;
      el.play().catch(() => {});
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [video]);

  if (loading) return <div className={styles.center}>Loading...</div>;
  if (error)   return <div className={styles.center} style={{color:"var(--danger)"}}>{error}</div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link
          to={video?.batch_id ? `/batch/${video.batch_id}` : "/"}
          className={styles.back}
        >
          ← {video?.batch_name || "Back"}
        </Link>
      </header>

      <div className={styles.layout}>
        {/* Player */}
        <div className={styles.playerWrap}>
          <video
            ref={videoRef}
            className={styles.player}
            controls
            playsInline
          />
        </div>

        {/* Info */}
        <div className={styles.info}>
          <h1 className={styles.title}>{video?.title}</h1>
          <div className={styles.meta}>
            {video?.topic_name  && <span>{video.topic_name}</span>}
            {video?.batch_name  && <span>{video.batch_name}</span>}
          </div>
          {!video?.pw_url && (
            <p className={styles.warn}>
              Stream URL not scraped yet — re-run scraper for this video.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
