import { useState, useEffect } from "react";
import { fetchApi, API_URL, getAuthToken } from "../api/client";
import { Play, ThumbsUp, ThumbsDown, Star, Layers, Download, Activity } from "lucide-react";
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
  const [feedbackStats, setFeedbackStats] = useState(null);
  const [chunkingData, setChunkingData] = useState(null);
  const [healthData, setHealthData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [gapsData, scoresData, statsData, fbData, chunkData, healthResult] = await Promise.all([
          fetchApi("/eval/gaps"),
          fetchApi("/eval/scores"),
          fetchApi("/admin/stats"),
          fetchApi("/admin/feedback-stats").catch(() => null),
          fetchApi("/admin/chunking-benchmark").catch(() => null),
          fetchApi("/admin/health").catch(() => null),
        ]);
        setGaps(gapsData);
        setScores(scoresData);
        setStats(statsData);
        setFeedbackStats(fbData);
        setChunkingData(chunkData);
        setHealthData(healthResult);
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

  const exportQA = async () => {
    try {
      const response = await fetch(`${API_URL}/admin/export/qa`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
      });
      if (!response.ok) throw new Error("Export failed");
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "paperly_qa_export.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      alert("Export failed: " + e.message);
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
        <div className={styles.headerBtns}>
          <button onClick={exportQA} className={styles.exportBtn}>
            <Download size={15} />
            <span>Export Q&amp;A</span>
          </button>
          <button onClick={runEval} className={styles.evalBtn}>
            <Play size={16} />
            <span>Run Diagnostics</span>
          </button>
        </div>
      </div>

      {/* ── System Health Widget ── */}
      {healthData && (
        <div className={styles.healthCard}>
          <div className={styles.feedbackHeader}>
            <Activity size={14} style={{ color: healthData.overall === "healthy" ? "#4ade80" : "#f87171" }} />
            <span>System Health</span>
            <span className={healthData.overall === "healthy" ? styles.evalBadgeGood : styles.evalBadgeDanger}>
              {healthData.overall === "healthy" ? "✅ All systems operational" : "⚠️ Degraded"}
            </span>
          </div>
          <div className={styles.healthGrid}>
            {[
              { label: "Database",   key: "database",      extra: healthData.database?.latency_ms ? `${healthData.database.latency_ms} ms` : null },
              { label: "Qdrant",     key: "qdrant",        extra: null },
              { label: "Cache",      key: "semantic_cache", extra: healthData.semantic_cache?.total_entries != null ? `${healthData.semantic_cache.total_entries} entries` : null },
              { label: "Uptime",     key: null,            extra: healthData.uptime_seconds != null ? `${Math.floor(healthData.uptime_seconds / 60)}m` : "—" },
              { label: "Today’s Queries", key: null,      extra: healthData.queries_today != null ? String(healthData.queries_today) : "—" },
            ].map(({ label, key, extra }) => {
              const isOk = key ? healthData[key]?.status === "ok" : true;
              return (
                <div key={label} className={styles.healthItem}>
                  <span className={isOk ? styles.healthDotGreen : styles.healthDotRed} />
                  <span className={styles.healthLabel}>{label}</span>
                  {extra && <span className={styles.healthExtra}>{extra}</span>}
                </div>
              );
            })}
          </div>
        </div>
      )}

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

      {/* ── Feedback Stats Card ── */}
      {feedbackStats && (
        <div className={styles.feedbackCard}>
          <div className={styles.feedbackHeader}>
            <Star size={14} style={{ color: "var(--color-accent)" }} />
            <span>Answer Feedback</span>
            {feedbackStats.ground_truth_count > 0 ? (
              <span className={styles.evalBadgeGood}>✓ Using real ground truth</span>
            ) : (
              <span className={styles.evalBadgeWarn}>⚠ Rate answers to improve RAGAS eval</span>
            )}
          </div>
          <div className={styles.feedbackMetrics}>
            <div className={styles.feedbackMetric}>
              <ThumbsUp size={13} style={{ color: "#4ade80" }} />
              <span>{feedbackStats.positive_count} helpful</span>
            </div>
            <div className={styles.feedbackMetric}>
              <ThumbsDown size={13} style={{ color: "#f87171" }} />
              <span>{feedbackStats.negative_count} not helpful</span>
            </div>
            <div className={styles.feedbackMetric}>
              <span style={{ fontWeight: 600, color: "var(--color-accent)" }}>
                {feedbackStats.feedback_given}
              </span>
              <span>/ {feedbackStats.total_queries} rated</span>
            </div>
            <div className={styles.feedbackMetric}>
              <span style={{ fontWeight: 600 }}>
                {feedbackStats.ground_truth_count}
              </span>
              <span>ground truths collected</span>
            </div>
          </div>
        </div>
      )}

      {/* ── Chunking Strategy Benchmark ── */}
      {chunkingData && chunkingData.strategies && (
        <div className={styles.benchmarkCard}>
          <div className={styles.feedbackHeader}>
            <Layers size={14} style={{ color: "var(--color-accent)" }} />
            <span>Chunking Strategy Benchmark</span>
          </div>
          <table className={styles.benchTable}>
            <thead>
              <tr>
                <th>Strategy</th>
                <th>Docs</th>
                <th>Avg Chunks</th>
                <th>Avg Latency</th>
                <th>Cache Hit Rate</th>
              </tr>
            </thead>
            <tbody>
              {chunkingData.strategies.map((s) => (
                <tr key={s.strategy}>
                  <td><span className={styles.strategyBadge}>{s.strategy}</span></td>
                  <td>{s.doc_count}</td>
                  <td>{s.avg_chunks}</td>
                  <td>{s.avg_latency_ms > 0 ? `${s.avg_latency_ms} ms` : "—"}</td>
                  <td>
                    <span className={s.cache_hit_rate > 0.2 ? styles.good : styles.ok}>
                      {(s.cache_hit_rate * 100).toFixed(1)}%
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
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
