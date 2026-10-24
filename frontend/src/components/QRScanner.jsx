// src/components/QRScanner.jsx
// Camera-based QR code scanner using html5-qrcode
import { useEffect, useRef, useState } from "react";
import { X, Camera, RefreshCw } from "lucide-react";

export default function QRScanner({ onScan, onClose, title = "Scan Product QR Code" }) {
  const containerId = "inventra-qr-scanner";
  const scannerRef  = useRef(null);
  const [error, setError]   = useState("");
  const [ready, setReady]   = useState(false);
  const [cameras, setCameras] = useState([]);
  const [camIdx, setCamIdx]   = useState(0);

  // Start scanner
  async function startScanner(cameraId) {
    setError("");
    try {
      const { Html5Qrcode } = await import("html5-qrcode");
      // Stop existing instance
      if (scannerRef.current) {
        try { await scannerRef.current.stop(); } catch (_) {}
        scannerRef.current = null;
      }

      const scanner = new Html5Qrcode(containerId);
      scannerRef.current = scanner;

      await scanner.start(
        cameraId || { facingMode: "environment" },
        { fps: 10, qrbox: { width: 220, height: 220 } },
        (decodedText) => {
          // decodedText is the SKU we encoded in the QR
          onScan(decodedText.trim());
          stopScanner();
        },
        () => {} // ignore ongoing scan errors
      );
      setReady(true);
    } catch (err) {
      setError(
        err?.message?.includes("Permission")
          ? "Camera permission denied. Please allow camera access and try again."
          : err?.message ?? "Could not start camera"
      );
    }
  }

  async function stopScanner() {
    if (scannerRef.current) {
      try { await scannerRef.current.stop(); } catch (_) {}
      scannerRef.current = null;
    }
  }

  useEffect(() => {
    // List cameras then start
    (async () => {
      try {
        const { Html5Qrcode } = await import("html5-qrcode");
        const devices = await Html5Qrcode.getCameras();
        setCameras(devices);
        if (devices.length > 0) {
          await startScanner(devices[0].id);
        } else {
          await startScanner(null); // try environment-facing
        }
      } catch (err) {
        setError("No cameras found or camera access blocked.");
      }
    })();

    return () => { stopScanner(); };
  }, []);

  async function switchCamera() {
    const next = (camIdx + 1) % cameras.length;
    setCamIdx(next);
    await startScanner(cameras[next].id);
  }

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 400,
      background: "#000000cc", backdropFilter: "blur(4px)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        background: "var(--surface)",
        borderRadius: 20,
        width: 360,
        overflow: "hidden",
        boxShadow: "0 24px 64px #00000090",
        border: "1px solid var(--line)",
      }}>
        {/* Header */}
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          padding: "16px 20px",
          background: "linear-gradient(135deg, var(--purple), #7c6ced)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Camera size={18} color="#fff" />
            <span style={{ font: "700 14px Manrope", color: "#fff" }}>{title}</span>
          </div>
          <button onClick={() => { stopScanner(); onClose(); }}
            style={{ background: "none", border: "none", cursor: "pointer", color: "#fff", opacity: 0.8 }}>
            <X size={18} />
          </button>
        </div>

        {/* Scanner viewport */}
        <div style={{ padding: 20 }}>
          {error ? (
            <div style={{ textAlign: "center", padding: "30px 16px" }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>📷</div>
              <div style={{ fontSize: 13, color: "var(--danger)", marginBottom: 16 }}>{error}</div>
              <button className="btn btn-secondary btn-sm" onClick={() => startScanner(cameras[camIdx]?.id ?? null)}>
                <RefreshCw size={13} /> Try Again
              </button>
            </div>
          ) : (
            <>
              {/* QR viewfinder */}
              <div style={{ position: "relative", borderRadius: 12, overflow: "hidden", background: "#000" }}>
                <div id={containerId} style={{ width: "100%", minHeight: 260 }} />
                {/* Corner overlay */}
                {ready && (
                  <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
                    {["0 0","0 auto auto 0","auto 0 0 auto","auto auto 0 0"].map((pos, i) => (
                      <div key={i} style={{
                        position: "absolute",
                        top:    [0,0,"auto","auto"][i],
                        left:   [0,"auto","auto",0][i],
                        right:  ["auto",0,0,"auto"][i],
                        bottom: ["auto","auto",0,0][i],
                        width: 28, height: 28,
                        borderTop:    [0,1,1,1][i] === 0 ? "none" : "3px solid var(--purple)",
                        borderBottom: [0,1,1,1][i] === 0 ? "none" : "3px solid var(--purple)",
                        borderLeft:   [0,0,1,1][i] === 0 ? "none" : "3px solid var(--purple)",
                        borderRight:  [0,0,0,1][i] === 0 ? "none" : "3px solid var(--purple)",
                        borderTopLeftRadius:     i === 0 ? 6 : 0,
                        borderTopRightRadius:    i === 1 ? 6 : 0,
                        borderBottomRightRadius: i === 2 ? 6 : 0,
                        borderBottomLeftRadius:  i === 3 ? 6 : 0,
                        margin: 16,
                      }} />
                    ))}
                  </div>
                )}
              </div>

              <p style={{ textAlign: "center", fontSize: 12, color: "var(--muted)", marginTop: 12, marginBottom: 8 }}>
                Hold the product QR code in view — it will scan automatically
              </p>

              {cameras.length > 1 && (
                <button className="btn btn-ghost btn-sm" style={{ width: "100%" }} onClick={switchCamera}>
                  <RefreshCw size={12} /> Switch Camera ({camIdx + 1}/{cameras.length})
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
