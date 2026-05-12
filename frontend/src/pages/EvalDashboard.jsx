import { useState, useEffect } from "react";
import { fetchApi } from "../api/client";
import { Play } from "lucide-react";
import styles from "./EvalDashboard.module.css";

function scoreClass(val) {
  if (val == null) return "";
  if (val > 0.8) return styles.good;
  if (val > 0.5) return styles.ok;
  return styles.bad;
}

export default function EvalDashboard() {
  const [gaps, setGaps] = useState([]);
  const [scores, setScores] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [gapsData, scoresData, statsData] = await Promise.all([
          fetchApi("/eval/gaps"),
          fetchApi("/eval/scores"),
          fetchApi("/admin/stats"),
        ]);
        setGaps(gapsData);
        setScores(scoresData);
        setStats(statsData);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const runEval = async () => {
    alert("Running evaluation… This may take a minute.");
    try {
      await fetchApi("/eval/run", { method: "POST" });
      alert("Evaluation complete!");
      const scoresData = await fetchApi("/eval/scores");
      setScores(scoresData);
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  if (loading) {
    return <div className={styles.loading}>Loading dashboard…</div>;
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <div>
          <h2 className={styles.title}>Insights & Performance</h2>
          <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-sm)", marginTop: "4px" }}>
            This dashboard helps you identify missing knowledge in your documents and tracks the AI's answer accuracy.
          </p>
        </div>
        <button onClick={runEval} className={styles.evalBtn}>
          <Play size={16} />
          <span>Run Diagnostics</span>
        </button>
      </div>

      {stats && (
        <div className={styles.statsGrid}>
          <div className={styles.statCard}>
            <span className={styles.statLabel}>Total Queries</span>
            <span className={`${styles.statValue} ${styles.primary}`}>{stats.total_queries}</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statLabel}>Unanswered</span>
            <span className={`${styles.statValue} ${styles.danger}`}>{stats.unanswered_count}</span>
          </div>
          <div className={styles.statCard}>
            <span className={styles.statLabel}>Documents</span>
            <span className={`${styles.statValue} ${styles.accent}`}>{stats.total_docs}</span>
          </div>
        </div>
      )}

      <div className={styles.panels}>
        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className={`${styles.panelDot} ${styles.red}`} />
            <h3 className={styles.panelTitle}>Knowledge Gaps</h3>
          </div>
          {gaps.length === 0 ? (
            <p className={styles.emptyMsg}>No gaps detected.</p>
          ) : (
            <ul className={styles.list}>
              {gaps.map((gap, i) => (
                <li key={i} className={styles.listItem}>
                  <div className={styles.gapTitle}>{gap.suggested_doc_title}</div>
                  <div className={styles.gapMeta}>
                    <strong>{gap.count}</strong> related queries
                  </div>
                  <div className={styles.gapQuote}>"{gap.representative_query}"</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHeader}>
            <div className={`${styles.panelDot} ${styles.green}`} />
            <h3 className={styles.panelTitle}>AI Accuracy Scores</h3>
          </div>
          {scores.length === 0 ? (
            <p className={styles.emptyMsg}>No scores yet. Run an evaluation.</p>
          ) : (
            <ul className={styles.list}>
              {scores.slice(0, 10).map((score) => (
                <li key={score.query_id} className={styles.listItem}>
                  <div className={styles.scoreQuery} title={score.query_text}>
                    {score.query_text}
                  </div>
                  <div className={styles.scoreMetrics}>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Faithfulness</span>
                      <span className={`${styles.metricValue} ${scoreClass(score.faithfulness)}`}>
                        {score.faithfulness?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                    <div className={styles.metric}>
                      <span className={styles.metricLabel}>Relevancy</span>
                      <span className={`${styles.metricValue} ${scoreClass(score.relevancy)}`}>
                        {score.relevancy?.toFixed(2) || "N/A"}
                      </span>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
