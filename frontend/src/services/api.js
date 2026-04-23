import axios from "axios";

const BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export async function scanDocument(file, jobId, options = {}) {
  const formData = new FormData();
  formData.append("file", file);
  const params = new URLSearchParams();
  if (jobId) params.set("job_id", jobId);
  if (options.pdfMode) params.set("pdf_mode", options.pdfMode);
  if (options.pdfPageLimit) params.set("pdf_page_limit", String(options.pdfPageLimit));
  const qs = params.toString();
  const target = qs ? `${BASE}/scan?${qs}` : `${BASE}/scan`;
  const res = await axios.post(target, formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000
  });
  return res.data;
}

export async function askQuestion(jobId, question) {
  const res = await axios.post(`${BASE}/ask?job_id=${encodeURIComponent(jobId)}`, { question });
  return res.data;
}
