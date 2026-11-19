import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import styles from "./Home.module.css";

export default function Home() {
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);

  useEffect(() => {
    api.batches()
      .then(setBatches)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className={styles.page}>
      <header className={styles.header}>
        <span className={styles.logo}>pw<span>mirror</span></span>
      </header>

      <main className={styles.main}>
        <h1 className={styles.title}>Courses</h1>

        {loading && <p className={styles.muted}>Loading...</p>}
        {error   && <p className={styles.error}>{error}</p>}

        <div className={styles.grid}>
          {batches.map((b) => (
            <Link key={b.id} to={`/batch/${b.id}`} className={styles.card}>
              <div className={styles.cardTop}>
                <span className={styles.subject}>{b.subject || "General"}</span>
              </div>
              <div className={styles.cardName}>{b.name}</div>
            </Link>
          ))}
        </div>
      </main>
    </div>
  );
}
