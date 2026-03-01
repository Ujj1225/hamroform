from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import StreamingResponse
from services import SERVICES
from processor import process_photo, process_signature, process_document
import io
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="HamroForm API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://hamroform.com",
        "https://www.hamroform.com",
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- PHOTO API ---------------- #


@app.post("/photo/process")
async def process_passport_photo(
    service_key: str = Form(...), 
    photo: UploadFile = File(...)
):
    if service_key not in SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service selected.")

    config = SERVICES[service_key]

    try:
        photo_bytes = await photo.read()

        processed = process_photo(
            image_bytes=photo_bytes,
            target_size=config["photo_size"],
            max_kb=config["photo_max_kb"],
        )

        return StreamingResponse(
            io.BytesIO(processed),
            media_type="image/jpeg",
            headers={"Content-Disposition": "attachment; filename=hamroform_photo.jpg"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- SIGNATURE API ---------------- #


@app.post("/signature/process")
async def process_sign(
    # max_kb: int = Form(...),
    signature: UploadFile = File(...),
):
    try:
        sig_bytes = await signature.read()

        processed = process_signature(
            image_bytes=sig_bytes
            # max_kb=max_kb
        )

        return StreamingResponse(
            io.BytesIO(processed),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "attachment; filename=hamroform_signature.jpg"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- CUSTOM PHOTO API ---------------- #


@app.post("/photo/process/custom")
async def process_custom_photo(
    width: int = Form(...), height: int = Form(...), photo: UploadFile = File(...)
):
    if width < 100 or height < 100:
        raise HTTPException(status_code=400, detail="Minimum size 100px required.")
    try:
        photo_bytes = await photo.read()

        processed = process_photo(
            image_bytes=photo_bytes, target_size=(width, height), max_kb=None
        )

        return StreamingResponse(
            io.BytesIO(processed),
            media_type="image/jpeg",
            headers={
                "Content-Disposition": "attachment; filename=hamroform_custom_photo.jpg"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- DOCUMENT API ---------------- #


@app.post("/document/process")
async def process_docs(service_key: str = Form(...), document: UploadFile = File(...)):
    if service_key not in SERVICES:
        raise HTTPException(status_code=400, detail="Invalid service selected.")

    config = SERVICES[service_key]

    try:
        doc_bytes = await document.read()

        processed, media_type = process_document(
            file_bytes=doc_bytes,
            filename=document.filename,
            max_kb=config["doc_max_kb"],
        )

        extension = "pdf" if media_type == "application/pdf" else "jpg"

        return StreamingResponse(
            io.BytesIO(processed),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=hamroform_document.{extension}"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------------- CUSTOM DOCUMENT API ---------------- #


@app.post("/document/process/custom")
async def process_custom_document(
    max_kb: int = Form(...), document: UploadFile = File(...)
):

    try:
        if max_kb < 5:
            raise HTTPException(status_code=400, detail="Minimum 5KB allowed.")
        doc_bytes = await document.read()

        processed, media_type = process_document(
            file_bytes=doc_bytes, filename=document.filename, max_kb=max_kb
        )

        extension = "pdf" if media_type == "application/pdf" else "jpg"

        return StreamingResponse(
            io.BytesIO(processed),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=hamroform_custom_document.{extension}"
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
