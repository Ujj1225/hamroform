from PIL import Image
import numpy as np
import cv2
import io
import pymupdf
from rembg import remove
from PIL import ImageFilter, ImageEnhance


# ---------------- LOAD FACE MODEL (once globally) ---------------- #

face_net = cv2.dnn.readNetFromCaffe(
    "deploy.prototxt", "res10_300x300_ssd_iter_140000.caffemodel"
)


# ---------------- COMMON UTILITIES ---------------- #


def validate_resolution(image, min_width=400, min_height=400):
    if image.width < min_width or image.height < min_height:
        raise ValueError("Image resolution too low. Please upload a clearer image.")


import io
from PIL import Image


def compress_jpg(image, max_kb, max_dimension=1920):
    target_bytes = max_kb * 1024
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    low, high = 10, 95
    best = None

    while low <= high:
        mid = (low + high) // 2
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=mid, optimize=True)
        size = buffer.tell()

        if size <= target_bytes:
            best = buffer.getvalue()
            low = mid + 1
        else:
            high = mid - 1
    if not best:
        current_scale = 0.9
        while current_scale > 0.1:
            new_size = (
                int(image.width * current_scale),
                int(image.height * current_scale),
            )
            temp_img = image.resize(new_size, Image.Resampling.LANCZOS)
            buffer = io.BytesIO()
            temp_img.save(buffer, format="JPEG", quality=20, optimize=True)
            if buffer.tell() <= target_bytes:
                return buffer.getvalue()
            current_scale -= 0.2

        raise ValueError(
            "Image is too large to compress to target size even with extreme resizing."
        )

    return best


# ---------------- FACE DETECTION & ICAO CROP ---------------- #


def detect_face_crop(image):
    img = np.array(image)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    h, w = img_bgr.shape[:2]

    blob = cv2.dnn.blobFromImage(
        cv2.resize(img_bgr, (300, 300)), 1.0, (300, 300), (104.0, 177.0, 123.0)
    )

    face_net.setInput(blob)
    detections = face_net.forward()

    if detections.shape[2] == 0:
        raise ValueError("No face detected.")

    confidence = detections[0, 0, 0, 2]
    if confidence < 0.6:
        raise ValueError("Face detection confidence too low.")

    box = detections[0, 0, 0, 3:7] * np.array([w, h, w, h])
    x1, y1, x2, y2 = box.astype("int")

    face_height = y2 - y1

    crop_h = int(face_height / 0.70)
    crop_w = int(crop_h * (35 / 45))

    center_x = (x1 + x2) // 2
    eye_level = y1 + int(face_height * 0.40)
    top_y = int(eye_level - crop_h * 0.55)

    x_start = max(0, center_x - crop_w // 2)
    y_start = max(0, top_y)

    x_end = min(w, x_start + crop_w)
    y_end = min(h, y_start + crop_h)

    cropped = img[y_start:y_end, x_start:x_end]

    if cropped.size == 0:
        raise ValueError("Invalid face crop.")

    return Image.fromarray(cropped)


def force_white_background(image):
    image = image.convert("RGBA")
    img = np.array(image)

    rgb = img[:, :, :3]
    alpha = img[:, :, 3]

    white = np.full(rgb.shape, 255, dtype=np.uint8)
    mask = alpha > 200
    white[mask] = rgb[mask]

    return Image.fromarray(white, "RGB")


# ---------------- PHOTO PROCESSOR (UPGRADED) ---------------- #
def process_photo(image_bytes, target_size, max_kb):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    validate_resolution(image)

    image = detect_face_crop(image)
    image_no_bg = remove(image)
    image_white = force_white_background(image_no_bg)

    enhancer = ImageEnhance.Sharpness(image_white)
    image_white = enhancer.enhance(1.4)

    contrast = ImageEnhance.Contrast(image_white)
    image_white = contrast.enhance(1.05)

    image_white = image_white.resize(target_size, Image.LANCZOS)
    image_white = image_white.filter(ImageFilter.SHARPEN)

    if max_kb is None:
        buffer = io.BytesIO()
        image_white.save(buffer, format="JPEG", quality=95, dpi=(300, 300))
        return buffer.getvalue()

    return compress_jpg(image_white, max_kb)


# ---------------- SIGNATURE PROCESSOR ---------------- #


# def process_signature(image_bytes, target_size=(300, 120), max_kb=50):
#     img = Image.open(io.BytesIO(image_bytes)).convert("L")
#     img = ImageEnhance.Contrast(img).enhance(2.5)

#     img_np = np.array(img)

#     thresh = cv2.adaptiveThreshold(
#         img_np,
#         255,
#         cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
#         cv2.THRESH_BINARY_INV,
#         21,
#         15
#     )
#     kernel = np.ones((2, 2), np.uint8)
#     thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
#     thresh = cv2.dilate(thresh, kernel, iterations=1)
#     coords = cv2.findNonZero(thresh)
#     if coords is not None:
#         x, y, w, h = cv2.boundingRect(coords)
#         thresh = thresh[y:y+h, x:x+w]
#     black_ink_np = np.where(thresh > 0, 0, 255).astype(np.uint8)
#     sig = Image.fromarray(black_ink_np)
#     sig = sig.resize(target_size, Image.Resampling.LANCZOS)
#     final_sig = Image.new("RGB", sig.size, (255, 255, 255))
#     final_sig.paste(sig)

#     return compress_jpg(final_sig, max_kb)


def process_signature(image_bytes, target_size=(300, 120), max_kb=50):
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img_np = np.array(img)
    img_np = cv2.GaussianBlur(img_np, (3, 3), 0)
    _, thresh = cv2.threshold(
        img_np,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )
    if np.mean(thresh) < 127:
        thresh = cv2.bitwise_not(thresh)
    coords = cv2.findNonZero(255 - thresh)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        thresh = thresh[y:y+h, x:x+w]
    sig = Image.fromarray(thresh)
    sig = sig.resize(target_size, Image.Resampling.LANCZOS)
    final_sig = Image.new("RGB", sig.size, (255, 255, 255))
    final_sig.paste(sig)

    return compress_jpg(final_sig, max_kb)




# ---------------- DOCUMENT PROCESSOR ---------------- #


def process_document(file_bytes, filename, max_kb):
    ext = filename.lower().split(".")[-1]

    if ext in ["jpg", "jpeg", "png"]:
        image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
        return compress_jpg(image, max_kb), "image/jpeg"

    elif ext == "pdf":
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        output = io.BytesIO()
        doc.save(output, garbage=4, deflate=True, clean=True)
        if len(output.getvalue()) / 1024 <= max_kb:
            return output.getvalue(), "application/pdf"
        new_doc = pymupdf.open()
        num_pages = len(doc)
        target_kb_per_page = max_kb // num_pages

        for page in doc:
            pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5))
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            compressed_img_bytes = compress_jpg(img, target_kb_per_page)
            with pymupdf.open(stream=compressed_img_bytes, filetype="jpg") as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
                with pymupdf.open("pdf", pdf_bytes) as single_page_pdf:
                    new_doc.insert_pdf(single_page_pdf)
        final_output = io.BytesIO()
        new_doc.save(final_output)
        return final_output.getvalue(), "application/pdf"
