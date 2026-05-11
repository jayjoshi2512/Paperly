import { useState, useEffect } from "react";
import { fetchApi } from "../api/client";

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
    alert("Running evaluation... Check console for results. This may take a minute.");
    try {
      const res = await fetchApi("/eval/run", { method: "POST" });
      console.log("Evaluation Results:", res);
      alert("Evaluation complete!");
      // Reload scores
      const scoresData = await fetchApi("/eval/scores");
      setScores(scoresData);
    } catch (e) {
      alert("Error: " + e.message);
    }
  };

  if (loading) return <div className="p-8 text-gray-500">Loading dashboard data...</div>;

  return (
    <div className="p-8 h-full overflow-y-auto bg-gray-50">
      <div className="flex justify-between items-center mb-8">
        <h2 className="text-2xl font-bold text-gray-800">Admin & Evaluation Dashboard</h2>
        <button onClick={runEval} className="bg-purple-600 text-white px-5 py-2.5 rounded-lg shadow-sm hover:bg-purple-700 font-medium transition-colors">
          Run RAGAS Evaluation
        </button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm font-medium mb-1">Total Queries</div>
            <div className="text-3xl font-bold text-gray-800">{stats.total_queries}</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm font-medium mb-1">Unanswered Queries</div>
            <div className="text-3xl font-bold text-red-600">{stats.unanswered_count}</div>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
            <div className="text-gray-500 text-sm font-medium mb-1">Total Documents</div>
            <div className="text-3xl font-bold text-blue-600">{stats.total_docs}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-8 mb-8">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="font-bold text-lg mb-6 text-red-700 flex items-center">
            <span className="w-2 h-2 rounded-full bg-red-500 mr-2"></span>
            Detected Knowledge Gaps
          </h3>
          {gaps.length === 0 ? <p className="text-gray-500 p-4 text-center bg-gray-50 rounded-lg">No gaps detected.</p> : (
            <ul className="space-y-4">
              {gaps.map((gap, i) => (
                <li key={i} className="border border-gray-100 rounded-lg p-4 hover:shadow-md transition-shadow">
                  <div className="font-semibold text-gray-800 mb-2">Suggested Doc: {gap.suggested_doc_title}</div>
                  <div className="text-sm text-gray-600">Based on <span className="font-bold text-gray-900">{gap.count}</span> queries. Example:</div>
                  <div className="mt-2 text-sm italic text-gray-500 bg-gray-50 p-2 rounded border-l-2 border-red-200">"{gap.representative_query}"</div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h3 className="font-bold text-lg mb-6 text-green-700 flex items-center">
            <span className="w-2 h-2 rounded-full bg-green-500 mr-2"></span>
            Recent RAGAS Scores
          </h3>
          {scores.length === 0 ? <p className="text-gray-500 p-4 text-center bg-gray-50 rounded-lg">No scores available. Run an evaluation.</p> : (
            <div className="max-h-96 overflow-y-auto pr-2">
              <ul className="space-y-3">
                {scores.slice(0, 10).map((score) => (
                  <li key={score.query_id} className="border border-gray-100 p-4 rounded-lg hover:bg-gray-50 transition-colors text-sm">
                    <div className="font-medium text-gray-800 mb-2 truncate" title={score.query_text}>{score.query_text}</div>
                    <div className="flex space-x-4 text-gray-600">
                      <div className="flex flex-col">
                        <span className="text-xs text-gray-400 uppercase tracking-wider">Faithfulness</span>
                        <span className={`font-semibold ${score.faithfulness > 0.8 ? 'text-green-600' : score.faithfulness > 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {score.faithfulness?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                      <div className="flex flex-col">
                        <span className="text-xs text-gray-400 uppercase tracking-wider">Relevancy</span>
                        <span className={`font-semibold ${score.relevancy > 0.8 ? 'text-green-600' : score.relevancy > 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                          {score.relevancy?.toFixed(2) || 'N/A'}
                        </span>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
