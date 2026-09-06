import { useEffect, useState, type FormEvent } from "react";
import {
  Settings,
  Send,
  Plus,
  Trash2,
  CheckCircle,
  XCircle,
} from "lucide-react";
import api from "../lib/api";
import { useAuth } from "../hooks/useAuth";
import type { WatchedAsset } from "../lib/types";

// Common tradeable assets
const AVAILABLE_ASSETS = [
  { symbol: "XAU/USD", name: "Gold / US Dollar" },
  { symbol: "XAG/USD", name: "Silver / US Dollar" },
  { symbol: "EUR/USD", name: "Euro / US Dollar" },
  { symbol: "GBP/USD", name: "British Pound / US Dollar" },
  { symbol: "USD/JPY", name: "US Dollar / Japanese Yen" },
  { symbol: "AUD/USD", name: "Australian Dollar / US Dollar" },
  { symbol: "USD/CHF", name: "US Dollar / Swiss Franc" },
  { symbol: "USD/CAD", name: "US Dollar / Canadian Dollar" },
  { symbol: "BTC/USD", name: "Bitcoin / US Dollar" },
  { symbol: "ETH/USD", name: "Ethereum / US Dollar" },
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

  // Assets
  const [assets, setAssets] = useState<WatchedAsset[]>([]);
  const [assetsLoading, setAssetsLoading] = useState(true);
  const [addingAsset, setAddingAsset] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState("");

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
      // Save chat ID first
      await api.put("/settings", { telegram_chat_id: chatId });
      // Then verify
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

  // Add Asset
  const handleAddAsset = async () => {
    if (!selectedAsset) return;
    setAddingAsset(true);

    const assetInfo = AVAILABLE_ASSETS.find((a) => a.symbol === selectedAsset);
    if (!assetInfo) return;

    try {
      const resp = await api.post<WatchedAsset>("/settings/assets", {
        asset_symbol: assetInfo.symbol,
        asset_name: assetInfo.name,
      });
      setAssets([...assets, resp.data]);
      setSelectedAsset("");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to add asset.");
    } finally {
      setAddingAsset(false);
    }
  };

  // Remove Asset
  const handleRemoveAsset = async (assetId: string) => {
    try {
      await api.delete(`/settings/assets/${assetId}`);
      setAssets(assets.filter((a) => a.id !== assetId));
    } catch (err) {
      console.error("Remove asset error:", err);
    }
  };

  // Filter out already-added assets
  const availableToAdd = AVAILABLE_ASSETS.filter(
    (a) => !assets.some((wa) => wa.asset_symbol === a.symbol)
  );

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
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <input
              className="form-input"
              type="text"
              placeholder="e.g. 123456789"
              value={chatId}
              onChange={(e) => setChatId(e.target.value)}
              style={{ flex: 1 }}
            />
            <button
              className="btn btn-secondary"
              onClick={handleVerifyTelegram}
              disabled={verifyLoading || !chatId}
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

      {/* ── Watched Assets Section ────────────────────────────────── */}
      <div className="glass-card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0, marginBottom: "1rem" }}>
          📊 Watched Assets
        </h3>

        {/* Current Assets */}
        {assetsLoading ? (
          <div className="loading-spinner" style={{ margin: "1rem auto" }} />
        ) : assets.length > 0 ? (
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "0.5rem",
              marginBottom: "1rem",
            }}
          >
            {assets.map((asset) => (
              <div
                key={asset.id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.6rem 1rem",
                  background: "rgba(99, 102, 241, 0.05)",
                  borderRadius: "10px",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                <div>
                  <strong style={{ fontSize: "0.9rem" }}>
                    {asset.asset_symbol}
                  </strong>
                  <span
                    style={{
                      color: "var(--text-muted)",
                      fontSize: "0.8rem",
                      marginLeft: "0.75rem",
                    }}
                  >
                    {asset.asset_name}
                  </span>
                </div>
                <button
                  className="btn btn-danger"
                  onClick={() => handleRemoveAsset(asset.id)}
                  style={{ padding: "0.35rem 0.6rem", fontSize: "0.75rem" }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p
            style={{
              color: "var(--text-muted)",
              fontSize: "0.85rem",
              marginBottom: "1rem",
            }}
          >
            No assets being watched.
          </p>
        )}

        {/* Add Asset */}
        {availableToAdd.length > 0 && (
          <div style={{ display: "flex", gap: "0.75rem" }}>
            <select
              className="form-select"
              value={selectedAsset}
              onChange={(e) => setSelectedAsset(e.target.value)}
              style={{ flex: 1 }}
            >
              <option value="">Select an asset to watch…</option>
              {availableToAdd.map((a) => (
                <option key={a.symbol} value={a.symbol}>
                  {a.symbol} — {a.name}
                </option>
              ))}
            </select>
            <button
              className="btn btn-primary"
              onClick={handleAddAsset}
              disabled={!selectedAsset || addingAsset}
            >
              <Plus size={16} />
              {addingAsset ? "Adding…" : "Add"}
            </button>
          </div>
        )}
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
    </div>
  );
}
