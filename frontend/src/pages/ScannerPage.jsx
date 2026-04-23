import ScannerViewport from "../components/ScannerViewport";
import DataPanel from "../components/DataPanel";
import DocumentStats from "../components/DocumentStats";
import ScanProgress from "../components/ScanProgress";
import VisioChat from "../components/VisioChat";

export default function ScannerPage({ data, imageBase64, mediaType, scanning, scanStep, onReset, jobId, error }) {
  return (
    <div className="scanner-shell">
      <div className="scanner-top">
        <h2 className="logo" style={{ margin: 0 }}>VISIO</h2>
        <button className="upload-btn" onClick={onReset}>NEW SCAN</button>
      </div>
      <ScanProgress currentStep={scanStep} visible={scanning} />
      {error && <div className="error">{error}</div>}
      {data && <DocumentStats data={data} />}
      <div className="scanner-grid">
        <ScannerViewport imageBase64={imageBase64} mediaType={mediaType} scanning={scanning} analysisData={data} />
        <DataPanel data={data} />
      </div>
      {data && <VisioChat jobId={jobId} />}
    </div>
  );
}
