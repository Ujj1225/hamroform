import React, { useState, useEffect, useCallback } from "react";
import {
  processPhoto,
  processSignature,
  processDocument,
  processCustomDocument,
  processCustomPhoto,
} from "./api";
import logo from "./assets/logo.png";

const SERVICES = {
  standard_pp: "Standard PP Size",
  custom_pp: "Custom PP Size",
  custom_doc: "Custom Compression (KB)",
  loksewa: "Lok Sewa (PSC)",
  neb: "NEB Grade 11/12",
  tu_entrance: "TU Entrance/Exam",
  passport: "e-Passport",
  pan_card: "PAN Card (IRD)",
  mec: "Medical Education (MEC)",
  noc: "No Objection (NOC)",
  nec: "Engineering Council (NEC)",
  nnc: "Nursing Council (NNC)",
  nmc: "Medical Council (NMC)",
  bar_council: "Bar Council (Law)",
  ssf: "Social Security (SSF)",
  ctevt: "CTEVT Entrance",
  online_account: "Online A/C (General)",
};

const THREE_DAYS = 3 * 24 * 60 * 60 * 1000;

const setWithExpiry = (key, value) => {
  const now = new Date().getTime();
  const item = { value, expiry: now + THREE_DAYS };
  localStorage.setItem(key, JSON.stringify(item));
};

const getWithExpiry = (key) => {
  const itemStr = localStorage.getItem(key);
  if (!itemStr) return null;
  const item = JSON.parse(itemStr);
  const now = new Date().getTime();
  if (now > item.expiry) {
    localStorage.removeItem(key);
    return null;
  }
  return item.value;
};

export default function App() {
  const [selectedService, setSelectedService] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeMode, setActiveMode] = useState("");
  const [loading, setLoading] = useState(false);
  const [customWidth, setCustomWidth] = useState("");
  const [customHeight, setCustomHeight] = useState("");
  const [customDocSize, setCustomDocSize] = useState("");
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const savedWidth = getWithExpiry("customWidth");
    const savedHeight = getWithExpiry("customHeight");
    const savedDocSize = getWithExpiry("customDocSize");
    if (savedWidth) setCustomWidth(savedWidth);
    if (savedHeight) setCustomHeight(savedHeight);
    if (savedDocSize) setCustomDocSize(savedDocSize);
  }, []);

  useEffect(() => {
    const savedService = getWithExpiry("selectedService");
    if (savedService) setSelectedService(savedService);
  }, []);

  useEffect(() => {
    const savedMode = getWithExpiry("activeMode");
    if (savedMode) setActiveMode(savedMode);
  }, []);

  const resetForm = useCallback(() => {
    setSelectedFile(null);

    const fileInput = document.getElementById("fileInput");
    if (fileInput) fileInput.value = "";
  }, []);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();

    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setSelectedFile(e.dataTransfer.files[0]);
    }
  };

  const handleDownload = (blob, originalFile) => {
    const extension = originalFile.name.split(".").pop();
    const filename = `hamroform.${extension}`;
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
    resetForm();
  };

  const handleProcess = async () => {
    if (loading) return;

    if (!activeMode) return alert("Please select a processing type.");
    if (!selectedFile) return alert("Please upload a file first.");
    if (!selectedService && activeMode !== "signature")
      return alert("Please select a service.");

    setLoading(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 90) return prev;
        return prev + Math.random() * 7;
      });
    }, 500);

    try {
      let response;

      if (activeMode === "photo") {
        if (selectedService === "custom_pp") {
          if (!customWidth || !customHeight)
            throw new Error("Please enter width and height.");
          response = await processCustomPhoto(
            selectedFile,
            customWidth,
            customHeight,
          );
        } else {
          response = await processPhoto(selectedFile, selectedService);
        }
      } else if (activeMode === "signature") {
        response = await processSignature(selectedFile);
      } else if (activeMode === "document") {
        if (selectedService === "custom_doc") {
          if (!customDocSize)
            throw new Error("Please enter target size in KB.");
          response = await processCustomDocument(selectedFile, customDocSize);
        } else {
          response = await processDocument(selectedFile, selectedService);
        }
      }

      setProgress(100);
      clearInterval(interval);

      handleDownload(response.data, selectedFile);
    } catch (error) {
      clearInterval(interval);
      alert(error.message || "Processing failed.");
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="container">
      <header className="header">
        <div className="logo-text">
          <img src={logo} alt="logo" className="logo" loading="lazy" />
          <span className="hamro">Hamro</span>
          <span className="form">Form</span>
        </div>
        <div className="selection">
          <select
            value={selectedService}
            disabled={loading}
            onChange={(e) => {
              setSelectedService(e.target.value);
              setWithExpiry("selectedService", e.target.value);
            }}
          >
            <option value="" disabled>
              Select Service
            </option>
            {Object.entries(SERVICES).map(([key, value]) => (
              <option key={key} value={key}>
                {value}
              </option>
            ))}
          </select>

          {activeMode === "photo" && selectedService === "custom_pp" && (
            <div className="custom-size-container">
              <input
                type="number"
                placeholder="Width (px)"
                value={customWidth}
                disabled={loading}
                onChange={(e) => {
                  setCustomWidth(e.target.value);
                  setWithExpiry("customWidth", e.target.value);
                }}
                className="custom-input"
              />
              <input
                type="number"
                placeholder="Height (px)"
                value={customHeight}
                disabled={loading}
                onChange={(e) => {
                  setCustomHeight(e.target.value);
                  setWithExpiry("customHeight", e.target.value);
                }}
                className="custom-input"
              />
            </div>
          )}

          {activeMode === "document" && selectedService === "custom_doc" && (
            <div className="custom-size-container single">
              <input
                type="number"
                placeholder="Target Size (KB)"
                value={customDocSize}
                disabled={loading}
                onChange={(e) => {
                  setCustomDocSize(e.target.value);
                  setWithExpiry("customDocSize", e.target.value);
                }}
                className="custom-input custom-input-size"
              />
            </div>
          )}
        </div>
      </header>

      <p className="subtitle">
        कुनै पनि सरकारी वा अन्य निकायका फारमहरु भर्नका लागि चाहिने फोटो, तथा
        अन्य Documents हरुको Size, Pixel इत्यादी मिलाउनका लागि नेपालमै र नेपालकै
        लागि बनेको सजिलो, भरपर्दो र निशुल्क सेवा।
      </p>

      <div className="card">
        <div className="mode-buttons">
          <button
            className={activeMode === "photo" ? "active" : ""}
            disabled={loading}
            onClick={() => {
              const mode = activeMode === "photo" ? "" : "photo";
              setActiveMode(mode);
              setWithExpiry("activeMode", mode);
            }}
          >
            PP size photo
          </button>

          <button
            className={activeMode === "document" ? "active" : ""}
            disabled={loading}
            onClick={() => {
              const mode = activeMode === "document" ? "" : "document";
              setActiveMode(mode);
              setWithExpiry("activeMode", mode);
            }}
          >
            Compress Document
          </button>
        </div>

        <div
          className={`upload-box ${loading ? "disabled-box" : ""} ${dragActive ? "drag-active" : ""}`}
          onClick={() =>
            !loading && document.getElementById("fileInput").click()
          }
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
          style={{ cursor: loading ? "not-allowed" : "pointer" }}
        >
          <input
            id="fileInput"
            type="file"
            hidden
            disabled={loading}
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
          {selectedFile ? (
            <span style={{ fontWeight: "bold" }}>{selectedFile.name}</span>
          ) : (
            <div className="upload-text">
              <div>Click here to upload a file</div>
              <div>कृपया फोटो वा फाइल अपलोड गर्नुहोस्</div>
            </div>
          )}
        </div>

        <button
          className="process-btn"
          onClick={handleProcess}
          disabled={loading || !selectedFile}
        >
          {loading ? `Processing ${Math.round(progress)}%` : "Download"}
        </button>
        {loading && (
          <div className="progress-bar-container">
            <div
              className="progress-bar"
              style={{ width: `${progress}%` }}
            ></div>
          </div>
        )}
      </div>

      <section className="info">
        <h2>About HamroForm</h2>
        <p className="bottom_subtitle">
          Fast, secure and compliant document processing platform for Nepal.
          Instantly resize passport photos, compress documents to meet official
          submission requirements — all in seconds.
        </p>
      </section>
    </div>
  );
}
