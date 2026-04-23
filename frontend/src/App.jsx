import { useEffect, useRef, useState } from "react";
import { scanDocument, askQuestion } from "./services/api";
import ScanProgress from "./components/ScanProgress";
import "./styles/globals.css";

const WS_BASE = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws";

export default function App() {
  const [jobId, setJobId] = useState("");
  const [step, setStep] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const wsRef = useRef(null);
  const stepRef = useRef("");

  useEffect(() => {
    stepRef.current = step;
  }, [step]);

  useEffect(() => () => wsRef.current?.close(), []);

  const connectProgressSocket = (nextJobId, retriesLeft = 1) => {
    wsRef.current?.close();
    const ws = new WebSocket(`${WS_BASE}?job_id=${encodeURIComponent(nextJobId)}`);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStep(data.step || "");
        setScanMessage(data.message || "");
      } catch (_e) {}
    };
    ws.onclose = () => {
      if (retriesLeft > 0 && stepRef.current !== "complete" && stepRef.current !== "error") {
        setTimeout(() => connectProgressSocket(nextJobId, retriesLeft - 1), 500);
      }
    };
  };

  const onFile = async (file) => {
    if (!file) return;
    setError("");
    setAnswer("");
    setStep("uploading");
    const nextJobId = crypto.randomUUID();
    connectProgressSocket(nextJobId);
    try {
      const pdfMode = file.name.toLowerCase().endsWith(".pdf") ? "all_pages" : "first_page";
      const data = await scanDocument(file, nextJobId, { pdfMode, pdfPageLimit: 3 });
      setJobId(data.job_id);
      setResult(data.result);
      setStep("complete");
      setScanMessage("Document processed successfully.");
    } catch (e) {
      const apiError = e?.response?.data;
      setError(apiError?.error || "Scan failed");
      setStep("error");
      setScanMessage(apiError?.code || "scan_error");
    } finally {
      wsRef.current?.close();
    }
  };

  const onAsk = async () => {
    if (!jobId || !question.trim()) return;
    setError("");
    try {
      const data = await askQuestion(jobId, question.trim());
      setAnswer(data.answer);
    } catch (e) {
      setError(e?.response?.data?.error || "Question failed");
    }
  };

  return (
    <main className="app">
      <h1>VISIO</h1>
      <p className="muted">Multimodal document intelligence</p>

      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.bmp,.txt" onChange={(e) => onFile(e.target.files?.[0])} />
      <ScanProgress step={step} />
      {scanMessage && <p className="muted">{scanMessage}</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <section className="panel">
          <img alt="preview" src={`data:${result.media_type};base64,${result.preview_base64}`} />
          <p><b>Type:</b> {result.document_type}</p>
          <p><b>Summary:</b> {result.summary}</p>
          <p><b>Confidence:</b> {result.confidence}%</p>
          <p><b>Pages:</b> {result.processed_page_count} processed out of {result.page_count}</p>
        </section>
      )}

      {jobId && (
        <section className="panel">
          <input value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="Ask about this document..." />
          <button onClick={onAsk}>Ask</button>
          {answer && <p>{answer}</p>}
        </section>
      )}
    </main>
  );
}
