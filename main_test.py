# 추가 기능을 테스트 및 기록하는 테스트 코드.
# 디버깅 후 문제가 없으면 main.py에 반영하고 있음. 

import os
import re
import random
from datetime import datetime, timezone
import requests
from PIL import Image
import io
import json
import traceback

# 현재 UTC 타임스탬프를 ISO 8601 형식으로 반환
def now_timestamp():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z") # 현재 시간을 UTC로 가져오고 마이크로초를 제거한 후 ISO 8601 형식으로 반환

HANDLE_ENV = "BLUESKY_HANDLE"
APP_PASSWORD_ENV = "BLUESKY_APP_PASSWORD"

# Bluesky 계정으로 로그인하여 JWT 토큰과 DID 값을 가져옴
def bluesky_login():
    handle = os.environ.get(HANDLE_ENV)
    app_password = os.environ.get(APP_PASSWORD_ENV)

    if not handle or not app_password:
        raise ValueError("환경 변수에서 핸들이나 앱 비밀번호를 찾을 수 없습니다.")

    print(f"[DEBUG] Bluesky 로그인 시도 - handle: {handle}")
    res = requests.post(
        "https://bsky.social/xrpc/com.atproto.server.createSession", # Bluesky 로그인 API 호출
        json={"identifier": handle, "password": app_password},
        headers={"Content-Type": "application/json"}
    )
    res.raise_for_status() # 오류 발생 시 예외를 발생시킴
    return res.json() # 로그인 후 JWT와 DID 값을 포함한 응답 반환

def is_ignored_did(did):
    if not os.path.exists(IGNORED_DID_FILE):
        return False
    with open(IGNORED_DID_FILE, "r", encoding="utf-8") as f:
        return did.strip() in [line.strip() for line in f if line.strip()]


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

POSTS_DIR = "./quotes/posts"
REPLIES_DIR = "./quotes/replies"
REPLY_IMAGES_DIR = "./quotes/reply_images"

# 자동 포스트용 텍스트 로딩 (quotes/posts/)
def load_random_work():
    print(f"[DEBUG] 랜덤 텍스트 로드 시도 - 폴더: {POSTS_DIR}")
    files = [f for f in os.listdir(POSTS_DIR) if f.endswith(".txt")]
    if not files:
        return None, None
    chosen_file = random.choice(files)
    with open(os.path.join(POSTS_DIR, chosen_file), encoding="utf-8") as f:
        return chosen_file.replace(".txt", ""), f.read()

# 자동 멘션 텍스트 응답 로딩 (quotes/replies/)
def load_random_reply_chunk():
    print(f"[DEBUG] 랜덤 답변 텍스트 청크 로드 시도 - 폴더: {REPLIES_DIR}")
    files = [f for f in os.listdir(REPLIES_DIR) if f.endswith(".txt")]
    print(f"[DEBUG] 텍스트 파일 목록: {files}")

    if not files:
        print("[WARNING] 텍스트 응답용 파일 없음")
        return None

    chosen_file = random.choice(files)
    with open(os.path.join(REPLIES_DIR, chosen_file), encoding="utf-8") as f:
        content = f.read()

    # 본문만 추출 (--- 구분선 기준)
    parts = content.split('---')
    if len(parts) < 2:
        print("[WARNING] --- 구분선이 없어 본문만 사용")
        main_text = content
    else:
        main_text = parts[1].strip()  # 본문만 추출

    chunks = split_into_chunks(main_text)
    print(f"[DEBUG] 총 {len(chunks)}개 청크 추출됨")

    if not chunks:
        print(f"[WARNING] 청크 없음 (파일 이름: {chosen_file})")
        return None

    selected = random.choice(chunks)
    print(f"[DEBUG] 선택된 청크: {selected[:50]}...")
    return selected

# 자동 멘션 이미지 응답 로딩 (quotes/reply_images/)
def load_random_reply_image():
    print(f"[DEBUG] 랜덤 답변 이미지 로드 시도 - 폴더: {REPLY_IMAGES_DIR}")
    image_exts = (".jpg", ".jpeg", ".png", ".webp", ".gif")
    files = [f for f in os.listdir(REPLY_IMAGES_DIR) if f.lower().endswith(image_exts)]
    if not files:
        return None
    return os.path.join(REPLY_IMAGES_DIR, random.choice(files))

# 자동 멘션 텍스트 응답 로딩
def handle_mention(mention_text, root_cid, root_uri, parent_cid, parent_uri, jwt, did):
    print(f"[DEBUG] 멘션 처리 시작: '{mention_text}'")

    # NG 키워드 체크
    ng_message, ng_keyword = check_ng_category(mention_text)
    if ng_message:
        print(f"[INFO] NG 키워드 감지됨: '{ng_keyword}' → 거절 메시지 전송")
        post = {
            "$type": "app.bsky.feed.post",
            "text": ng_message,
            "createdAt": now_timestamp(),
            "langs": ["ko"],
            "reply": {
                "root": {"cid": root_cid, "uri": root_uri},
                "parent": {"cid": parent_cid, "uri": parent_uri}
            }
        }
        create_record(jwt, did, "app.bsky.feed.post", post)
        return

    # 자동 응답 분기
    req_type = classify_request(mention_text)
    print(f"[DEBUG] classify_request 결과: {req_type}") 
    if req_type == "reply_text":
        print("[DEBUG] reply_text 분기 진입")
        reply_text = load_random_reply_chunk()
        if reply_text:
            print(f"[DEBUG] 응답할 텍스트: {reply_text[:50]}...")
            post = {
                "$type": "app.bsky.feed.post",
                "text": reply_text,
                "createdAt": now_timestamp(),
                "langs": ["ko"],
                "reply": {
                    "root": {"cid": root_cid, "uri": root_uri},
                    "parent": {"cid": parent_cid, "uri": parent_uri}
                }
            }
            try:
                create_record(jwt, did, "app.bsky.feed.post", post)
                print("[DEBUG] 텍스트 포스트 전송 성공")
            except Exception as e:
                print(f"[ERROR] 텍스트 포스트 전송 실패: {e}")
        else:
            # fallback 응답
            post = {
                "$type": "app.bsky.feed.post",
                "text": "⚠️ 텍스트 응답이 현재 준비되어 있지 않습니다. 나중에 다시 시도해주세요.",
                "createdAt": now_timestamp(),
                "langs": ["ko"],
                "reply": {
                    "root": {"cid": root_cid, "uri": root_uri},
                    "parent": {"cid": parent_cid, "uri": parent_uri}
                }
            }
            create_record(jwt, did, "app.bsky.feed.post", post)
            print("[WARNING] 텍스트 응답 실패 - fallback 메시지 전송 완료")

    elif req_type == "reply_image":
        image_path = load_random_reply_image()
        if image_path and os.path.exists(image_path):
            try:
                image_bytes, mime = compress_image(image_path)
                blob = upload_blob(jwt, image_bytes, mime)
                post = {
                    "$type": "app.bsky.feed.post",
                    "text": "📷 요청하신 이미지를 첨부합니다.",
                    "createdAt": now_timestamp(),
                    "langs": ["ko"],
                    "embed": {
                        "$type": "app.bsky.embed.images",
                        "images": [{
                            "alt": os.path.basename(image_path),
                            "image": blob
                        }]
                    },
                    "reply": {
                        "root": {"cid": root_cid, "uri": root_uri},
                        "parent": {"cid": parent_cid, "uri": parent_uri}
                    }
                }
                create_record(jwt, did, "app.bsky.feed.post", post)
            except Exception as e:
                print(f"[ERROR] 이미지 응답 실패: {e}")

    elif req_type == "ambiguous":
        post = {
            "$type": "app.bsky.feed.post",
            "text": "⚠️ 텍스트와 이미지 요청이 동시에 감지되었습니다. 한 번에 하나씩 요청해주세요.",
            "createdAt": now_timestamp(),
            "langs": ["ko"],
            "reply": {
                "root": {"cid": root_cid, "uri": root_uri},
                "parent": {"cid": parent_cid, "uri": parent_uri}
            }
        }
        create_record(jwt, did, "app.bsky.feed.post", post)

# 블랙리스트 해제 멘션을 보내면 해당 계정은 블랙리스트에서 제거됨.
OWNER_DID = os.environ.get("BLUESKY_DID")

def remove_from_ignored_dids(target_did):
    if not os.path.exists(IGNORED_DID_FILE):
        return
    with open(IGNORED_DID_FILE, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip() and line.strip() != target_did]
    with open(IGNORED_DID_FILE, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

# 하루에 질문 10회 제한
MENTION_COUNT_FILE = "/tmp/mention_counts.json"

def track_mention_count(did):
    today = datetime.utcnow().strftime("%Y-%m-%d")
    data = {}
    if os.path.exists(MENTION_COUNT_FILE):
        with open(MENTION_COUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    if today not in data:
        data[today] = {}

    data[today][did] = data[today].get(did, 0) + 1

    with open(MENTION_COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data[today][did]

# 자동 맨션 기능
def process_mentions(auth):
    print("[DEBUG] Mentions 처리 시작")

    jwt = auth["accessJwt"]
    did = auth["did"]

    res = requests.get(
        "https://bsky.social/xrpc/app.bsky.notification.listNotifications",
        headers={"Authorization": f"Bearer {jwt}"},
        params={"limit": 50}
    )
    res.raise_for_status()
    notifications = res.json().get("notifications", [])

    for notif in notifications:
        if notif.get("reason") != "mention":
            continue

        cid = notif["cid"]
        if is_already_processed(cid):
            print(f"[INFO] 이미 처리된 멘션: {cid}")
            continue

        author = notif["author"]
        author_did = author["did"]
        uri = notif["uri"]
        text = notif.get("record", {}).get("text", "")

        if is_ignored_did(author_did):
            print(f"[INFO] 무시된 DID: {author_did}")
            mark_cid_processed(cid)
            continue

        ng_msg, ng_kw = check_ng_category(text)
        if ng_msg:
            log_ng_mention(cid, author_did, ng_kw, ng_msg, text)
            add_to_ignored_dids([author_did])
            handle_mention(text, cid, uri, cid, uri, jwt, did)
            mark_cid_processed(cid)
            continue

        if author_did == OWNER_DID and "블랙리스트 해제" in text:
            # 해제할 대상 추출 (예: "@wonguobot 블랙리스트 해제 @did:plc:xxxx")
                match = re.search(r"@([a-zA-Z0-9_.:-]+)", text)
                if match:
                    target_did = match.group(1)
                    remove_from_ignored_dids(target_did)
                    print(f"[INFO] 블랙리스트 해제됨: {target_did}")

                    # 블랙리스트 해제 알림 멘션도 여기서 함께 처리
                    if jwt and did:
                        post = {
                            "$type": "app.bsky.feed.post",
                            "text": f"✅ @{target_did} 블랙리스트에서 해제되었습니다.",
                            "createdAt": now_timestamp(),
                            "langs": ["ko"]
                        }
                        create_record(jwt, did, "app.bsky.feed.post", post)
                else:
                    print("[WARNING] 블랙리스트 해제 명령어는 있지만 대상 DID를 찾지 못함.")
                create_record(jwt, did, "app.bsky.feed.post", post)

        count = track_mention_count(author_did)
        if count > 10:
            print(f"[INFO] {author_did} - 하루 멘션 {count}회 초과 → 무시 목록 등록")
            add_to_ignored_dids([author_did])
            mark_cid_processed(cid)
            continue

        log_mention(cid, author_did, text)
        handle_mention(text, cid, uri, cid, uri, jwt, did)
        mark_cid_processed(cid)
        print(f"[DEBUG] 멘션 응답 완료: {cid} ({author['handle']})")

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

# 블루스카이 핸들 하이퍼링크 감지 기능 (+ DID 자동 변환)
def resolve_handle_to_did(handle):
    try:
        res = requests.get(
            "https://bsky.social/xrpc/com.atproto.identity.resolveHandle",
            params={"handle": handle}
        )
        res.raise_for_status()
        return res.json()["did"]
    except Exception as e:
        print(f"[ERROR] DID resolve 실패: {handle} ({e})")
        return None

# URL을 감지하여 Bluesky API에서 하이퍼링크 미리보기(facets)를 붙일 수 있도록 구조화된 리스트로 반환
def extract_facets(text):
    print("[DEBUG] extract_facets 시작")
    facets = []
    text = re.sub(r'[\u00A0\u2000-\u200B\u202F\u205F\u3000]', ' ', text)
    text = text.replace('：', ':')

    # URL 감지
    print("[DEBUG] URL 패턴 검사 시작")
    url_pattern = r'(https?://[^\s\)\]\}\<\>\"\']+)'
    for match in re.finditer(url_pattern, text):
        url = match.group(0)
        byte_start = len(text[:match.start()].encode("utf-8"))
        byte_end = len(text[:match.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{"$type": "app.bsky.richtext.facet#link", "uri": url}]
        })
        print(f"[DEBUG] URL 감지됨: {url} (byteStart={byte_start}, byteEnd={byte_end})")

    # 핸들 감지 및 DID 자동 변환
    print("[DEBUG] 핸들 패턴 검사 시작")
    mention_pattern = r'@([a-zA-Z0-9_.-]+\.bsky\.social)'
    for match in re.finditer(mention_pattern, text):
        handle = match.group(1)
        did = resolve_handle_to_did(handle)
        if not did:
            print(f"[WARNING] DID resolve 실패: {handle}")
            continue
        byte_start = len(text[:match.start()].encode("utf-8"))
        byte_end = len(text[:match.end()].encode("utf-8"))
        facets.append({
            "index": {"byteStart": byte_start, "byteEnd": byte_end},
            "features": [{
                "$type": "app.bsky.richtext.facet#mention",
                "did": did
            }]
        })
        print(f"[DEBUG] 멘션 감지됨: @{handle} (DID: {did}, byteStart={byte_start}, byteEnd={byte_end})")

    if facets:
        print(f"[DEBUG] 총 facets 생성됨: {len(facets)}개")
    else:
        print("[DEBUG] facets 없음 (URL/멘션 미감지)")
    return facets


# 2. 자동 멘션 응답 키워드 분기
def classify_request(text):
    image_keywords = ["이미지", "그림", "사진"]
    text_keywords = ["스크립트", "ss", "텍스트"]

    text = text.lower().replace("：", ":").strip()

    has_image_kw = any(k in text for k in image_keywords)
    has_text_kw = any(k in text for k in text_keywords)

    if has_image_kw and has_text_kw:
        return "ambiguous"  # 텍스트와 이미지 키워드가 모두 있으면 응답 생략
    elif has_image_kw:
        return "reply_image"
    elif has_text_kw:
        return "reply_text"
    else:
        return None

# 3. NG 키워드 감지 + 카테고리별 거절 + 블랙리스트 등록
# 커스텀이 가능합니다. 
NG_RULES = {
    "비공식 커플링 명칭": {
        "keywords": ["우가진×우오즈미", "우가진×웡", "우가우오", "우가웡", "JJ×우오즈미", "J우오즈미", "웡×JJ", "웡J", "비공식"],
        "messages": ["봇주는 오메르타 시리즈의 비공식 커플링 관련 주제를 거부하고 있습니다."]
    },
    "비속어 및 취향 비하": {
        "keywords": ["병신", "지랄", "좆", "이딴", "쓰레기", "씨발", "니미", "한남", "한녀", "한남충", "김치녀", "남미새", "여미새", "역겹", "토나와", "두창","왜 좋아해?", "왜 좋아하냐?"],
        "messages": [
            "저속한 표현은 삼가바랍니다.",
            "타인의 취향을 존중할 줄 아는 오타쿠가 되시길 바랍니다.",
            "불편하시면 뮤트나 차단 기능을 활용해주세요."
        ]
    },

    "다른 카린 게임 작품": {
        "keywords": ["단죄의 마리아", "오메가 뱀파이어", "절대미궁그림", "절대미궁", "절대미궁 비밀의 엄지공주", "프린세스 나이트메어", "아니마 문디"],
        "messages": ["본 봇은 오메르타 시리즈의 서브 커플링 웡우오 전용 팬봇입니다. 즉 카린 작품 통합 봇이 아닙니다."]
    }
}

IGNORED_DID_FILE = "/tmp/ignored_dids.txt"

def check_ng_category(text):
    for category, rule in NG_RULES.items():
        for kw in rule["keywords"]:
            if kw in text:
                return random.choice(rule["messages"]), kw
    return None, None


def log_ng_mention(cid, author_did, keyword, message, text):
    with open("/tmp/ng_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}Z] CID: {cid} | Author: {author_did}\n")
        f.write(f"Keyword: '{keyword}' | Message: '{message}'\n")
        f.write(f"Text: {text}\n\n")

def log_mention(cid, author_did, text):
    with open("/tmp/mention_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}Z] CID: {cid} | Author: {author_did}\n")
        f.write(f"Text: {text}\n\n")

def add_to_ignored_dids(new_dids):
    current = set()
    if os.path.exists(IGNORED_DID_FILE):
        with open(IGNORED_DID_FILE, "r", encoding="utf-8") as f:
            current = set(line.strip() for line in f if line.strip())

    with open(IGNORED_DID_FILE, "a", encoding="utf-8") as f:
        for did in new_dids:
            if did not in current:
                f.write(did + "\n")
                print(f"[INFO] 무시 대상 등록됨: {did}")

# 이미 처리한 멘션이면 skip
PROCESSED_CID_FILE = "/tmp/processed_cids.txt"

def is_already_processed(cid):
    if not os.path.exists(PROCESSED_CID_FILE):
        return False
    with open(PROCESSED_CID_FILE, "r", encoding="utf-8") as f:
        return cid in [line.strip() for line in f if line.strip()]

def mark_cid_processed(cid):
    with open(PROCESSED_CID_FILE, "a", encoding="utf-8") as f:
        f.write(cid + "\n")


def main(auth):
    print("[DEBUG] 메인 함수 시작")
    work_title, content = load_random_work()
    if not content:
        return {"status": "error", "message": "No content loaded"}

    parts = content.split('---')
    head_text = parts[0].strip() if len(parts) >= 1 else ""
    body = parts[1].strip() if len(parts) >= 2 else ""
    closing = parts[2].strip() if len(parts) == 3 else ""

    blocks = split_lines_with_images(body)

    jwt = auth["accessJwt"]
    did = auth["did"]

    if head_text:
        print("[DEBUG] 서두 텍스트 존재. 첫 포스트 생성.")
        post = {
            "$type": "app.bsky.feed.post",
            "text": head_text,
            "createdAt": now_timestamp(),
            "langs": ["ko"]
        }
        root = parent = create_record(jwt, repo=did, collection="app.bsky.feed.post", record=post)

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
            image_path = os.path.join(POSTS_DIR, block["filename"]) # 이미지 파일 경로
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
    try:
        auth = bluesky_login()
        process_mentions(auth)
        return main(auth)
    except Exception as e:
        print(f"[ERROR] Lambda 전체 처리 중 오류: {e}")
        traceback.print_exc()
        return {"status": "error", "message": str(e)}
