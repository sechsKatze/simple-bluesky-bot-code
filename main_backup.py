# 백업용 구 버전 코드. 실행에 문제 없어요.
# 기존 기능(스레드 300자 분할, 이미지 업로드와 블스 규격에 맞는 최적화, URL 구현)만 있는 코드로 이것만 있어도 봇 기동에 문제없습니다. 

import os
import re
import random
from datetime import datetime, timezone
import requests
from PIL import Image
import io

# 현재 UTC 타임스탬프를 ISO 8601 형식으로 반환
def now_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") # 현재 시간을 UTC로 가져오고 마이크로초를 제거한 후 ISO 8601 형식으로 반환

# Bluesky 계정으로 로그인하여 JWT 토큰과 DID 값을 가져옴
def bluesky_login(handle, app_password):
    print(f"[DEBUG] Bluesky 로그인 시도 - handle: {handle}")
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession", # Bluesky 로그인 API 호출
        json={"identifier": handle, "password": app_password},
        headers={"Content-Type": "application/json"}
    )
    res.raise_for_status() # 오류 발생 시 예외를 발생시킴
    return res.json() # 로그인 후 JWT와 DID 값을 포함한 응답 반환

# Bluesky에 새 게시물을 생성하는 API 호출
def create_record(jwt, repo, collection, record):
    # JWT 토큰을 사용하여 게시물을 생성하는 API 호출
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.createRecord",
        headers={
            "Authorization": f"Bearer {jwt}", # 인증을 위한 JWT 토큰
            "Content-Type": "application/json"
        },
        json={
            "repo": repo, # 게시물의 레포지토리
            "collection": collection, # 게시물이 속할 컬렉션
            "record": record # 게시물 내용
        }
    )
    res.raise_for_status() # 오류 발생 시 예외를 발생시킴
    return res.json() # 생성된 게시물에 대한 응답 반환

# 이미지를 JPEG 형식으로 압축하고 1MB 이하로 용량 조정. 
# 해상도가 너무 클 경우 4096x4096 이내로 축소함.
# RGBA 또는 P 모드는 RGB로 변환하고, JPEG 품질을 점차 낮춰가며 압축
def compress_image(image_path, max_size=1024 * 1024):
    print(f"[DEBUG] 이미지 압축 시작: {image_path}")
    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB") # 이미지 모드가 RGBA 또는 P일 경우 RGB로 변환

        # 해상도 제한: 4096x4096
        max_dimensions = (4096, 4096)
        original_size = img.size
        img.thumbnail(max_dimensions, Image.Resampling.LANCZOS) # 이미지 축소
        if img.size != original_size:
            print(f"[DEBUG] 이미지 해상도 축소됨: {original_size} → {img.size}")

        quality = 70  # 품질을 70으로 설정하여 더 낮은 용량을 목표
        buffer = io.BytesIO() # 메모리 내 임시 버퍼
        while True:
            buffer.seek(0)
            buffer.truncate()
            img.save(buffer, format="JPEG", quality=quality) # 이미지 저장
            print(f"[DEBUG] 이미지 용량: {buffer.tell()} bytes, 품질: {quality}")
            if buffer.tell() <= max_size or quality < 30: # 용량이 1MB 이하로 되거나 품질이 30 미만일 경우 종료
                break
            quality -= 5 # 품질을 낮추어 다시 시도

        if buffer.tell() > max_size:
            print(f"[WARNING] 최종 이미지 용량이 여전히 {buffer.tell()} bytes로 커서 품질을 더 낮출 예정입니다.")

        buffer.seek(0)
        return buffer.read(), "image/jpeg" # 압축된 이미지 반환

# 압축된 이미지를 Bluesky 서버에 업로드하여 blob 참조를 생성
def upload_blob(jwt, image_bytes, mime_type="image/jpeg"):
    headers = {
        "Authorization": f"Bearer {jwt}", # 인증을 위한 JWT 토큰
        "Content-Type": "application/octet-stream", # 이미지 데이터 타입
    }
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.repo.uploadBlob", # Bluesky API 호출
        headers=headers,
        data=image_bytes # 이미지 바이트 데이터 전송
    )
    res.raise_for_status() # 오류 발생 시 예외를 발생시킴
    return res.json()["blob"] # 업로드된 이미지의 blob 참조 반환

# quotes 폴더에서 랜덤한 .txt 파일을 선택하고 제목과 내용을 반환
def load_random_work(quotes_dir="./quotes"):
    print(f"[DEBUG] 랜덤 텍스트 로드 시도 - 폴더: {quotes_dir}")
    files = [f for f in os.listdir(quotes_dir) if f.endswith(".txt")] # .txt 파일만 선택
    if not files:
        return None, None # 파일이 없으면 None 반환
    chosen_file = random.choice(files) # 랜덤으로 파일 선택
    with open(os.path.join(quotes_dir, chosen_file), encoding="utf-8") as f:
        return chosen_file.replace(".txt", ""), f.read() # 제목과 내용을 반환

# 텍스트에서 이미지 파일명을 추출하여 텍스트/이미지 블록으로 분리
def split_lines_with_images(text):
    print("[DEBUG] 텍스트 내 이미지 블록 추출 시작")
    image_pattern = r'^(.*\.(jpg|jpeg|png|gif|webp))$' # 이미지 파일 확장자 패턴
    lines = text.splitlines() # 텍스트를 줄 단위로 나눔
    blocks = [] # 최종적으로 반환할 블록 리스트
    buffer = "" # 텍스트를 임시로 저장할 버퍼

    # 각 줄을 순차적으로 처리
    for line in lines:
        line = line.strip() # 줄 앞뒤 공백 제거
        if not line: # 빈 줄은 무시
            continue
        if re.match(image_pattern, line, re.IGNORECASE): # 이미지 파일명인 경우
            if buffer.strip(): # 이전에 저장된 텍스트가 있다면
                blocks.append({"type": "text", "content": buffer.strip()}) # 이전 텍스트 블록 추가
                buffer = "" # 텍스트 블록을 추가 후 버퍼 초기화
            blocks.append({"type": "image", "filename": line})  # 이미지 블록 추가
        else:
            buffer += line + "\n" # 텍스트는 계속해서 버퍼에 저장
    if buffer.strip(): # 텍스트가 남아 있다면 블록에 추가
        blocks.append({"type": "text", "content": buffer.strip()}) # 마지막 텍스트 블록 추가
    return blocks

# 300자를 초과하지 않도록 텍스트를 블록 단위로 분할
def split_into_chunks(text, max_length=300):
    lines = text.splitlines()
    chunks = []
    chunk = ""
    for line in lines:
        if len(chunk) + len(line) + 1 <= max_length: # 텍스트가 max_length 이하인 경우
            chunk += line + "\n" 
        else:
            chunks.append(chunk.strip()) # 현재 블록을 chunks에 추가
            chunk = line + "\n" # 새로운 블록 시작
    if chunk:
        chunks.append(chunk.strip())  # 마지막 블록 추가
    return chunks

# 이 줄부터 메인 실행 함수 - 텍스트 로드, 이미지 업로드, 게시물 생성까지 전체 수행

# URL을 감지하여 Bluesky API에서 하이퍼링크 미리보기(facets)를 붙일 수 있도록 구조화된 리스트로 반환
def extract_facets(text):
    text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text) # 다양한 종류의 유니코드 공백 문자들을 일반 공백(' ')으로 통일
    text = text.replace('：', ':') # 전각 콜론(：)을 일반 콜론(:)으로 바꿔서 URL 인식에 방해되지 않도록 처리
    facets = []
    pattern = r'(https?://[^\s\)\]\}\<\>\"\']+)' # URL 패턴 정의: 괄호나 따옴표 등의 문자로 끝나지 않는 http/https 링크를 감지

    # 텍스트 내에서 패턴과 일치하는 URL을 반복적으로 찾아냄
    for match in re.finditer(pattern, text):
        start, end = match.start(), match.end()
        url = match.group(0)

        # Bluesky facets는 byte 위치를 요구하므로, UTF-8 기준으로 byte offset 계산
        byte_start = len(text[:start].encode('utf-8'))
        byte_end = len(text[:end].encode('utf-8'))
        print(f"[DEBUG] URL 감지됨: {url} (byteStart={byte_start}, byteEnd={byte_end})")

        # Bluesky에서 링크를 facets로 인식하게 만들기 위한 구조
        facets.append({
            "index": {
                "byteStart": byte_start,
                "byteEnd": byte_end
            },
            "features": [
                {
                    "$type": "app.bsky.richtext.facet#link", # 링크 타입 지정
                    "uri": url # 감지된 URL
                }
            ]
        })
    if facets:
        print(f"[DEBUG] 총 facets 생성됨: {len(facets)}개")
    else:
        print("[DEBUG] facets 없음 (URL 미감지)")
    return facets # URL 정보를 포함한 facets 리스트 반환

def main():
    print("[DEBUG] 메인 함수 시작")
    quotes_dir = "./quotes"
    work_title, content = load_random_work(quotes_dir) # 랜덤 텍스트 로드
    if not content:
        return {"status": "error", "message": "No content loaded"} # 내용이 없으면 오류 반환

    parts = content.split('---') # 내용 분리 (헤드, 본문, 클로징)
    head_text = parts[0].strip() if len(parts) >= 1 else ""
    body = parts[1].strip() if len(parts) >= 2 else ""
    closing = parts[2].strip() if len(parts) == 3 else ""

    blocks = split_lines_with_images(body) # 본문에서 이미지 블록 분리

    handle = "userID.bsky.social"
    app_password = os.environ.get("BLUESKY_APP_PASSWORD") # 환경변수에서 비밀번호 가져오기
    if not app_password:
        return {"status": "error", "message": "Missing app password"} # 비밀번호 없으면 오류 반환

    auth = bluesky_login(handle, app_password) # Bluesky 로그인
    print("[DEBUG] 로그인 성공, DID:", auth["did"])
    jwt = auth["accessJwt"]
    did = auth["did"]

    parent = None # 부모 포스트 초기화
    root = None # 루트 포스트 초기화
    prev_text = None # 이전 텍스트 저장 변수 초기화

    if head_text:
        print("[DEBUG] 서두 텍스트 존재. 첫 포스트 생성.")
        post = {
            "$type": "app.bsky.feed.post",
            "text": head_text,
            "createdAt": now_timestamp(),
            "langs": ["ko"]
        }
        root = parent = create_record(jwt, repo=did, collection="app.bsky.feed.post", record=post) # 첫 포스트 생성

    # 본문 블록 처리
    for block in blocks:
        print(f"[DEBUG] 블록 처리: {block['type']}")
        if block["type"] == "text":
            chunks = split_into_chunks(block["content"]) # 텍스트 블록을 작은 청크로 분할
            for chunk in chunks: 
                urls = re.findall(r'(https?://[^\s\)\]\}\<\>\"\']+)', chunk) # 텍스트 블록 안에서 URL을 추출
                post_text = re.sub(r'(https?://[^\s\)\]\}\<\>\"\']+)', '', chunk).strip() # 기존 텍스트에서 URL을 제거하고 정리 (URL이 중복되어 facets가 두 번 붙는 걸 방지하기 위함)
                
                # URL이 존재하면, 텍스트 말미에 줄바꿈으로 URL을 다시 추가 (미리보기 유도)
                if urls:
                    post_text += "\n\n" + "\n".join(urls)
                    
                facets = extract_facets(post_text) # 가공된 최종 텍스트에서 facets를 추출

                # Bluesky에 보낼 포스트 객체 구성
                post = {
                    "$type": "app.bsky.feed.post",
                    "text": post_text,
                    "createdAt": now_timestamp(),
                    "langs": ["ko"]
                }

                if facets: # facets가 감지되었다면 포스트에 추가하여 하이퍼링크 기능 활성화
                    post["facets"] = facets
                    print(f"[DEBUG] facets 포함됨 (chunk): {facets}")

                if parent: # 부모 포스트가 있으면 reply 정보 추가
                    post["reply"] = {
                        "root": {"cid": root["cid"], "uri": root["uri"]},
                        "parent": {"cid": parent["cid"], "uri": parent["uri"]}
                    }
                parent = create_record(jwt, did, "app.bsky.feed.post", post) # 텍스트 포스트 생성
                prev_text = chunk # 텍스트가 처리될 때 prev_text 갱신

        elif block["type"] == "image":
            image_path = os.path.join(quotes_dir, block["filename"]) # 이미지 파일 경로
            if os.path.exists(image_path):
                try:
                    print(f"[DEBUG] 이미지 파일 존재: {image_path}")
                    image_bytes, mime = compress_image(image_path) # 이미지 압축
                    print(f"[DEBUG] 이미지 압축 및 변환 완료: {block['filename']}")

                    blob = upload_blob(jwt, image_bytes, mime) # 이미지 블롭 업로드
                    print(f"[DEBUG] 이미지 업로드 성공: {block['filename']}")

                    # 이미지가 포함된 포스트에는 이미지 파일명만 사용하거나, 텍스트가 너무 길면 간단한 설명을 추가
                    post_text = f"📷 이미지: {block['filename']}"

                    image_entry = {
                        "alt": block["filename"],
                        "image": blob
                    }

                    # NSFW 라벨링 제거, 모더레이션 봇에게 맡기도록 처리
                    post = {
                        "$type": "app.bsky.feed.post",
                        "text": post_text,  # 이미지 설명만 포함
                        "createdAt": now_timestamp(),
                        "langs": ["ko"],
                        "embed": {
                            "$type": "app.bsky.embed.images",
                            "images": [image_entry]
                        }
                    }

                    if parent: # 부모 포스트가 있으면 reply 정보 추가
                        post["reply"] = {
                            "root": {"cid": root["cid"], "uri": root["uri"]},
                            "parent": {"cid": parent["cid"], "uri": parent["uri"]}
                        }

                    parent = create_record(jwt, did, "app.bsky.feed.post", post) # 이미지 포함 포스트 생성
                    print(f"[DEBUG] 이미지 포함 포스트 업로드 완료: {block['filename']}")
                    prev_text = None
                except Exception as e:
                    print(f"⚠️ 이미지 업로드 실패: {block['filename']} ({e})")
                    continue

    if closing:  # 클로징 텍스트가 있다면 추가
        post = {
            "$type": "app.bsky.feed.post",
            "text": closing,
            "createdAt": now_timestamp(),
            "langs": ["ko"]
        }
        if parent:  # 부모 포스트가 있으면 reply 정보 추가
            post["reply"] = {
                "root": {"cid": root["cid"], "uri": root["uri"]},
                "parent": {"cid": parent["cid"], "uri": parent["uri"]}
            }
        parent = create_record(jwt, did, "app.bsky.feed.post", post)  # 클로징 포스트 생성

    return {
        "status": "success",
        "message": f"Posted: {work_title} (text + images + closing)"
    }

# AWS Lambda에서 진입점 역할을 하는 핸들러 함수
def lambda_handler(event, context):
    print("[DEBUG] Lambda 핸들러 실행 시작")
    return main() # 메인 함수 실행
