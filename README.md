본 프로젝트에 사용되는 코드는 CC0(Creative Commons Zero v1.0 Universal)로 배포되고 있습니다. 

---

# 블루스카이 봇 프로젝트
**AWS Lambda + Python 기반의 자동 포스팅 봇**  
이 프로젝트는 블루스카이(Bluesky)에 자동으로 텍스트와 이미지를 포스팅하는 봇의 코드 모음입니다. 300자 단위 스레드 생성, 이미지 자동 첨부 및 사이즈 조정 기능을 제공합니다.

## 주요 기능
- **스레드 생성**  
  블루스카이의 포스트는 300자 제한이 있습니다. 이 봇의 코드는 긴 텍스트를 자동으로 분할하여 스레드 형태로 게시합니다.

- **이미지 자동 첨부**  
  `quotes` 폴더에 이미지 파일을 넣고, 텍스트 내에서 이미지 이름을 호출하면 해당 이미지를 자동으로 업로드합니다.

- **이미지 크기 조정 및 압축**  
  블루스카이는 2048px 이하 / 1MB 이하 이미지만 업로드됩니다.  
  Pillow 모듈을 사용하여 자동으로 크기와 용량을 조절합니다.

---

## 필요 사항
- **언어**: Python  
- **필수 모듈**:  
  - `atprototools`  
  - `Pillow (PIL)`  
  → 설치:  
    ```bash
    pip install atprototools pillow
    ```

- **폴더 구조**:  
  - `quotes/` 폴더: 텍스트 및 이미지 파일 저장

- **연동 서비스**:  
  - AWS Lambda  
  - IAM (권한: `AllowPublishLayerVersion`, `AWSLambda_FullAccess`)  
  - AWS CloudWatch  

- **환경변수 설정 (Lambda)**:  
  - `BLUESKY_APP_PASSWORD`  
  - `BLUESKY_DID`  
  - `BLUESKY_HANDLE`

- **압축용 툴**:  
  - `zip_builder.py` (반디집 사용도 가능하지만, 오류 방지를 위해 zip_builder.py 권장)
  - 'zip_python_layer.py' (Docker로 생성한 Python 폴더를 압축하는 용도. 반디집으로도 대체 가능.)

--- 

## Docker 사용 가이드라인
AWS Lambda에서는 Linux 전용 바이너리만 허용되기 때문에, 로컬(Windows/macOS)에서 pip install만 하면 작동하지 않습니다. 특히 from PIL import Image 구문이 작동하지 않는 오류가 발생할 수 있습니다. 그래서 Docker를 사용해 Amazon Linux 환경에서 Pillow를 설치해주는 과정이 필요합니다.

### 1. 왜 Docker를 쓰나요?
- 일반적인 설치(pip install pillow)는 Windows/macOS용 파일(.pyd, .so)을 포함함
- AWS Lambda는 Amazon Linux x86_64용 바이너리만 지원
- 그래서 Docker로 Amazon Linux 환경에서 전용 Pillow 패키지를 설치해야 함

### 2. 준비: Docker 설치
- [Docker Desktop](https://www.docker.com/products/docker-desktop)을 설치하고 실행
- 계정 생성은 권장 (이미지 다운로드 등에서 필요할 수 있음)
### 3. Docker 명령어 실행
- 터미널(cmd 또는 PowerShell)을 열고, 아래 명령어 입력
  -- docker run -v "%cd%:/var/task" public.ecr.aws/sam/build-런타임 설정:latest /bin/sh -c "pip install pillow -t python/lib/python3.12/site-packages"
- 참고
  -- "%cd%"는 현재 경로를 Docker 컨테이너에 연결하는 명령어 (Windows 전용)
  -- 런타임 설정 Lambda에서 설정한 버전에 맞게 바꿔주세요 (예: python3.11,  등)

### 4. 폴더 구조 확인
- 명령어 실행 후, 프로젝트 폴더 안에 다음과 같은 구조가 생성됩니다
- python/lib/Lambda에 설정한 런타임 함수/site-packages

### 5. 압축하기 (Python.zip 만들기)
- 반디집, 7-Zip 등 압축 프로그램 사용
- zip_python_layer.py 같은 자동 압축 스크립트 사용 (코드는 적었습니다.)

--- 
## AWS CLI 사용법
 * AWS CLI가 필요한 이유 : aws lambda에 레이어를 등록하려면 AWS CLI가 필요함. 콘솔에 입력시 aws를 인식하게 해줌.
 * IAM에 들어가 AWS CLI에 사용해야 하는 AWS Access Key ID와 Secret Access Key를 발급.
 * IAM 사용자에 들어가 권한(Permissions) → 정책 추가(Add permissions) → 기존 정책 직접 연결 → 검색창에 "AWSLambdaFullAccess"를 입력 후 권한 추가.
 * 콘솔 명령창을 열어 aws configure를 입력. AWS Access Key ID와 AWS Secret Access Key, Default region name, Default output format를 입력.
 * 실패 시 : 권한 부족 때문이므로 사용자 정의 인라인 정책을 추가해야 함. (등록법은 AllowPublishLambdaLayer.json을 참고할 것.)
 * 레이어 함수 추가 명령어 :
   - CMD : aws lambda publish-layer-version ^ --layer-name pillow-layer ^ --zip-file "fileb://python.zip" ^ --compatible-runtimes python3.12
   - Powershell : aws lambda publish-layer-version --layer-name pillow-layer --zip-file "fileb://python.zip" --compatible-runtimes python3.12


