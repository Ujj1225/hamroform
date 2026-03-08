import io
import numpy as np
from PIL import Image, ImageEnhance, ImageOps
from rembg import remove, new_session
import cv2
import fitz

BG_SESSION = new_session("u2netp")

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)


def detect_face_crop(image):
    img_array = np.array(image)
    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(faces) == 0:
        return image

    (x, y, fw, fh) = max(faces, key=lambda b: b[2] * b[3])

    h, w, _ = img_array.shape
    crop_h = int(fh / 0.5)
    crop_w = int(crop_h * (35 / 45))

    center_x = x + fw // 2
    top_y = y - int(crop_h * 0.25)
    x_start = center_x - crop_w // 2
    y_start = top_y
    x_end = x_start + crop_w
    y_end = y_start + crop_h
    left_pad = max(0, -x_start)
    top_pad = max(0, -y_start)
    right_pad = max(0, x_end - w)
    bottom_pad = max(0, y_end - h)
    actual_x1, actual_y1 = max(0, x_start), max(0, y_start)
    actual_x2, actual_y2 = min(w, x_end), min(h, y_end)

    cropped_img = image.crop((actual_x1, actual_y1, actual_x2, actual_y2))
    if left_pad or top_pad or right_pad or bottom_pad:
        cropped_img = ImageOps.expand(
            cropped_img, (left_pad, top_pad, right_pad, bottom_pad), fill="white"
        )
    return cropped_img.resize((crop_w, crop_h), Image.Resampling.LANCZOS)


def force_white_background(image_rgba):
    if image_rgba.mode != "RGBA":
        image_rgba = image_rgba.convert("RGBA")
    white_bg = Image.new("RGBA", image_rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(white_bg, image_rgba).convert("RGB")


def compress_jpg(image, max_kb):
    """Universal compressor for photos and signatures"""
    target_bytes = max_kb * 1024
    for q in range(95, 5, -5):
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=q, optimize=True)
        if buf.tell() <= target_bytes:
            return buf.getvalue()
    scale = 0.8
    while scale > 0.3:
        new_size = (int(image.width * scale), int(image.height * scale))
        temp = image.resize(new_size, Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        temp.save(buf, format="JPEG", quality=20, optimize=True)
        if buf.tell() <= target_bytes:
            return buf.getvalue()
        scale -= 0.2
    return buf.getvalue()


def process_photo(image_bytes, target_size, max_kb):
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = detect_face_crop(image)
    image_no_bg = remove(image, session=BG_SESSION)
    image_white = force_white_background(image_no_bg)
    image_white = ImageEnhance.Sharpness(image_white).enhance(1.1)
    image_white = image_white.resize(target_size, Image.Resampling.LANCZOS)
    if max_kb:
        return compress_jpg(image_white, max_kb)
    buf = io.BytesIO()
    image_white.save(buf, format="JPEG", quality=95)
    return buf.getvalue()


# ---------------- SIGNATURE & DOCUMENT PROCESSORS ---------------- #


def process_signature(image_bytes: bytes, max_kb: int = 50) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return image_bytes

    # Resize large images (speed boost)
    h, w = img.shape[:2]
    if w > 1500:
        scale = 1500 / w
        img = cv2.resize(img, None, fx=scale, fy=scale)

    # grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # threshold (ink becomes white)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

    # -----------------------------
    # REMOVE NOTEBOOK LINES
    # -----------------------------
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_lines = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2
    )

    thresh = cv2.subtract(thresh, remove_lines)

    # clean noise
    kernel = np.ones((3, 3), np.uint8)
    thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel, iterations=2)

    # -----------------------------
    # FIND SIGNATURE
    # -----------------------------
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        sig = thresh
    else:
        # keep only reasonable contours
        contours = [c for c in contours if cv2.contourArea(c) > 150]

        if contours:
            pts = np.concatenate(contours)
            x, y, w, h = cv2.boundingRect(pts)

            pad = 15
            x1 = max(0, x - pad)
            y1 = max(0, y - pad)
            x2 = min(thresh.shape[1], x + w + pad)
            y2 = min(thresh.shape[0], y + h + pad)

            sig = thresh[y1:y2, x1:x2]
        else:
            sig = thresh

    # -----------------------------
    # WHITE BACKGROUND
    # -----------------------------
    final = np.ones_like(sig) * 255
    final[sig > 0] = 0

    # -----------------------------
    # COMPRESS UNDER 50KB
    # -----------------------------
    quality = 90
    while True:
        success, buffer = cv2.imencode(
            ".jpg", final, [int(cv2.IMWRITE_JPEG_QUALITY), quality]
        )
        if not success:
            break

        if len(buffer) <= max_kb * 1024 or quality <= 30:
            break

        quality -= 5

    return buffer.tobytes()


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
