const STEP_LABELS = {
  validating: "Validating upload",
  uploading: "Uploading",
  rendering_pages: "Rendering pages",
  scanning: "Scanning with AI",
  complete: "Complete",
  error: "Error"
};

const ORDER = ["validating", "uploading", "rendering_pages", "scanning", "complete"];

export default function ScanProgress({ step }) {
  if (!step) return null;
  const currentIndex = ORDER.indexOf(step);
  return (
    <section className="panel">
      <p><b>Progress:</b> {STEP_LABELS[step] || step}</p>
      <div className="progressRow">
        {ORDER.map((s, idx) => {
          const done = currentIndex >= idx || step === "complete";
          const active = s === step;
          return (
            <div key={s} className={`progressNode ${done ? "done" : ""} ${active ? "active" : ""}`}>
              {STEP_LABELS[s]}
            </div>
          );
        })}
      </div>
    </section>
  );
}
