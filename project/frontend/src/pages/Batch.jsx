import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import styles from "./Batch.module.css";

function formatDuration(secs) {
  if (!secs) return "";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m ${s}s`;
}

export default function Batch() {
  const { batchId } = useParams();

  const [batch,     setBatch]     = useState(null);
  const [topics,    setTopics]    = useState([]);
  const [videos,    setVideos]    = useState([]);
  const [activeTopic, setActiveTopic] = useState(null);
  const [loading,   setLoading]   = useState(true);

  // Load batch + topics on mount
  useEffect(() => {
    Promise.all([api.batch(batchId), api.topics(batchId)])
      .then(([b, t]) => {
        setBatch(b);
        setTopics(t);
        if (t.length > 0) setActiveTopic(t[0].id);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [batchId]);

  // Load videos when active topic changes
  useEffect(() => {
    if (!activeTopic) return;
    api.videos({ batch_id: batchId, topic_id: activeTopic, limit: 100 })
      .then(setVideos)
      .catch(console.error);
  }, [activeTopic, batchId]);

  if (loading) return <div className={styles.loading}>Loading...</div>;

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <Link to="/" className={styles.back}>← Back</Link>
        <span className={styles.batchName}>{batch?.name}</span>
      </header>

      <div className={styles.layout}>
        {/* Topics sidebar */}
        <aside className={styles.sidebar}>
          <div className={styles.sidebarTitle}>Topics</div>
          {topics.map((t) => (
            <button
              key={t.id}
              className={`${styles.topicBtn} ${activeTopic === t.id ? styles.active : ""}`}
              onClick={() => setActiveTopic(t.id)}
            >
              {t.name}
            </button>
          ))}
        </aside>

        {/* Video list */}
        <main className={styles.content}>
          {videos.length === 0 && (
            <p className={styles.muted}>No videos in this topic.</p>
          )}
          <div className={styles.videoList}>
            {videos.map((v) => (
              <Link key={v.id} to={`/watch/${v.id}`} className={styles.videoRow}>
                <div className={styles.thumb}>
                  {v.thumbnail_url
                    ? <img src={v.thumbnail_url} alt="" loading="lazy" />
                    : <div className={styles.thumbPlaceholder} />
                  }
                </div>
                <div className={styles.videoInfo}>
                  <div className={styles.videoTitle}>{v.title}</div>
                  <div className={styles.videoMeta}>
                    {v.topic_name && <span>{v.topic_name}</span>}
                    {v.duration_secs && <span>{formatDuration(v.duration_secs)}</span>}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </main>
      </div>
    </div>
  );
}
