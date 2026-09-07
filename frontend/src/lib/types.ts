// ──────────────────────────────────────────────────────
// TheWatcher — Shared TypeScript Types
// ──────────────────────────────────────────────────────

export interface UserProfile {
  id: string;
  email: string;
  telegram_chat_id: string | null;
  telegram_verified: boolean;
  polling_interval: number;
  alert_sensitivity: string;
  created_at: string | null;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface WatchedAsset {
  id: string;
  user_id: string;
  asset_symbol: string;
  asset_name: string;
  entity_type?: "asset" | "person" | "organization";
  is_active: boolean;
  created_at: string;
}

export interface PriceData {
  symbol: string;
  current_price: number;
  open_price: number | null;
  high_price: number | null;
  low_price: number | null;
  previous_close: number | null;
  change: number | null;
  change_percent: number | null;
  timestamp: string | null;
}

export interface Alert {
  id: string;
  user_id: string;
  asset_symbol: string | null;
  alert_type: string;
  severity: "critical" | "warning" | "info";
  title: string;
  body: string | null;
  ai_analysis: string | null;
  impact_score: number | null;
  sentiment: "bullish" | "bearish" | "neutral" | null;
  telegram_sent: boolean;
  created_at: string;
}

export interface NewsItem {
  id: string;
  source: string;
  source_type: string;
  title: string;
  url: string | null;
  summary: string | null;
  sentiment_score: number | null;
  published_at: string | null;
  fetched_at: string;
}

export interface AgentStatus {
  is_running: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  total_runs: number;
  active_users: number;
}

export interface AgentRun {
  id: string;
  user_id: string | null;
  started_at: string | null;
  completed_at: string | null;
  status: "running" | "completed" | "failed";
  sources_checked: number;
  items_found: number;
  alerts_generated: number;
  error_log: string | null;
}

export interface DashboardData {
  prices: PriceData[];
  recent_alerts: Alert[];
  market_mood: string | null;
  mood_summary: string | null;
  agent_running: boolean;
  total_alerts_today: number;
  watched_assets_count?: number;
}
