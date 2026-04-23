import { useCallback, useMemo, useState } from "react";
import UploadPage from "./pages/UploadPage";
import ScannerPage from "./pages/ScannerPage";
import useWebSocket from "./hooks/useWebSocket";
import "./styles/globals.css";

const WS_BASE = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws";

export default function App() {
  const [jobId, setJobId] = useState("");
  const [scanStep, setScanStep] = useState("");
  const [result, setResult] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [scannerView, setScannerView] = useState(false);
  const [scanError, setScanError] = useState("");
  const wsUrl = useMemo(() => (jobId ? `${WS_BASE}?job_id=${encodeURIComponent(jobId)}` : ""), [jobId]);

  const handleWsMessage = useCallback((payload) => {
    setScanStep(payload.step || "");
    if (payload.step === "complete") {
      setScanning(false);
      setScannerView(true);
    }
  }, []);

  useWebSocket(
    wsUrl,
    handleWsMessage,
    Boolean(jobId && scanning)
  );

  const handleScanStart = (_file, nextJobId) => {
    setJobId(nextJobId || "");
    setResult(null);
    setScanning(true);
    setScannerView(true);
    setScanError("");
    setScanStep("uploading");
  };

  const handleScanComplete = (response) => {
    setJobId(response.job_id);
    setResult(response.result);
    setScanning(false);
    setScannerView(true);
    setScanError("");
    setScanStep("complete");
  };

  const handleScanError = (message) => {
    setScanning(false);
    setScannerView(true);
    setScanError(message || "Scan failed");
    setScanStep("error");
  };

  const reset = () => {
    setResult(null);
    setScanning(false);
    setScannerView(false);
    setScanError("");
    setScanStep("");
  };

  return scannerView ? (
    <ScannerPage
      data={result}
      imageBase64={result?.preview_base64 || ""}
      mediaType={result?.media_type || "image/png"}
      scanning={scanning}
      scanStep={scanStep}
      onReset={reset}
      jobId={jobId}
      error={scanError}
    />
  ) : (
    <UploadPage onScanStart={handleScanStart} onScanComplete={handleScanComplete} onScanError={handleScanError} />
  );
}
