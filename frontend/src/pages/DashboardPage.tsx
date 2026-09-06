import { useEffect, useState } from "react";
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Bell,
  BarChart3,
} from "lucide-react";
import api from "../lib/api";
import type { DashboardData } from "../lib/types";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const resp = await api.get<DashboardData>("/dashboard");
        setData(resp.data);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 60000); // Refresh every 60s
    return () => clearInterval(interval);
  }, []);

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
        <h1>Dashboard</h1>
        <p>Real-time market overview and alerts</p>
      </div>

      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card glass-card">
          <div className="stat-label">Agent Status</div>
          <div
            className="stat-value"
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
            }}
          >
            <span
              className={`status-dot ${data?.agent_running ? "running" : "stopped"}`}
            />
            {data?.agent_running ? "Running" : "Stopped"}
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-label">Alerts Today</div>
          <div className="stat-value" style={{ color: "var(--accent-amber)" }}>
            {data?.total_alerts_today ?? 0}
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-label">Watched Assets</div>
          <div className="stat-value" style={{ color: "var(--accent-indigo)" }}>
            {data?.prices.length ?? 0}
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-label">Market Mood</div>
          <div
            className="stat-value"
            style={{
              color:
                data?.market_mood === "bullish"
                  ? "var(--accent-emerald)"
                  : data?.market_mood === "bearish"
                    ? "var(--accent-rose)"
                    : "var(--text-secondary)",
            }}
          >
            {data?.market_mood
              ? data.market_mood.charAt(0).toUpperCase() +
                data.market_mood.slice(1)
              : "—"}
          </div>
        </div>
      </div>

      {/* Price Cards */}
      <h2 className="section-title">
        <BarChart3 size={18} /> Live Prices
      </h2>
      {data?.prices && data.prices.length > 0 ? (
        <div className="cards-grid">
          {data.prices.map((price) => {
            const isPositive = (price.change_percent ?? 0) >= 0;
            const isZero = price.change_percent === 0 || price.change_percent === null;

            return (
              <div key={price.symbol} className="price-card glass-card">
                <div className="symbol">{price.symbol}</div>
                <div className="price">
                  ${price.current_price.toLocaleString(undefined, {
                    minimumFractionDigits: 2,
                    maximumFractionDigits: 2,
                  })}
                </div>
                <div
                  className={`change ${isZero ? "neutral" : isPositive ? "positive" : "negative"}`}
                >
                  {isZero ? (
                    <Minus size={16} />
                  ) : isPositive ? (
                    <TrendingUp size={16} />
                  ) : (
                    <TrendingDown size={16} />
                  )}
                  {price.change_percent !== null
                    ? `${price.change_percent >= 0 ? "+" : ""}${price.change_percent.toFixed(2)}%`
                    : "—"}
                  {price.change !== null && (
                    <span style={{ color: "var(--text-muted)", marginLeft: "0.5rem" }}>
                      ({price.change >= 0 ? "+" : ""}
                      {price.change.toFixed(2)})
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-state glass-card">
          <div className="icon">📊</div>
          <p>No assets being watched. Add some in Settings.</p>
        </div>
      )}

      {/* Recent Alerts */}
      <h2 className="section-title">
        <Bell size={18} /> Recent Alerts
      </h2>
      {data?.recent_alerts && data.recent_alerts.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {data.recent_alerts.map((alert) => (
            <div key={alert.id} className="alert-card glass-card">
              <div className="alert-header">
                <span className={`severity-badge ${alert.severity}`}>
                  {alert.severity}
                </span>
                {alert.asset_symbol && (
                  <span style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>
                    {alert.asset_symbol}
                  </span>
                )}
                {alert.sentiment && (
                  <span
                    style={{
                      marginLeft: "auto",
                      fontSize: "0.8rem",
                      color:
                        alert.sentiment === "bullish"
                          ? "var(--accent-emerald)"
                          : alert.sentiment === "bearish"
                            ? "var(--accent-rose)"
                            : "var(--text-muted)",
                    }}
                  >
                    {alert.sentiment === "bullish"
                      ? "📈"
                      : alert.sentiment === "bearish"
                        ? "📉"
                        : "➡️"}{" "}
                    {alert.sentiment}
                  </span>
                )}
              </div>
              <div className="alert-title">{alert.title}</div>
              {alert.ai_analysis && (
                <div className="alert-body">{alert.ai_analysis}</div>
              )}
              <div className="alert-meta">
                {alert.impact_score && <span>Impact: {alert.impact_score}/10</span>}
                <span>
                  {new Date(alert.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state glass-card">
          <div className="icon">🔔</div>
          <p>No alerts yet. Start the agent to begin monitoring.</p>
        </div>
      )}
    </div>
  );
}
