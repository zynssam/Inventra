// src/components/QRDisplay.jsx
// Renders a QR code for a product and provides a download button
import { useRef } from "react";
import { QRCodeSVG } from "qrcode.react";
import { Download, QrCode } from "lucide-react";

export function ProductQRCode({ sku, name, size = 160, showDownload = true }) {
  const ref = useRef(null);

  function download() {
    // Convert SVG to PNG and download
    const svg = ref.current?.querySelector("svg");
    if (!svg) return;

    const clone = svg.cloneNode(true);
    clone.style.background = "#ffffff";
    const data  = new XMLSerializer().serializeToString(clone);
    const blob  = new Blob([data], { type: "image/svg+xml" });
    const url   = URL.createObjectURL(blob);
    const a     = document.createElement("a");
    a.href      = url;
    a.download  = `inventra-qr-${sku}.svg`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
      <div ref={ref} style={{
        padding: 12, background: "#fff", borderRadius: 12,
        border: "1px solid var(--line)",
        boxShadow: "0 2px 12px #0002",
      }}>
        <QRCodeSVG
          value={sku}                          // encode the SKU — scanner decodes → lookup by SKU
          size={size}
          level="M"
          includeMargin={false}
          fgColor="#0f0f14"
          bgColor="#ffffff"
        />
      </div>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 12 }}>{name}</div>
        <div style={{ fontFamily: "monospace", fontSize: 11, color: "var(--muted)" }}>{sku}</div>
      </div>
      {showDownload && (
        <button className="btn btn-ghost btn-sm" onClick={download} style={{ fontSize: 11 }}>
          <Download size={12} /> Download QR
        </button>
      )}
    </div>
  );
}

// Small inline badge shown in product rows
export function QRBadge({ sku, name }) {
  return (
    <div style={{ position: "relative", display: "inline-block" }}>
      <div className="qr-badge-trigger" style={{
        cursor: "pointer", color: "var(--muted)",
        display: "flex", alignItems: "center", gap: 4, fontSize: 11,
        padding: "2px 6px", borderRadius: 6,
        border: "1px solid var(--line)",
        transition: "border-color 0.15s, color 0.15s",
      }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = "var(--purple)"; e.currentTarget.style.color = "var(--purple)"; }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = "var(--line)";   e.currentTarget.style.color = "var(--muted)"; }}
        onClick={e => {
          e.stopPropagation();
          const popup = e.currentTarget.nextSibling;
          popup.style.display = popup.style.display === "block" ? "none" : "block";
        }}
      >
        <QrCode size={11} /> QR
      </div>
      {/* Popup */}
      <div style={{
        display: "none", position: "absolute", zIndex: 200,
        top: "calc(100% + 8px)", left: "50%", transform: "translateX(-50%)",
        background: "var(--surface)", border: "1px solid var(--line)",
        borderRadius: 14, padding: 16, boxShadow: "0 12px 40px #00000080",
        minWidth: 200,
      }}
        onClick={e => e.stopPropagation()}
      >
        <div style={{ font: "700 11px Manrope", color: "var(--muted)", marginBottom: 10, textAlign: "center" }}>Product QR Code</div>
        <ProductQRCode sku={sku} name={name} size={140} />
      </div>
    </div>
  );
}
