// src/components/QRScanner.jsx
// QR scanner: Camera (live) + Upload Image — powered by html5-qrcode
import { useEffect, useRef, useState } from "react";
import { X, Camera, Upload, RefreshCw, CheckCircle, ImageUp } from "lucide-react";

const CONTAINER_ID = "inventra-qr-scanner";

export default function QRScanner({ onScan, onClose, title = "Scan Product QR Code" }) {
  const [mode, setMode]       = useState("camera");   // "camera" | "upload"
  const [error, setError]     = useState("");
  const [ready, setReady]     = useState(false);
  const [cameras, setCameras] = useState([]);
  const [camIdx, setCamIdx]   = useState(0);
  const [uploadResult, setUploadResult] = useState(null); // { text, ok }
  const [uploading, setUploading]       = useState(false);
  const scannerRef  = useRef(null);
  const fileInputRef = useRef(null);

  // ── Camera helpers ──────────────────────────────────────────────────────────
  async function stopCamera() {
    if (scannerRef.current) {
      try { await scannerRef.current.stop(); } catch (_) {}
      scannerRef.current = null;
    }
    setReady(false);
  }

  async function startCamera(cameraId) {
    setError("");
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      await stopCamera();
      const scanner = new Html5Qrcode(CONTAINER_ID);
      scannerRef.current = scanner;
      await scanner.start(
        cameraId || { facingMode: "environment" },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (text) => { stopCamera(); onScan(text.trim()); },
        () => {}
      );
      setReady(true);
    } catch (err) {
      const msg = err?.message ?? "";
      setError(
        msg.includes("Permission")
          ? "Camera permission denied. Allow camera access and try again."
          : msg || "Could not start camera."
      );
    }
  }

  async function switchCamera() {
    const next = (camIdx + 1) % cameras.length;
    setCamIdx(next);
    await startCamera(cameras[next].id);
  }

  // ── Upload helper ───────────────────────────────────────────────────────────
  async function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploadResult(null);
    setError("");
    setUploading(true);
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      const scanner = new Html5Qrcode("qr-file-scanner-hidden");
      const result  = await scanner.scanFile(file, false);
      setUploadResult({ text: result, ok: true });
      // Short delay so user sees the success state, then fire callback
      setTimeout(() => onScan(result.trim()), 900);
    } catch (err) {
      setUploadResult({ text: "No QR code found in this image. Try a clearer photo.", ok: false });
    } finally {
      setUploading(false);
      // Reset so the same file can be re-selected
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  // ── Mode switching ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (mode === "camera") {
      (async () => {
        try {
          const { Html5Qrcode } = await import("html5-qrcode");
          const devices = await Html5Qrcode.getCameras();
          setCameras(devices);
          await startCamera(devices[0]?.id ?? null);
        } catch (_) {
          setError("No cameras found or camera access blocked.");
        }
      })();
    } else {
      stopCamera();
      setError("");
      setUploadResult(null);
    }
    return () => { stopCamera(); };
  }, [mode]);

  const handleClose = async () => { await stopCamera(); onClose(); };

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 400,
      background: "#000000cc", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      {/* Hidden div required by html5-qrcode for file scanning */}
      <div id="qr-file-scanner-hidden" style={{ display: "none" }} />

      <div style={{
        background: "var(--surface)", borderRadius: 20,
        width: 380, overflow: "hidden",
        boxShadow: "0 24px 64px #00000090",
        border: "1px solid var(--line)",
        animation: "slideUp 0.2s ease",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "16px 20px",
          background: "linear-gradient(135deg, var(--purple), #7c6ced)",
        }}>
          <Camera size={17} color="#fff" />
          <span style={{ font: "700 14px Manrope", color: "#fff" }}>{title}</span>
          <button onClick={handleClose}
            style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "#fff", opacity: 0.8 }}>
            <X size={18} />
          </button>
        </div>

        {/* Mode tabs */}
        <div style={{
          display: "flex", borderBottom: "1px solid var(--line)",
          background: "var(--surface-2)",
        }}>
          {[
            { key: "camera", icon: <Camera size={13} />, label: "Camera" },
            { key: "upload", icon: <ImageUp size={13} />, label: "Upload Image" },
          ].map(tab => (
            <button key={tab.key} onClick={() => setMode(tab.key)} style={{
              flex: 1, padding: "11px 0",
              display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
              background: "none", border: "none", cursor: "pointer",
              fontSize: 12, fontWeight: 600,
              color: mode === tab.key ? "var(--purple)" : "var(--muted)",
              borderBottom: mode === tab.key ? "2px solid var(--purple)" : "2px solid transparent",
              transition: "color 0.15s, border-color 0.15s",
            }}>
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div style={{ padding: 20 }}>

          {/* ── CAMERA mode ────────────────────────────────────────── */}
          {mode === "camera" && (
            <>
              {error ? (
                <div style={{ textAlign: "center", padding: "30px 16px" }}>
                  <div style={{ fontSize: 36, marginBottom: 10 }}>📷</div>
                  <div style={{ fontSize: 12, color: "var(--danger)", marginBottom: 16 }}>{error}</div>
                  <button className="btn btn-secondary btn-sm" onClick={() => startCamera(cameras[camIdx]?.id ?? null)}>
                    <RefreshCw size={12} /> Try Again
                  </button>
                </div>
              ) : (
                <>
                  <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "#000" }}>
                    <div id={CONTAINER_ID} style={{ width: "100%", minHeight: 260 }} />
                    {/* Corner decorators */}
                    {ready && (
                      <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
                        {[
                          { top: 0, left: 0, borderTop: 1, borderLeft: 1, borderRadius: "6px 0 0 0" },
                          { top: 0, right: 0, borderTop: 1, borderRight: 1, borderRadius: "0 6px 0 0" },
                          { bottom: 0, right: 0, borderBottom: 1, borderRight: 1, borderRadius: "0 0 6px 0" },
                          { bottom: 0, left: 0, borderBottom: 1, borderLeft: 1, borderRadius: "0 0 0 6px" },
                        ].map((s, i) => (
                          <div key={i} style={{
                            position: "absolute", width: 26, height: 26, margin: 18,
                            borderStyle: "solid", borderColor: "var(--purple)", borderWidth: 0,
                            borderTopWidth:    s.borderTop    ? 3 : 0,
                            borderRightWidth:  s.borderRight  ? 3 : 0,
                            borderBottomWidth: s.borderBottom ? 3 : 0,
                            borderLeftWidth:   s.borderLeft   ? 3 : 0,
                            borderRadius: s.borderRadius,
                            ...{ top: s.top, left: s.left, right: s.right, bottom: s.bottom },
                          }} />
                        ))}
                      </div>
                    )}
                  </div>
                  <p style={{ textAlign: "center", fontSize: 11, color: "var(--muted)", marginTop: 10, marginBottom: 8 }}>
                    Point at a product QR code — scans automatically
                  </p>
                  {cameras.length > 1 && (
                    <button className="btn btn-ghost btn-sm" style={{ width: "100%" }} onClick={switchCamera}>
                      <RefreshCw size={12} /> Switch Camera ({camIdx + 1}/{cameras.length})
                    </button>
                  )}
                </>
              )}
            </>
          )}

          {/* ── UPLOAD mode ────────────────────────────────────────── */}
          {mode === "upload" && (
            <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

              {/* Drop zone / file picker */}
              <label htmlFor="qr-file-input" style={{
                display: "flex", flexDirection: "column", alignItems: "center",
                gap: 12, padding: "32px 20px",
                border: "2px dashed var(--line)", borderRadius: 14,
                cursor: "pointer", transition: "border-color 0.15s, background 0.15s",
                background: uploading ? "var(--surface-2)" : "transparent",
              }}
                onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = "var(--purple)"; }}
                onDragLeave={e => { e.currentTarget.style.borderColor = "var(--line)"; }}
                onDrop={async e => {
                  e.preventDefault();
                  e.currentTarget.style.borderColor = "var(--line)";
                  const file = e.dataTransfer.files?.[0];
                  if (file && fileInputRef.current) {
                    // Simulate file input change
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    fileInputRef.current.files = dt.files;
                    fileInputRef.current.dispatchEvent(new Event("change", { bubbles: true }));
                  }
                }}
                onMouseEnter={e => e.currentTarget.style.borderColor = "var(--purple)"}
                onMouseLeave={e => e.currentTarget.style.borderColor = uploading ? "var(--purple)" : "var(--line)"}
              >
                {uploading ? (
                  <>
                    <div className="spinner" />
                    <span style={{ fontSize: 12, color: "var(--muted)" }}>Reading QR from image…</span>
                  </>
                ) : (
                  <>
                    <div style={{
                      width: 52, height: 52, borderRadius: "50%",
                      background: "var(--purple-glow)", border: "1px solid var(--purple)",
                      display: "grid", placeItems: "center",
                    }}>
                      <Upload size={22} color="var(--purple)" />
                    </div>
                    <div style={{ textAlign: "center" }}>
                      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 4 }}>Click to upload or drag & drop</div>
                      <div style={{ fontSize: 11, color: "var(--muted)" }}>PNG, JPG, WEBP — photo of a QR code</div>
                    </div>
                  </>
                )}
              </label>

              <input
                id="qr-file-input"
                ref={fileInputRef}
                type="file"
                accept="image/*"
                style={{ display: "none" }}
                onChange={handleFileChange}
              />

              {/* Result */}
              {uploadResult && (
                <div style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "12px 14px", borderRadius: 10, fontSize: 12,
                  background: uploadResult.ok ? "#4ade8015" : "#f8717115",
                  border: `1px solid ${uploadResult.ok ? "#4ade8040" : "#f8717140"}`,
                  color: uploadResult.ok ? "#4ade80" : "#f87171",
                }}>
                  {uploadResult.ok
                    ? <CheckCircle size={15} style={{ flexShrink: 0, marginTop: 1 }} />
                    : <span style={{ flexShrink: 0 }}>✕</span>
                  }
                  <div>
                    {uploadResult.ok
                      ? <><strong>QR detected:</strong> {uploadResult.text}<br /><span style={{ fontSize: 10, opacity: 0.8 }}>Identifying product…</span></>
                      : uploadResult.text
                    }
                  </div>
                </div>
              )}

              {/* Tips */}
              {!uploadResult && !uploading && (
                <div style={{ fontSize: 11, color: "var(--muted)", lineHeight: 1.6, padding: "0 4px" }}>
                  <strong style={{ color: "var(--text-2)" }}>Tips for best results:</strong><br />
                  • Keep the QR code clearly visible and well-lit<br />
                  • Avoid blurry or angled photos<br />
                  • The QR code should take up most of the image
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
