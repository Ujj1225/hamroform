import io
import os
import cv2
import numpy as np
import pymupdf
from PIL import Image, ImageFilter, ImageEnhance
from rembg import remove, new_session

BG_SESSION = new_session("birefnet-general")

face_net = cv2.dnn.readNetFromCaffe(
    "deploy.prototxt", "res10_300x300_ssd_iter_140000.caffemodel"
)


def validate_resolution(image, min_width=400, min_height=400):
    if image.width < min_width or image.height < min_height:
        raise ValueError("Image resolution too low. Please upload a clearer image.")


def compress_jpg(image, max_kb, max_dimension=1920):
    target_bytes = max_kb * 1024
    if max(image.size) > max_dimension:
        image.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    low, high = 10, 95
    best = None

    while low <= high:
        mid = (low + high) // 2
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=mid, optimize=True, subsampling=0)
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
        raise ValueError("Image is too large to compress even with extreme resizing.")

    return best


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


def force_white_background(image_rgba):
    """
    Blends the transparent RGBA image onto a solid white canvas.
    """
    white_bg = Image.new("RGBA", image_rgba.size, (255, 255, 255, 255))
    # Alpha composite ensures smooth anti-aliased edges
    blended = Image.alpha_composite(white_bg, image_rgba)
    return blended.convert("RGB")


def process_photo(image_bytes, target_size, max_kb):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    validate_resolution(image)
    image = detect_face_crop(image)
    image_no_bg = remove(
        image,
        session=BG_SESSION,
        alpha_matting=True,
        alpha_matting_foreground_threshold=240,
        alpha_matting_background_threshold=10,
        alpha_matting_erode_size=10,
    )
    image_white = force_white_background(image_no_bg)
    enhancer = ImageEnhance.Sharpness(image_white)
    image_white = enhancer.enhance(1.1)
    image_white = image_white.resize(target_size, Image.Resampling.LANCZOS)
    if max_kb is None:
        buffer = io.BytesIO()
        image_white.save(buffer, format="JPEG", quality=98, subsampling=0)
        return buffer.getvalue()

    return compress_jpg(image_white, max_kb)


# ---------------- SIGNATURE & DOCUMENT PROCESSORS ---------------- #


def process_signature(image_bytes, target_size=(300, 120), max_kb=50):
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    img_np = np.array(img)
    img_np = cv2.GaussianBlur(img_np, (3, 3), 0)
    _, thresh = cv2.threshold(img_np, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    if np.mean(thresh) < 127:
        thresh = cv2.bitwise_not(thresh)

    coords = cv2.findNonZero(255 - thresh)
    if coords is not None:
        x, y, w, h = cv2.boundingRect(coords)
        thresh = thresh[y : y + h, x : x + w]

    sig = Image.fromarray(thresh)
    sig = sig.resize(target_size, Image.Resampling.LANCZOS)
    final_sig = Image.new("RGB", sig.size, (255, 255, 255))
    final_sig.paste(sig)

    return compress_jpg(final_sig, max_kb)


from PIL import Image, ImageOps
import fitz

def optimize_image(img_bytes, target_kb):
    img = Image.open(io.BytesIO(img_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    elif img.mode == "RGBA":
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg

    max_width = 1800
    if img.width > max_width:
        ratio = max_width / img.width
        new_height = int(img.height * ratio)
        img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

    quality = 90
    output = io.BytesIO()

    while quality >= 10:
        output.seek(0)
        output.truncate(0)

        img.save(
            output,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=2,  
        )

        if len(output.getvalue()) / 1024 <= target_kb:
            break

        quality -= 5

    return output.getvalue()


def process_document(file_bytes, filename, max_kb, iteration=0):
    ext = filename.lower().split(".")[-1]

    if ext in ["jpg", "jpeg", "png"]:
        return optimize_image(file_bytes, max_kb), "image/jpeg"

    elif ext == "pdf":
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        new_doc = fitz.open()

        buffer_factor = max(0.8 - (iteration * 0.1), 0.5)
        usable_kb = max_kb * buffer_factor
        target_per_page = usable_kb / len(doc)

        render_scale = max(2.0 - (iteration * 0.3), 1.0)

        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(render_scale, render_scale))
            temp_img_bytes = pix.tobytes("jpg")

            compressed_bytes = optimize_image(temp_img_bytes, target_per_page)

            new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
            new_page.insert_image(page.rect, stream=compressed_bytes)

        final_output = io.BytesIO()
        new_doc.save(final_output, garbage=4, deflate=True, clean=True)
        final_bytes = final_output.getvalue()

        if len(final_bytes) / 1024 > max_kb and iteration < 4:
            return process_document(file_bytes, filename, max_kb, iteration + 1)

        return final_bytes, "application/pdf"
