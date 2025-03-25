본 프로젝트에 사용되는 코드는 CC0(Creative Commons Zero v1.0 Universal)로 배포되고 있습니다. 

# 블루스카이 봇 프로젝트
이 프로젝트는 AWS Lambda와 연동된 파이썬 기반의 블루스카이(Bluesky) 봇을 구현하는 코드들을 정리한 것입니다. 주요 기능으로는 300자 단위의 스레드 생성, 폴더 내 이미지 자동 첨부, 이미지 크기 조정 및 압축 등이 있습니다.

## 주요 기능
- **스레드 생성**: 블루스카이의 포스트는 한 개당 300자로 제한되어 있습니다. 본 봇은 300자를 초과하는 내용을 자동으로 스레드 형태로 연결하여 게시합니다.
- **이미지 자동 첨부** : quotes 폴더 내에 이미지 파일 포맷과 이미지 파일을 넣으면 텍스트 안의 이미지 파일명을 읽어 이미지 파일을 업로드하는 기능입니다. 
- **이미지 크기 조정 및 압축** : 블루스카이는 2048px 이하, 1mg 이하의 이미지만을 허용합니다. 따라서 이미지가 너무 크거나 고용량이면 업로드에 실패할 수 있습니다. 해당 기능은 Pillow 모듈을 활용해 이미지의 크기와 용량을 자동으로 줄여 블루스카이의 규격에 맞게 업로드를 해줍니다. 

## 필요 사항
 * 언어 : 파이썬(Python) : 해당 프로젝트에 사용된 모든 프로그램, 코드의 언어는 파이썬으로 작성되었습니다. 
 * 파이썬 모듈 : atprototools (설치법 : 블루스카이 봇을 정리한 폴더 내에 CMD, Powershell로 "pip install atprototools"를 입력하고 엔터), PIL
 * 폴더 : quotes(봇에 구현할 텍스트와 이미지 파일을 넣는 폴더)
 * 설치 프로그램 : Docker Desktop, AWS CLI
 * 연동 서비스 : AWS Lambda, IAM, CloudWatch
   - Lambda의 환경변수에 "BLUESKY_APP_PASSWORD", "BLUESKY_DID", "BLUESKY_HANDLE"은 추가할 것.
   - IAM에는 AllowPublishLayerVersion와 AWSLambda_FullAccess을 추가. 
 * 압축파일 생성 프로그램 : zip_builder.py (반디집으로 압축해도 상관없으나 에러가 날 확률이 있어 zip_builder.py를 추천함.)

## Docker 사용법
 * Docker를 사용하는 이유 : AWS Lambda는 Linux x86_64용 바이너리만 허용하기 때문에 일반적인 pip 설치법인 "pip install pillow -t ." 명령어를 입력하면 .pyd(Windows용)과 .so(macOS용) 포함해 실행할 수 없게 되어 봇에 사용되는 main.py가 에러날 수 있음. 따라서 Docker를 사용해 Amazon Linux용 Pillow만을 빌드해 Lambda에 맞춰 실행할 수 있음.
 * Docker Desktop을 다운로드 받아 설치 후 실행. (계정 생성은 가능한 추천함.)
 * CMD, Powershell을 열어 「docker run -v "$PWD":/var/task public.ecr.aws/sam/build-python3.12:1.115.0-x86_64 /bin/sh -c "pip install pillow -t python/lib/python3.12/site-packages/; exit"」을 입력.
   - 「cd 파일 경로」를 입력하면 해당 파일 경로로 이동 가능.
 * Python 폴더(파일 내부는 python/lib/python3.12/site-packages)가 생성됨. 반디집이나 zip_python_layer.py를 사용해 Python.zip로 압축.
 * 콘솔에「aws lambda publish-layer-version --layer-name pillow-layer --zip-file "fileb://python.zip" --compatible-runtimes python3.12(Lambda에 설정한 런타임에 맞춰야 함!)」를 입력해 "pillow-layer"를 생성.

## AWS CLI 사용법
 * AWS CLI가 필요한 이유 : aws lambda에 레이어를 등록하려면 AWS CLI가 필요함. 콘솔에 입력시 aws를 인식하게 해줌. 
 * 레이어 함수 추가 명령어 :
   - CMD : aws lambda publish-layer-version ^ --layer-name pillow-layer ^ --zip-file "fileb://python.zip" ^ --compatible-runtimes python3.12
   - Powershell : aws lambda publish-layer-version --layer-name pillow-layer --zip-file "fileb://python.zip" --compatible-runtimes python3.12


