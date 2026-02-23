import React, { useState, useEffect } from "react";
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
  nmc: "Medical Counci  l (NMC)",
  bar_council: "Bar Council (Law)",
  ssf: "Social Security (SSF)",
  ctevt: "CTEVT Entrance",
  online_account: "Online A/C (General)",
};

const THREE_DAYS = 3 * 24 * 60 * 60 * 1000;

const setWithExpiry = (key, value) => {
  const now = new Date().getTime();

  const item = {
    value,
    expiry: now + THREE_DAYS,
  };

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
  // const [selectedService, setSelectedService] = useState("standard_pp");
  const [selectedService, setSelectedService] = useState("");
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeMode, setActiveMode] = useState("");
  const [loading, setLoading] = useState(false);
  const [customWidth, setCustomWidth] = useState("");
  const [customHeight, setCustomHeight] = useState("");
  const [customDocSize, setCustomDocSize] = useState("");

  useEffect(() => {
    const savedWidth = getWithExpiry("customWidth");
    const savedHeight = getWithExpiry("customHeight");
    const savedDocSize = getWithExpiry("customDocSize");

    if (savedWidth) setCustomWidth(savedWidth);
    if (savedHeight) setCustomHeight(savedHeight);
    if (savedDocSize) setCustomDocSize(savedDocSize);
  }, []);

  // const handleDownload = (blob, filename) => {
  //   const url = window.URL.createObjectURL(blob);
  //   const a = document.createElement("a");
  //   a.href = url;
  //   a.download = filename;
  //   a.click();
  // };

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
  };
  // const handleProcess = async () => {
  //   if (!activeMode) {
  //     alert("Please select a processing type.");
  //     return;
  //   }

  //   if (!selectedService && activeMode !== "signature") {
  //     alert("Please select a service.");
  //     return;
  //   }

  //   if (!selectedFile) {
  //     alert("Please upload a file first.");
  //     return;
  //   }

  //   setLoading(true);

  //   try {
  //     let response;

  //     if (activeMode === "photo") {
  //       if (selectedService === "custom_pp") {
  //         if (!customWidth || !customHeight) {
  //           alert("Please enter width and height.");
  //           setLoading(false);
  //           return;
  //         }

  //         const formData = new FormData();
  //         formData.append("photo", selectedFile);
  //         formData.append("width", customWidth);
  //         formData.append("height", customHeight);

  //         response = await fetch("/photo/process/custom", {
  //           method: "POST",
  //           body: formData,
  //         });
  //         if (!response.ok) {
  //           throw new Error("Custom photo processing failed");
  //         }

  //         const blob = await response.blob();
  //         handleDownload(blob, "hamroform_custom_photo.jpg");
  //       } else {
  //         response = await processPhoto(selectedFile, selectedService);
  //         handleDownload(response.data, "hamroform_photo.jpg");
  //       }
  //     } else if (activeMode === "signature") {
  //       response = await processSignature(selectedFile);
  //       handleDownload(response.data, "hamroform_signature.jpg");
  //     } else if (activeMode === "document") {
  //       if (selectedService === "custom_doc") {
  //         if (!customDocSize) {
  //           alert("Please enter target size in KB.");
  //           setLoading(false);
  //           return;
  //         }

  //         const formData = new FormData();
  //         formData.append("document", selectedFile);
  //         formData.append("max_kb", customDocSize);

  //         const response = await processCustomDocument(
  //           selectedFile,
  //           customDocSize,
  //         );

  //         if (!response.ok) {
  //           throw new Error("Custom photo processing failed");
  //         }

  //         const blob = await response.blob();
  //         handleDownload(blob, "hamroform_custom_document");
  //       } else {
  //         response = await processDocument(selectedFile, selectedService);
  //         handleDownload(response.data, "hamroform_document");
  //         setSelectedFile(null);
  //         setCustomWidth("");
  //         setCustomHeight("");
  //         setCustomDocSize("");
  //       }
  //     }
  //   } catch (error) {
  //     alert("Processing failed.");
  //   }

  //   setLoading(false);
  // };

  const handleProcess = async () => {
    if (!activeMode) {
      alert("Please select a processing type.");
      return;
    }

    if (!selectedFile) {
      alert("Please upload a file first.");
      return;
    }

    if (!selectedService && activeMode !== "signature") {
      alert("Please select a service.");
      return;
    }

    setLoading(true);

    try {
      let response;

      if (activeMode === "photo") {
        if (selectedService === "custom_pp") {
          if (!customWidth || !customHeight) {
            alert("Please enter width and height.");
            setLoading(false);
            return;
          }

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
          if (!customDocSize) {
            alert("Please enter target size in KB.");
            setLoading(false);
            return;
          }

          response = await processCustomDocument(selectedFile, customDocSize);
        } else {
          response = await processDocument(selectedFile, selectedService);
        }
      }

      handleDownload(response.data, selectedFile);

      setSelectedFile(null);
      // setCustomWidth("");
      // setCustomHeight("");
      // setCustomDocSize("");
    } catch (error) {
      console.error(error);
      alert("Processing failed.");
    }

    setLoading(false);
  };
  return (
    <div className="container">
      <header className="header">
        <div className="logo-text">
          {/* <img src={logo} alt="logo" /> */}
          <img src={logo} alt="logo" className="logo" />
          <span className="hamro">Hamro</span>
          <span className="form">Form</span>
        </div>
        <div className="selection">
          <select
            value={selectedService}
            onChange={(e) => setSelectedService(e.target.value)}
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
        कुनै पनि सरकारी वा अन्य निकायका फारमहरु भर्नका लागि चाहिने फोटो,
        हस्ताक्षर तथा अन्य Documents हरुको Size, Pixel इत्यादी मिलाउनका लागि
        नेपालमै र नेपालकै लागि बनेको सजिलो, भरपर्दो र निशुल्क सेवा।
      </p>

      <div className="card">
        <div className="mode-buttons">
          <button
            className={activeMode === "photo" ? "active" : ""}
            onClick={() => setActiveMode(activeMode === "photo" ? "" : "photo")}
          >
            PP size photo
          </button>

          <button
            className={activeMode === "signature" ? "active" : ""}
            onClick={() =>
              setActiveMode(activeMode === "signature" ? "" : "signature")
            }
          >
            Process Signature
          </button>

          <button
            className={activeMode === "document" ? "active" : ""}
            onClick={() =>
              setActiveMode(activeMode === "document" ? "" : "document")
            }
          >
            Compress Document
          </button>
        </div>

        <div
          className="upload-box"
          onClick={() => document.getElementById("fileInput").click()}
        >
          <input
            id="fileInput"
            type="file"
            hidden
            onChange={(e) => setSelectedFile(e.target.files[0])}
          />
          {selectedFile ? (
            selectedFile.name
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
          disabled={loading}
        >
          {loading ? "Processing..." : "Download"}
        </button>
      </div>

      {/* <div className="ad-space">
        Banner Advertisement Space
      </div> */}

      <section className="info">
        <h2>About HamroForm</h2>
        <p className="bottom_subtitle">
          Fast, secure and compliant document processing platform for Nepal.
          Instantly resize passport photos, optimize signatures and compress
          documents to meet official submission requirements — all in seconds.
        </p>
      </section>
    </div>
  );
}
