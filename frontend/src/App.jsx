import { useState } from "react";
import { scanDocument, askQuestion } from "./services/api";
import "./styles/globals.css";

const WS_BASE = process.env.REACT_APP_WS_URL || "ws://localhost:8000/ws";

export default function App() {
  const [jobId, setJobId] = useState("");
  const [step, setStep] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");

  const onFile = async (file) => {
    if (!file) return;
    setError("");
    setStep("uploading");
    const nextJobId = crypto.randomUUID();
    const ws = new WebSocket(`${WS_BASE}?job_id=${encodeURIComponent(nextJobId)}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setStep(data.step || "");
      } catch (_e) {}
    };
    try {
      const data = await scanDocument(file, nextJobId);
      setJobId(data.job_id);
      setResult(data.result);
      setStep("complete");
    } catch (e) {
      setError(e?.response?.data?.error || "Scan failed");
      setStep("error");
    } finally {
      ws.close();
    }
  };

  const onAsk = async () => {
    if (!jobId || !question.trim()) return;
    const data = await askQuestion(jobId, question.trim());
    setAnswer(data.answer);
  };

  return (
    <main className="app">
      <h1>VISIO</h1>
      <p className="muted">Multimodal document intelligence</p>

      <input type="file" accept=".pdf,.jpg,.jpeg,.png,.webp,.bmp,.txt" onChange={(e) => onFile(e.target.files?.[0])} />
      {step && <p>Step: {step}</p>}
      {error && <p className="error">{error}</p>}

      {result && (
        <section className="panel">
          <img alt="preview" src={`data:${result.media_type};base64,${result.preview_base64}`} />
          <p><b>Type:</b> {result.document_type}</p>
          <p><b>Summary:</b> {result.summary}</p>
          <p><b>Confidence:</b> {result.confidence}%</p>
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
