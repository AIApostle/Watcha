import { useEffect, useState, type FormEvent } from "react";
import {
  Settings,
  Send,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
  Coins,
  User,
  Building2,
  Server,
  RefreshCw,
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../hooks/useAuth";
import type { WatchedAsset } from "../lib/types";
import {
  getApiBaseUrl,
  setCustomApiUrl,
  resetApiUrl,
  DEFAULT_PROD_API_URL,
} from "../lib/apiConfig";

interface WatchablePreset {
  symbol: string;
  name: string;
  category: "asset" | "person" | "organization";
  description?: string;
}

// Preset monitoring targets
const PRESET_ITEMS: WatchablePreset[] = [
  // Currencies & Metals
  { symbol: "XAU/USD", name: "Gold / US Dollar", category: "asset", description: "Spot Gold" },
  { symbol: "XAG/USD", name: "Silver / US Dollar", category: "asset", description: "Spot Silver" },
  { symbol: "EUR/USD", name: "Euro / US Dollar", category: "asset", description: "Forex Major" },
  { symbol: "GBP/USD", name: "British Pound / US Dollar", category: "asset", description: "Forex Major" },
  { symbol: "USD/JPY", name: "US Dollar / Japanese Yen", category: "asset", description: "Forex Major" },
  { symbol: "AUD/USD", name: "Australian Dollar / US Dollar", category: "asset", description: "Forex Commodity" },
  { symbol: "USD/CHF", name: "US Dollar / Swiss Franc", category: "asset", description: "Forex Major" },
  { symbol: "USD/CAD", name: "US Dollar / Canadian Dollar", category: "asset", description: "Forex Major" },
  { symbol: "BTC/USD", name: "Bitcoin / US Dollar", category: "asset", description: "Crypto" },
  { symbol: "ETH/USD", name: "Ethereum / US Dollar", category: "asset", description: "Crypto" },

  // Key Leaders & People
  { symbol: "PERSON:Donald Trump", name: "Donald Trump", category: "person", description: "US President — Trade, Tariffs & Policy" },
  { symbol: "PERSON:Jerome Powell", name: "Jerome Powell", category: "person", description: "Federal Reserve Chair — Interest Rates & Economy" },
  { symbol: "PERSON:Christine Lagarde", name: "Christine Lagarde", category: "person", description: "ECB President — European Monetary Policy" },
  { symbol: "PERSON:Elon Musk", name: "Elon Musk", category: "person", description: "Market, Tech & Crypto Influencer" },
  { symbol: "PERSON:Janet Yellen", name: "Janet Yellen", category: "person", description: "US Treasury — Debt, Sanctions & Dollar" },
  { symbol: "PERSON:Kazuo Ueda", name: "Kazuo Ueda", category: "person", description: "Bank of Japan Governor — Yen Policy" },

  // Organizations & Institutions
  { symbol: "ORG:Federal Reserve", name: "Federal Reserve (Fed)", category: "organization", description: "US Central Bank" },
  { symbol: "ORG:European Central Bank", name: "European Central Bank (ECB)", category: "organization", description: "Eurozone Central Bank" },
  { symbol: "ORG:OPEC", name: "OPEC / OPEC+", category: "organization", description: "Oil Production & Energy Policy" },
  { symbol: "ORG:SEC", name: "Securities & Exchange Commission (SEC)", category: "organization", description: "US Financial & Crypto Regulations" },
  { symbol: "ORG:US Treasury", name: "US Department of the Treasury", category: "organization", description: "US Fiscal & Bond Markets" },
  { symbol: "ORG:Bank of Japan", name: "Bank of Japan (BOJ)", category: "organization", description: "Japan Central Bank" },
];

export default function SettingsPage() {
  const { user } = useAuth();

  // Telegram
  const [chatId, setChatId] = useState(user?.telegram_chat_id || "");
  const [telegramVerified, setTelegramVerified] = useState(
    user?.telegram_verified || false
  );
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [verifyMessage, setVerifyMessage] = useState("");

  // Monitoring
  const [pollingInterval, setPollingInterval] = useState(
    user?.polling_interval || 15
  );
  const [alertSensitivity, setAlertSensitivity] = useState(
    user?.alert_sensitivity || "medium"
  );
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState("");

  // Watchlist Items (Assets, People, Organizations)
  const [assets, setAssets] = useState<WatchedAsset[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [addingAsset, setAddingAsset] = useState(false);

  // Watchlist Selector & Custom Creation State
  const [activeCategory, setActiveCategory] = useState<"all" | "asset" | "person" | "organization" | "custom">("all");
  const [selectedPreset, setSelectedPreset] = useState("");
  const [customName, setCustomName] = useState("");
  const [customCategory, setCustomCategory] = useState<"asset" | "person" | "organization">("person");

  // Load assets on mount
  useEffect(() => {
    const fetchAssets = async () => {
      try {
        const resp = await api.get<WatchedAsset[]>("/settings/assets");
        setAssets(resp.data);
      } catch (err) {
        console.error("Assets fetch error:", err);
      } finally {
        setAssetsLoading(false);
      }
    };
    fetchAssets();
  }, []);

  // Save Settings
  const handleSaveSettings = async (e: FormEvent) => {
    e.preventDefault();
    setSettingsSaving(true);
    setSettingsMessage("");

    try {
      await api.put("/settings", {
        telegram_chat_id: chatId || null,
        polling_interval: pollingInterval,
        alert_sensitivity: alertSensitivity,
      });
      setSettingsMessage("✅ Settings saved successfully.");
      if (chatId !== user?.telegram_chat_id) {
        setTelegramVerified(false);
      }
    } catch (err: any) {
      setSettingsMessage(
        `❌ ${err.response?.data?.detail || "Failed to save settings."}`
      );
    } finally {
      setSettingsSaving(false);
    }
  };

  // Verify Telegram
  const handleVerifyTelegram = async () => {
    if (!chatId) return;
    setVerifyLoading(true);
    setVerifyMessage("");

    try {
      await api.put("/settings", { telegram_chat_id: chatId });
      const resp = await api.post<{ success: boolean; message: string }>(
        "/settings/telegram/verify"
      );
      setVerifyMessage(resp.data.message);
      setTelegramVerified(resp.data.success);
    } catch (err: any) {
      setVerifyMessage(
        `❌ ${err.response?.data?.detail || "Verification failed."}`
      );
    } finally {
      setVerifyLoading(false);
    }
  };

  // Backend API URL Configuration
  const [backendUrl, setBackendUrl] = useState(getApiBaseUrl());
  const [apiTesting, setApiTesting] = useState(false);
  const [apiStatus, setApiStatus] = useState<"connected" | "disconnected" | "checking">("checking");
  const [apiMessage, setApiMessage] = useState("");

  const checkApiHealth = async (urlToCheck?: string) => {
    const target = (urlToCheck !== undefined ? urlToCheck : backendUrl).trim().replace(/\/+$/, "");
    if (!target) return;
    setApiTesting(true);
    setApiStatus("checking");
    setApiMessage("");
    try {
      const resp = await fetch(`${target}/api/health`, { method: "GET" });
      if (resp.ok) {
        const data = await resp.json();
        setApiStatus("connected");
        setApiMessage(`Active & operational (${data.service || "Watcha"})`);
      } else {
        setApiStatus("disconnected");
        setApiMessage(`Server returned status HTTP ${resp.status}`);
      }
    } catch {
      setApiStatus("disconnected");
      setApiMessage("Cannot reach backend. If hosted on Render Free tier, it may take 30-50s to wake from sleep.");
    } finally {
      setApiTesting(false);
    }
  };

  useEffect(() => {
    checkApiHealth(getApiBaseUrl());
  }, []);

  const handleSaveBackendUrl = async (e: FormEvent) => {
    e.preventDefault();
    setCustomApiUrl(backendUrl);
    await checkApiHealth(backendUrl);
  };

  const handleResetBackendUrl = async () => {
    resetApiUrl();
    const defaultUrl = getApiBaseUrl();
    setBackendUrl(defaultUrl);
    await checkApiHealth(defaultUrl);
  };

  // Add Preset Item (Asset, Person, or Organization)
  const handleAddPreset = async () => {
    if (!selectedPreset) return;
    setAddingAsset(true);

    const item = PRESET_ITEMS.find((p) => p.symbol === selectedPreset);
    if (!item) {
      setAddingAsset(false);
      return;
    }

    try {
      const resp = await api.post<WatchedAsset>("/settings/assets", {
        asset_symbol: item.symbol,
        asset_name: item.name,
        entity_type: item.category,
      });
      setAssets([...assets, resp.data]);
      setSelectedPreset("");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add to watchlist.");
    } finally {
      setAddingAsset(false);
    }
  };

  // Add Custom Entity
  const handleAddCustom = async () => {
    if (!customName.trim()) return;
    setAddingAsset(true);

    const cleanName = customName.trim();
    let symbol = cleanName;
    if (customCategory === "person") symbol = `PERSON:${cleanName}`;
    else if (customCategory === "organization") symbol = `ORG:${cleanName}`;

    try {
      const resp = await api.post<WatchedAsset>("/settings/assets", {
        asset_symbol: symbol,
        asset_name: cleanName,
        entity_type: customCategory,
      });
      setAssets([...assets, resp.data]);
      setCustomName("");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add custom target.");
    } finally {
      setAddingAsset(false);
    }
  };

  // Remove Watchlist Item
  const handleRemoveAsset = async (assetId: string) => {
    try {
      await api.delete(`/settings/assets/${assetId}`);
      setAssets(assets.filter((a) => a.id !== assetId));
    } catch (err) {
      console.error("Remove asset error:", err);
    }
  };

  // Filter available presets that haven't been added yet
  const availablePresets = PRESET_ITEMS.filter((p) => {
    const alreadyAdded = assets.some(
      (wa) =>
        wa.asset_symbol === p.symbol ||
        wa.asset_name.toLowerCase() === p.name.toLowerCase()
    );
    if (alreadyAdded) return false;
    if (activeCategory === "all") return true;
    return p.category === activeCategory;
  });

  // Helper for badge display
  const getItemBadge = (item: WatchedAsset) => {
    const sym = item.asset_symbol;
    if (sym.startsWith("PERSON:") || item.entity_type === "person") {
      return {
        type: "person",
        label: "Person / Leader",
        icon: <User size={13} />,
        color: "#60a5fa",
        bg: "rgba(59, 130, 246, 0.15)",
        displayName: item.asset_name || sym.replace("PERSON:", ""),
        displaySymbol: "PERSON",
      };
    }
    if (sym.startsWith("ORG:") || item.entity_type === "organization") {
      return {
        type: "organization",
        label: "Organization",
        icon: <Building2 size={13} />,
        color: "#c084fc",
        bg: "rgba(168, 85, 247, 0.15)",
        displayName: item.asset_name || sym.replace("ORG:", ""),
        displaySymbol: "ORG",
      };
    }
    return {
      type: "asset",
      label: "Market Pair",
      icon: <Coins size={13} />,
      color: "#34d399",
      bg: "rgba(16, 185, 129, 0.15)",
      displayName: item.asset_name,
      displaySymbol: sym,
    };
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1>
          <Settings
            size={24}
            style={{ display: "inline", marginRight: "0.5rem" }}
          />
          Settings
        </h1>
        <p>Configure your monitoring preferences</p>
      </div>

      {/* ── Telegram Section ──────────────────────────────────────── */}
      <div className="glass-card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>
          📱 Telegram Notifications
        </h3>

        <div className="form-group">
          <label className="form-label">Telegram Chat ID</label>
          <div style={{ display: "flex", gap: "0.75rem", flexWrap: "wrap" }}>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. 123456789"
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              style={{ flex: "1 1 200px", minWidth: 0 }}
            />
            <button
              className="btn btn-secondary"
              onClick={handleVerifyTelegram}
              disabled={verifyLoading || !chatId}
              style={{ flexShrink: 0 }}
            >
              <Send size={16} />
              {verifyLoading ? "Sending…" : "Verify"}
            </button>
          </div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              marginTop: "0.5rem",
              fontSize: "0.82rem",
            }}
          >
            {telegramVerified ? (
              <>
                <CheckCircle size={14} color="var(--accent-emerald)" />
                <span style={{ color: "var(--accent-emerald)" }}>Verified</span>
              </>
            ) : (
              <>
                <XCircle size={14} color="var(--text-muted)" />
                <span style={{ color: "var(--text-muted)" }}>Not verified</span>
              </>
            )}
          </div>
          {verifyMessage && (
            <p style={{ fontSize: "0.85rem", marginTop: "0.5rem" }}>
              {verifyMessage}
            </p>
          )}
        </div>

        <p
          style={{
            fontSize: "0.82rem",
            color: "var(--text-muted)",
            margin: 0,
          }}
        >
          Message <strong>@userinfobot</strong> on Telegram to find your chat
          ID. Then message your bot to enable it to send you messages.
        </p>
      </div>

      {/* ── Watched Assets & Entities Section ──────────────────────── */}
      <div className="glass-card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
          <div>
            <h3 style={{ marginTop: 0, marginBottom: "0.25rem" }}>
              👁️ Watchlist (Currencies, Leaders & Organizations)
            </h3>
            <p style={{ margin: 0, fontSize: "0.83rem", color: "var(--text-muted)" }}>
              The AI agent monitors breaking news, speeches, statements, and market movements for these targets.
            </p>
          </div>
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)", background: "rgba(255,255,255,0.06)", padding: "0.25rem 0.6rem", borderRadius: "20px" }}>
            {assets.length} Active Target{assets.length === 1 ? "" : "s"}
          </span>
        </div>

        {/* Current Assets */}
        {assetsLoading ? (
          <div className="loading-spinner" style={{ margin: "1rem auto" }} />
        ) : assets.length > 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.6rem",
              marginBottom: "1.25rem",
            }}
          >
            {assets.map((asset) => {
              const badge = getItemBadge(asset);
              return (
                <div
                  key={asset.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "0.65rem 1rem",
                    background: "rgba(255, 255, 255, 0.02)",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                    <span
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.3rem",
                        padding: "0.25rem 0.6rem",
                        fontSize: "0.72rem",
                        fontWeight: 600,
                        color: badge.color,
                        background: badge.bg,
                        borderRadius: "6px",
                        letterSpacing: "0.02em",
                      }}
                    >
                      {badge.icon}
                      {badge.label}
                    </span>

                    <div>
                      <strong style={{ fontSize: "0.92rem", color: "var(--text-primary)" }}>
                        {badge.displayName}
                      </strong>
                      <span
                        style={{
                          color: "var(--text-muted)",
                          fontSize: "0.8rem",
                          marginLeft: "0.5rem",
                        }}
                      >
                        ({badge.displaySymbol})
                      </span>
                    </div>
                  </div>

                  <button
                    className="btn btn-danger"
                    onClick={() => handleRemoveAsset(asset.id)}
                    style={{ padding: "0.35rem 0.6rem", fontSize: "0.75rem" }}
                    title="Remove from watchlist"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              );
            })}
          </div>
        ) : (
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.85rem",
              marginBottom: "1.25rem",
            }}
          >
            No targets being watched yet. Select an asset, leader, or organization below to start monitoring.
          </p>
        )}

        {/* Add Target Controls */}
        <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "1.2rem" }}>
          <label className="form-label" style={{ marginBottom: "0.6rem", display: "block" }}>
            Add Target to Watchlist
          </label>

          {/* Category Filter Tabs */}
          <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", marginBottom: "0.85rem" }}>
            {[
              { id: "all", label: "All Presets" },
              { id: "asset", label: "💰 Market Pairs" },
              { id: "person", label: "👤 Key Leaders" },
              { id: "organization", label: "🏛️ Organizations" },
              { id: "custom", label: "➕ Custom Target" },
            ].map((tab) => (
              <button
                key={tab.id}
                type="button"
                onClick={() => {
                  setActiveCategory(tab.id as any);
                  setSelectedPreset("");
                }}
                style={{
                  padding: "0.35rem 0.75rem",
                  fontSize: "0.78rem",
                  borderRadius: "20px",
                  border: "1px solid",
                  borderColor:
                    activeCategory === tab.id
                      ? "var(--accent-indigo, #6366f1)"
                      : "var(--border-subtle)",
                  background:
                    activeCategory === tab.id
                      ? "rgba(99, 102, 241, 0.2)"
                      : "rgba(255, 255, 255, 0.03)",
                  color:
                    activeCategory === tab.id
                      ? "#fff"
                      : "var(--text-secondary)",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* Preset Selector vs Custom Input Form */}
          {activeCategory === "custom" ? (
            <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
              <select
                className="form-select"
                value={customCategory}
                onChange={(e) => setCustomCategory(e.target.value as any)}
                style={{ flex: "1 1 140px", minWidth: 0 }}
              >
                <option value="person">👤 Person / Leader</option>
                <option value="organization">🏛️ Organization</option>
                <option value="asset">💰 Financial Asset</option>
              </select>

              <input
                className="form-input"
                type="text"
                placeholder="e.g. Bank of England, Jensen Huang, OPEC..."
                value={customName}
                onChange={(e) => setCustomName(e.target.value)}
                style={{ flex: "2 1 180px", minWidth: 0 }}
              />

              <button
                className="btn btn-primary"
                onClick={handleAddCustom}
                disabled={!customName.trim() || addingAsset}
                style={{ flexShrink: 0, whiteSpace: "nowrap" }}
              >
                <Plus size={16} />
                {addingAsset ? "Adding…" : "Add Custom"}
              </button>
            </div>
          ) : (
            <div style={{ display: "flex", gap: "0.6rem", flexWrap: "wrap" }}>
              <select
                className="form-select"
                value={selectedPreset}
                onChange={(e) => setSelectedPreset(e.target.value)}
                style={{ flex: "1 1 240px", minWidth: 0 }}
              >
                <option value="">
                  {availablePresets.length > 0
                    ? "Choose a target to watch…"
                    : "All presets in this category are already active!"}
                </option>
                {availablePresets.map((p) => (
                  <option key={p.symbol} value={p.symbol}>
                    {p.category === "person" ? "👤" : p.category === "organization" ? "🏛️" : "💰"}{" "}
                    {p.name} {p.description ? `— ${p.description}` : ""}
                  </option>
                ))}
              </select>

              <button
                className="btn btn-primary"
                onClick={handleAddPreset}
                disabled={!selectedPreset || addingAsset}
                style={{ flexShrink: 0, whiteSpace: "nowrap" }}
              >
                <Plus size={16} />
                {addingAsset ? "Adding…" : "Add Target"}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Monitoring Settings ───────────────────────────────────── */}
      <div className="glass-card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>
          ⚙️ Monitoring Preferences
        </h3>

        <form onSubmit={handleSaveSettings}>
          <div className="form-group">
            <label className="form-label">Polling Interval</label>
            <select
              className="form-select"
              value={pollingInterval}
              onChange={(e) => setPollingInterval(Number(e.target.value))}
            >
              <option value={5}>Every 5 minutes</option>
              <option value={15}>Every 15 minutes</option>
              <option value={30}>Every 30 minutes</option>
              <option value={60}>Every 60 minutes</option>
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Alert Sensitivity</label>
            <select
              className="form-select"
              value={alertSensitivity}
              onChange={(e) => setAlertSensitivity(e.target.value)}
            >
              <option value="all">
                All — send all alerts (Low, Medium, & High)
              </option>
              <option value="high">
                High — major & critical events (impact ≥ 1)
              </option>
              <option value="medium">
                Medium — significant events only (impact ≥ 4)
              </option>
              <option value="low">
                Low — critical events only (impact ≥ 7)
              </option>
            </select>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={settingsSaving}
          >
            {settingsSaving ? "Saving…" : "Save Settings"}
          </button>

          {settingsMessage && (
            <p
              style={{
                fontSize: "0.85rem",
                marginTop: "0.75rem",
                marginBottom: 0,
              }}
            >
              {settingsMessage}
            </p>
          )}
        </form>
      </div>

      {/* ── Backend Server Connection ─────────────────────────────── */}
      <div className="glass-card" style={{ padding: "1.5rem", marginBottom: "2rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", flexWrap: "wrap", gap: "0.5rem" }}>
          <h3 style={{ margin: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <Server size={20} color="var(--color-primary, #6366f1)" /> Backend API Server
          </h3>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
                padding: "0.2rem 0.65rem",
                borderRadius: "9999px",
                fontSize: "0.75rem",
                fontWeight: 600,
                background:
                  apiStatus === "connected"
                    ? "rgba(34, 197, 94, 0.15)"
                    : apiStatus === "checking"
                    ? "rgba(234, 179, 8, 0.15)"
                    : "rgba(239, 68, 68, 0.15)",
                color:
                  apiStatus === "connected"
                    ? "#22c55e"
                    : apiStatus === "checking"
                    ? "#eab308"
                    : "#ef4444",
                border: `1px solid ${
                  apiStatus === "connected"
                    ? "rgba(34, 197, 94, 0.3)"
                    : apiStatus === "checking"
                    ? "rgba(234, 179, 8, 0.3)"
                    : "rgba(239, 68, 68, 0.3)"
                }`,
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "50%",
                  background:
                    apiStatus === "connected"
                      ? "#22c55e"
                      : apiStatus === "checking"
                      ? "#eab308"
                      : "#ef4444",
                }}
              />
              {apiStatus === "connected"
                ? "Connected"
                : apiStatus === "checking"
                ? "Checking…"
                : "Disconnected"}
            </span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => checkApiHealth()}
              disabled={apiTesting}
              style={{ padding: "0.25rem 0.5rem", fontSize: "0.75rem" }}
              title="Test Connection"
            >
              <RefreshCw size={12} className={apiTesting ? "spin-icon" : ""} />
            </button>
          </div>
        </div>

        <p style={{ color: "var(--color-text-secondary, #94a3b8)", fontSize: "0.85rem", marginTop: 0, marginBottom: "1rem" }}>
          Configure where this frontend sends API requests. Hosted Vercel deployments automatically connect to your Render cloud backend, while local testing routes to localhost.
        </p>

        <form onSubmit={handleSaveBackendUrl}>
          <div className="form-group" style={{ marginBottom: "1rem" }}>
            <label className="form-label" style={{ display: "flex", justifyContent: "space-between" }}>
              <span>API Base URL</span>
              <span style={{ fontSize: "0.75rem", color: "var(--color-text-muted, #64748b)" }}>
                Default: {DEFAULT_PROD_API_URL}
              </span>
            </label>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <input
                type="text"
                className="form-input"
                style={{ flex: 1, minWidth: "240px" }}
                value={backendUrl}
                onChange={(e) => setBackendUrl(e.target.value)}
                placeholder="https://your-backend.onrender.com"
              />
              <button
                type="submit"
                className="btn btn-primary btn-sm"
                disabled={apiTesting}
              >
                Save & Connect
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleResetBackendUrl}
                disabled={apiTesting}
              >
                Reset Default
              </button>
            </div>
          </div>

          {apiMessage && (
            <p
              style={{
                fontSize: "0.82rem",
                marginTop: "0.5rem",
                marginBottom: 0,
                color: apiStatus === "connected" ? "#22c55e" : "#f87171",
              }}
            >
              {apiStatus === "connected" ? "✓" : "⚠"} {apiMessage}
            </p>
          )}
        </form>
      </div>
    </div>
  );
}
