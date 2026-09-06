import { useEffect, useState, useCallback } from "react";
import { Bot, Play, Square, RefreshCw } from "lucide-react";
import api from "../lib/api";
import type { AgentStatus, AgentRun } from "../lib/types";

export default function AgentPage() {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = useCallback(async () => {
    try {
      const [statusResp, runsResp] = await Promise.all([
        api.get<AgentStatus>("/agent/status"),
        api.get<AgentRun[]>("/agent/runs"),
      ]);
      setStatus(statusResp.data);
      setRuns(runsResp.data);
    } catch (err) {
      console.error("Agent data fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const handleStart = async () => {
    setActionLoading(true);
    try {
      await api.post("/agent/start");
      await fetchData();
    } catch (err) {
      console.error("Start error:", err);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStop = async () => {
    setActionLoading(true);
    try {
      await api.post("/agent/stop");
      await fetchData();
    } catch (err) {
      console.error("Stop error:", err);
    } finally {
      setActionLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen" style={{ minHeight: "50vh" }}>
        <div className="loading-spinner" />
      </div>
    );
  }

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>
          <Bot
            size={24}
            style={{ display: "inline", marginRight: "0.5rem" }}
          />
          Agent Control
        </h1>
        <p>Monitor and control the market scanning agent</p>
      </div>

      {/* Status Card */}
      <div
        className="glass-card"
        style={{
          padding: "2rem",
          marginBottom: "2rem",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "1.5rem",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.75rem",
              marginBottom: "0.75rem",
            }}
          >
            <span
              className={`status-dot ${status?.is_running ? "running" : "stopped"}`}
              style={{ width: 14, height: 14 }}
            />
            <span style={{ fontSize: "1.25rem", fontWeight: 700 }}>
              {status?.is_running ? "Agent Running" : "Agent Stopped"}
            </span>
          </div>
          <div
            style={{
              display: "flex",
              gap: "2rem",
              color: "var(--text-secondary)",
              fontSize: "0.85rem",
            }}
          >
            <span>Total runs: {status?.total_runs ?? 0}</span>
            <span>Active users: {status?.active_users ?? 0}</span>
            {status?.last_run_at && (
              <span>
                Last run: {new Date(status.last_run_at).toLocaleString()}
              </span>
            )}
            {status?.next_run_at && (
              <span>
                Next run: {new Date(status.next_run_at).toLocaleString()}
              </span>
            )}
          </div>
        </div>

        <div style={{ display: "flex", gap: "0.75rem" }}>
          {status?.is_running ? (
            <button
              className="btn btn-danger"
              onClick={handleStop}
              disabled={actionLoading}
            >
              <Square size={16} />
              {actionLoading ? "Stopping…" : "Stop Agent"}
            </button>
          ) : (
            <button
              className="btn btn-success"
              onClick={handleStart}
              disabled={actionLoading}
            >
              <Play size={16} />
              {actionLoading ? "Starting…" : "Start Agent"}
            </button>
          )}
          <button
            className="btn btn-secondary"
            onClick={fetchData}
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      {/* Run History */}
      <h2 className="section-title">Run History</h2>
      {runs.length > 0 ? (
        <div className="glass-card" style={{ overflow: "auto" }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Status</th>
                <th>Started</th>
                <th>Duration</th>
                <th>Sources</th>
                <th>Items</th>
                <th>Alerts</th>
                <th>Errors</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const duration =
                  run.started_at && run.completed_at
                    ? Math.round(
                        (new Date(run.completed_at).getTime() -
                          new Date(run.started_at).getTime()) /
                          1000
                      )
                    : null;

                return (
                  <tr key={run.id}>
                    <td>
                      <span
                        className={`severity-badge ${
                          run.status === "completed"
                            ? "info"
                            : run.status === "failed"
                              ? "critical"
                              : "warning"
                        }`}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td>
                      {run.started_at
                        ? new Date(run.started_at).toLocaleString()
                        : "—"}
                    </td>
                    <td>{duration !== null ? `${duration}s` : "—"}</td>
                    <td>{run.sources_checked}</td>
                    <td>{run.items_found}</td>
                    <td>{run.alerts_generated}</td>
                    <td
                      style={{
                        color: run.error_log
                          ? "var(--accent-rose)"
                          : "var(--text-muted)",
                        maxWidth: 200,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                      title={run.error_log || undefined}
                    >
                      {run.error_log || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty-state glass-card">
          <div className="icon">🤖</div>
          <p>No scan runs yet. Start the agent to begin.</p>
        </div>
      )}
    </div>
  );
}
