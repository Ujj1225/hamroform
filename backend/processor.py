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
    return compress_jpg(image_white, max_kb) if max_kb else None


# ---------------- SIGNATURE & DOCUMENT PROCESSORS ---------------- #


def process_signature(image_bytes: bytes) -> bytes:
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return image_bytes
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clean = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 25
    )
    inverted = cv2.bitwise_not(clean)
    horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_horizontal = cv2.morphologyEx(
        inverted, cv2.MORPH_OPEN, horiz_kernel, iterations=2
    )
    cnts_h = cv2.findContours(
        remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[0]
    for c in cnts_h:
        cv2.drawContours(inverted, [c], -1, (0, 0, 0), 5)

    vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    remove_vertical = cv2.morphologyEx(
        inverted, cv2.MORPH_OPEN, vert_kernel, iterations=2
    )
    cnts_v = cv2.findContours(
        remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )[0]
    for c in cnts_v:
        cv2.drawContours(inverted, [c], -1, (0, 0, 0), 5)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(inverted, kernel, iterations=2)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if contours:
        valid_cnts = [c for c in contours if cv2.contourArea(c) > 500]
        if valid_cnts:
            all_pts = np.concatenate(valid_cnts)
            x, y, w, h = cv2.boundingRect(all_pts)
            pad = 40
            y1, y2 = max(0, y - pad), min(clean.shape[0], y + h + pad)
            x1, x2 = max(0, x - pad), min(clean.shape[1], x + w + pad)

            final_output = clean[y1:y2, x1:x2]
        else:
            final_output = clean
    else:
        final_output = clean
    is_success, buffer = cv2.imencode(
        ".jpg", final_output, [int(cv2.IMWRITE_JPEG_QUALITY), 90]
    )
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
