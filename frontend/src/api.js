import axios from "axios";

const API = axios.create({
  baseURL: "http://3.110.136.143",
});

export const processPhoto = (file, serviceKey) => {
  const formData = new FormData();
  formData.append("service_key", serviceKey); 
  formData.append("photo", file);             
  return API.post("/photo/process", formData, {
    responseType: "blob",
  });
};

export const processSignature = (file) => {
  const formData = new FormData();
  formData.append("signature", file);         
  return API.post("/signature/process", formData, {
    responseType: "blob",
  });
};

// export const processCompressor = (file) => {
//     const formData = new FormData();
//     formData.append("signature", file);
//     return API.post("/signature/process", formData, {
//         responseType: "blob",
//     })
// }

export const processDocument = (file, serviceKey) => {
  const formData = new FormData();
  formData.append("service_key", serviceKey); 
  formData.append("document", file);          
  return API.post("/document/process", formData, {
    responseType: "blob",
  });
};

// export const processCustomDocument = (file, maxKb) => {
//   const formData = new FormData();
//   formData.append("document", file);
//   formData.append("max_kb", maxKb);

//   return API.post("/document/process/custom", formData, {
//     responseType: "blob",
//   });
// };

export const processCustomDocument = (file, maxKb) => {
  const formData = new FormData();
  formData.append("document", file);
  formData.append("max_kb", maxKb);

  return API.post("/document/process/custom", formData, {
    responseType: "blob",
  });
};

export const processCustomPhoto = (file, width, height) => {
  const formData = new FormData();
  formData.append("photo", file);
  formData.append("width", width);
  formData.append("height", height);

  return API.post("/photo/process/custom", formData, {
    responseType: "blob",
  });
};


