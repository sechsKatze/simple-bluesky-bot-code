import os
import re
import random
from datetime import datetime, timezone
import requests
from PIL import Image
import io

# 현재 UTC 타임스탬프를 ISO 8601 형식으로 반환
def now_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

# Bluesky 계정으로 로그인하여 JWT 토큰과 DID 값을 가져옴
def bluesky_login(handle, app_password):
# Bluesky 세션을 생성하고 accessJwt와 did를 반환
    print(f"[DEBUG] Bluesky 로그인 시도 - handle: {handle}")
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession",
        json={"identifier": handle, "password": app_password},
        headers={"Content-Type": "application/json"}
    )
    res.raise_for_status()
    return res.json()

# Bluesky에 새 게시물을 생성하는 API 호출
def create_record(jwt, repo, collection, record):
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={
            "Authorization": f"Bearer {jwt}",
            "Content-Type": "application/json"
        },
        json={
            "repo": repo,
            "collection": collection,
            "record": record
        }
    )
    res.raise_for_status()
    return res.json()

# 이미지를 JPEG 형식으로 압축하고 1MB 이하로 용량 조정
def compress_image(image_path, max_size=1024 * 1024):
# 이미지를 최대 max_size 이하로 압축하고 JPEG로 변환함. 해상도가 너무 클 경우 4096x4096 이내로 축소함.RGBA 또는 P 모드는 RGB로 변환하고, JPEG 품질을 점차 낮춰가며 압축
    print(f"[DEBUG] 이미지 압축 시작: {image_path}")
    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # 해상도 제한: 4096x4096
        max_dimensions = (4096, 4096)
        original_size = img.size
        img.thumbnail(max_dimensions, Image.Resampling.LANCZOS)
        if img.size != original_size:
            print(f"[DEBUG] 이미지 해상도 축소됨: {original_size} → {img.size}")

        quality = 70  # 품질을 70으로 설정하여 더 낮은 용량을 목표
        buffer = io.BytesIO()
        while True:
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format="JPEG", quality=quality)
            print(f"[DEBUG] 이미지 용량: {buffer.tell()} bytes, 품질: {quality}")
            if buffer.tell() <= max_size or quality < 30:
                break
            quality -= 5

        if buffer.tell() > max_size:
            print(f"[WARNING] 최종 이미지 용량이 여전히 {buffer.tell()} bytes로 커서 품질을 더 낮출 예정입니다.")

        buffer.seek(0)
        return buffer.read(), "image/jpeg"

# 압축된 이미지를 Bluesky 서버에 업로드하여 blob 참조를 생성
def upload_blob(jwt, image_bytes, mime_type="image/jpeg"):
    headers = {
        "Authorization": f"Bearer {jwt}",
        "Content-Type": "application/octet-stream",
    }
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.uploadBlob",
        headers=headers,
        data=image_bytes
    )
    res.raise_for_status()
    return res.json()["blob"]

# quotes 폴더에서 랜덤한 .txt 파일을 선택하고 제목과 내용을 반환
def load_random_work(quotes_dir="./quotes"):
    print(f"[DEBUG] 랜덤 텍스트 로드 시도 - 폴더: {quotes_dir}")
    files = [f for f in os.listdir(quotes_dir) if f.endswith(".txt")]
    if not files:
        return None, None
    chosen_file = random.choice(files)
    with open(os.path.join(quotes_dir, chosen_file), encoding="utf-8") as f:
        return chosen_file.replace(".txt", ""), f.read()

# 텍스트에서 이미지 파일명을 추출하여 텍스트/이미지 블록으로 분리
def split_lines_with_images(text):
    print("[DEBUG] 텍스트 내 이미지 블록 추출 시작")
    image_pattern = r'^(.*\.(jpg|jpeg|png|gif|webp))$'
    lines = text.splitlines()
    blocks = []
    buffer = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if re.match(image_pattern, line, re.IGNORECASE):
            if buffer:
                blocks.append({"type": "text", "content": buffer.strip()})
                buffer = ""
            blocks.append({"type": "image", "filename": line})
        else:
            buffer += line + "\n"
    if buffer:
        blocks.append({"type": "text", "content": buffer.strip()})
    return blocks

# 300자를 초과하지 않도록 텍스트를 블록 단위로 분할
def split_into_chunks(text, max_length=300):
    lines = text.splitlines()
    chunks = []
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 <= max_length:
            chunk += line + "\n"
        else:
            chunks.append(chunk.strip())
            chunk = line + "\n"
    if chunk:
        chunks.append(chunk.strip())
    return chunks

# 메인 실행 함수 - 텍스트 로드, 이미지 업로드, 게시물 생성까지 전체 수행
def main():
    print("[DEBUG] 메인 함수 시작")
    quotes_dir = "./quotes"
    work_title, content = load_random_work(quotes_dir)
    if not content:
        return {"status": "error", "message": "No content loaded"}

    parts = content.split('---')
    head_text = parts[0].strip() if len(parts) >= 1 else ""
    body = parts[1].strip() if len(parts) >= 2 else ""
    closing = parts[2].strip() if len(parts) == 3 else ""

    blocks = split_lines_with_images(body)

    handle = "계정명.bsky.social"
    app_password = os.environ.get("BLUESKY_APP_PASSWORD")
    if not app_password:
        return {"status": "error", "message": "Missing app password"}

    auth = bluesky_login(handle, app_password)
    print("[DEBUG] 로그인 성공, DID:", auth["did"])
    jwt = auth["accessJwt"]
    did = auth["did"]

    parent = None
    root = None
    prev_text = None

    if head_text:
        print("[DEBUG] 서두 텍스트 존재. 첫 포스트 생성.")
        post = {
            "$type": "app.bsky.feed.post",
            "text": head_text,
            "createdAt": now_timestamp(),
            "langs": ["ko"]
        }
        root = parent = create_record(jwt, repo=did, collection="app.bsky.feed.post", record=post)

    for block in blocks:
        print(f"[DEBUG] 블록 처리: {block['type']}")
        if block["type"] == "text":
            chunks = split_into_chunks(block["content"])
            for chunk in chunks:
                post = {
                    "$type": "app.bsky.feed.post",
                    "text": chunk,
                    "createdAt": now_timestamp(),
                    "langs": ["ko"]
                }
                if parent:
                    post["reply"] = {
                        "root": {"cid": root["cid"], "uri": root["uri"]},
                        "parent": {"cid": parent["cid"], "uri": parent["uri"]}
                    }
                parent = create_record(jwt, did, "app.bsky.feed.post", post)
                prev_text = chunk

        elif block["type"] == "image":
            image_path = os.path.join(quotes_dir, block["filename"])
            if os.path.exists(image_path):
                try:
                    print(f"[DEBUG] 이미지 파일 존재: {image_path}")
                    image_bytes, mime = compress_image(image_path)
                    print(f"[DEBUG] 이미지 압축 및 변환 완료: {block['filename']}")

                    blob = upload_blob(jwt, image_bytes, mime)
                    print(f"[DEBUG] 이미지 업로드 성공: {block['filename']}")

                    post_text = prev_text if prev_text and len(prev_text) <= 300 else f"📷 이미지: {block['filename']}"

                    image_entry = {
                        "alt": block["filename"],
                        "image": blob
                    }

                    # NSFW 라벨링 제거, 서버에 맡기도록 처리
                    post = {
                        "$type": "app.bsky.feed.post",
                        "text": post_text,
                        "createdAt": now_timestamp(),
                        "langs": ["ko"],
                        "embed": {
                            "$type": "app.bsky.embed.images",
                            "images": [image_entry]
                        }
                    }

                    if parent:
                        post["reply"] = {
                            "root": {"cid": root["cid"], "uri": root["uri"]},
                            "parent": {"cid": parent["cid"], "uri": parent["uri"]}
                        }

                    parent = create_record(jwt, did, "app.bsky.feed.post", post)
                    print(f"[DEBUG] 이미지 포함 포스트 업로드 완료: {block['filename']}")
                    prev_text = None
                except Exception as e:
                    print(f"⚠️ 이미지 업로드 실패: {block['filename']} ({e})")
                    continue

    if closing:
        post = {
            "$type": "app.bsky.feed.post",
            "text": closing,
            "createdAt": now_timestamp(),
            "langs": ["ko"]
        }
        if parent:
            post["reply"] = {
                "root": {"cid": root["cid"], "uri": root["uri"]},
                "parent": {"cid": parent["cid"], "uri": parent["uri"]}
            }
        parent = create_record(jwt, did, "app.bsky.feed.post", post)

    return {
        "status": "success",
        "message": f"Posted: {work_title} (text + images + closing)"
    }

# AWS Lambda에서 진입점 역할을 하는 핸들러 함수
def lambda_handler(event, context):
    print("[DEBUG] Lambda 핸들러 실행 시작")
    return main()
