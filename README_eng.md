This project’s code is distributed under CC0 (Creative Commons Zero v1.0 Universal).<br/>
A blog post that helped in creating the Bluesky bot - [Link](https://udaqueness.blog/2023/07/23/%ED%8C%8C%EC%9D%B4%EC%8D%AC%EC%9C%BC%EB%A1%9C-%EB%B8%94%EB%A3%A8%EC%8A%A4%EC%B9%B4%EC%9D%B4-%EB%B4%87-%EB%A7%8C%EB%93%A4%EA%B8%B0/)


# Bluesky Bot Project
**An automatic posting bot based on AWS Lambda + Python.**  
This project contains the code for a bot that automatically posts text and images to Bluesky. It provides thread creation in 300-character units, automatic image attachment, and size adjustment features.

## Key Features
- **Thread Creation**  
  Bluesky posts have a 300-character limit. This bot code automatically splits long text into threads for posting.

- **Automatic Image Attachment**  
  Place image files in the `quotes` folder, and the bot automatically uploads the corresponding image when its name is referenced in the text.

- **Image Resizing and Compression**  
  Bluesky only accepts images up to 2048px and 1MB in size. The bot uses the Pillow module to automatically resize and compress images.



## Requirements
- **Language**: Python  
- **Required Modules**
  - `atprototools` & `atprototools media`
  - `Pillow (PIL)`  
  → install :  
    ```bash
    pip install atprototools pillow
    ```
    ```bash
    pip install atprototools[media]
    ```

- **Essential Folders and Files**
  - `atprototools/` folder : Library for Bluesky login and media upload API
  - `quotes/` folder : Stores text and image files
  - `cacert.pem` File : SSL certificate bundle for HTTPS
  - `main.py` File : Lambda entry point and bot logic
 
- **Required Tools**
  - [Docker Desktop download link](https://www.docker.com/products/docker-desktop)
  - AWS CLI (Windows) - [64bit](https://awscli.amazonaws.com/AWSCLIV2.msi) / [32bit](https://awscli.amazonaws.com/AWSCLIV2-32bit.msi)

- **Integration Services** 
  - AWS Lambda
  - IAM (권한: `AllowPublishLayerVersion`, `AWSLambda_FullAccess`)  
  - AWS CloudWatch  

- **Environment Variables (Lambda)**
  - `BLUESKY_APP_PASSWORD`  
  - `BLUESKY_DID` <br/>
    did 코드 확인법 :
    ```bash
    https://bsky.social/xrpc/com.atproto.identity.resolveHandle?handle=자신의 블스 계정주소
    ```
  - `BLUESKY_HANDLE`

- **Compression Tools**:
  - `zip_builder.py` (반디집 사용도 가능하지만, 오류 방지를 위해 zip_builder.py 권장)
  - `zip_python_layer.py` (Docker로 생성한 Python 폴더를 압축하는 용도. 반디집으로도 대체 가능.)



## Docker Usage Guidelines
AWS Lambda에서는 Linux 전용 바이너리만 허용되기 때문에, 로컬(Windows/macOS)에서 pip install만 하면 작동하지 않습니다. 특히 from PIL import Image 구문이 작동하지 않는 오류가 발생할 수 있습니다. 그래서 Docker를 사용해 Amazon Linux 환경에서 Pillow를 설치해주는 과정이 필요합니다.

### 1. 왜 Docker를 쓰나요?
- 일반적인 설치(pip install pillow)는 Windows/macOS용 파일(.pyd, .so)을 포함함
- AWS Lambda는 Amazon Linux x86_64용 바이너리만 지원
- 그래서 Docker로 Amazon Linux 환경에서 전용 Pillow 패키지를 설치해야 함

### 2. 준비: Docker 설치
- Docker Desktop을 설치하고 실행
- 계정 생성은 권장 (이미지 다운로드 등에서 필요할 수 있음)
### 3. Docker 명령어 실행
- 터미널(cmd 또는 PowerShell)을 열고, 아래 명령어 입력 :
  ```bash
  docker run -v "%cd%:/var/task" public.ecr.aws/sam/build-런타임 설정:latest /bin/sh -c "pip install pillow -t python/lib/런타임 설정/site-packages"
  ```
- 참고
  - "%cd%"는 현재 경로를 Docker 컨테이너에 연결하는 명령어 (Windows 전용)
  - 런타임 설정 : Lambda에서 설정한 버전에 맞게 바꿔주세요 (예: python3.11 등)

### 4. 폴더 구조 확인
- 명령어 실행 후, 프로젝트 폴더 안에 다음과 같은 구조가 생성됩니다
- python/lib/Lambda에 설정한 런타임 함수/site-packages

### 5. 압축하기 (Python.zip 만들기)
- 반디집, 7-Zip 등 압축 프로그램 사용
- [zip_python_layer.py](https://github.com/sechsKatze/simple-bluesky-bot-code/blob/main/zip_python_layer.py) 같은 자동 압축 스크립트 사용.


## AWS CLI 사용 가이드라인
AWS Lambda에 이미지 라이브러리(Pillow 등)를 올리려면 AWS CLI를 사용해서 레이어(Layer)를 등록해야 합니다. 과정은 다음과 같습니다. 

### 1. AWS CLI가 필요한 이유
- Lambda에 **외부 라이브러리(Pillow 등)**를 추가하려면 ZIP 파일을 CLI로 업로드해야 함
- 터미널에서 aws 명령어를 쓸 수 있게 설치 및 설정 필요

### 2. IAM 사용자 만들기 & 권한 설정
- AWS 콘솔 → IAM 서비스로 이동
- 사용자(User) 생성 또는 기존 사용자 선택
- AWSLambdaFullAccess 권한 추가
  - "권한" → "권한 추가" → "기존 정책 연결" → AWSLambdaFullAccess 검색 후 추가
- Access Key 발급
  - “보안 자격 증명” 탭에서 Access Key ID, Secret Access Key 발급 (※ 메모장이던 어디던 무조건 메모 후 저장할 것!)

### 3. CLI 설정 (aws configure)
- 콘솔 명령(cmd 또는 PowerShell) 열고 "aws configure"을 입력
- 아래 순서대로 입력할 것
  - AWS Access Key ID
  - AWS Secret Access Key
  - Default region name → 예: ap-northeast-2 (서울)
  - Default output format → json를 주로 사용.

### 4. 에러가 발생할 때 (권한 부족 등)
- 레이어 등록 시 AccessDenied 오류가 나면 사용자에게 레이어 업로드 권한이 부족한 것!
- [AllowPublishLambdaLayer.json](https://github.com/sechsKatze/simple-bluesky-bot-code/blob/main/AllowPublishLayerVersion.json) 파일을 참고해서 직접 인라인 정책 추가하면 해결됨

### 5. 레이어 업로드 명령어
- 이미지 처리용 라이브러리(Pillow 등)가 담긴 python.zip 파일을 Lambda에 레이어로 올리는 명령어
 - CMD :
   ```bash
   aws lambda publish-layer-version ^ --layer-name pillow-layer ^ --zip-file "fileb://python.zip" ^ --compatible-runtimes 설정한 런타임
   ```
 - Powershell :
   ```bash
   aws lambda publish-layer-version --layer-name pillow-layer --zip-file "fileb://python.zip" --compatible-runtimes 설정한 런타임
   ```
