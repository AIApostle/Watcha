import { useEffect, useState } from "react";
import { Newspaper, ExternalLink } from "lucide-react";
import api from "../lib/api";
import type { NewsItem } from "../lib/types";

export default function NewsPage() {
  const [news, setNews] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [sourceType, setSourceType] = useState("");

  useEffect(() => {
    const fetchNews = async () => {
      try {
        const params: Record<string, string> = {};
        if (sourceType) params.source_type = sourceType;
        const resp = await api.get<NewsItem[]>("/news", { params });
        setNews(resp.data);
      } catch (err) {
        console.error("News fetch error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchNews();
  }, [sourceType]);

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
          <Newspaper
            size={24}
            style={{ display: "inline", marginRight: "0.5rem" }}
          />
          News Feed
        </h1>
        <p>Aggregated financial and political news from all sources</p>
      </div>

      {/* Filters */}
      <div className="filters-bar" style={{ display: "flex", flexWrap: "wrap", gap: "0.5rem" }}>
        {[
          { key: "", label: "All Sources" },
          { key: "calendar", label: "📅 ForexFactory Calendar" },
          { key: "social", label: "🗣️ Trump & Social" },
          { key: "api", label: "⚡ Financial APIs" },
          { key: "rss", label: "📰 Major RSS" },
        ].map(({ key, label }) => (
          <button
            key={key}
            className={`btn ${sourceType === key ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setSourceType(key)}
            style={{ padding: "0.45rem 1rem", fontSize: "0.8rem" }}
          >
            {label}
          </button>
        ))}
      </div>

      {/* News List */}
      {news.length > 0 ? (
        <div
          style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}
        >
          {news.map((item) => (
            <div key={item.id} className="news-card glass-card">
              <div style={{ flex: "0 0 auto" }}>
                <span className={`source-badge ${item.source_type}`}>
                  {item.source}
                </span>
              </div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="news-title">
                  {item.url ? (
                    <a
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {item.title}{" "}
                      <ExternalLink
                        size={12}
                        style={{ display: "inline", verticalAlign: "middle" }}
                      />
                    </a>
                  ) : (
                    item.title
                  )}
                </div>
                {item.summary && (
                  <div className="news-summary">{item.summary}</div>
                )}
                <div className="news-meta">
                  {item.sentiment_score !== null && (
                    <span>
                      Sentiment:{" "}
                      {item.sentiment_score > 0
                        ? "📈"
                        : item.sentiment_score < 0
                          ? "📉"
                          : "➡️"}{" "}
                      {item.sentiment_score.toFixed(2)}
                    </span>
                  )}
                  {item.published_at && (
                    <span>
                      {" · "}
                      {new Date(item.published_at).toLocaleString()}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state glass-card">
          <div className="icon">📰</div>
          <p>No news articles yet. Run the agent to start collecting.</p>
        </div>
      )}
    </div>
  );
}
