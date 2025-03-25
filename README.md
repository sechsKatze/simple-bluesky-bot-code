본 프로젝트에 사용되는 코드는 CC0(Creative Commons Zero v1.0 Universal)로 배포되고 있습니다. 

# 블루스카이 봇 프로젝트
이 프로젝트는 AWS Lambda와 연동된 파이썬 기반의 블루스카이(Bluesky) 봇을 구현하는 코드들을 정리한 것입니다. 주요 기능으로는 300자 단위의 스레드 생성, 폴더 내 이미지 자동 첨부, 이미지 크기 조정 및 압축 등이 있습니다.

## 주요 기능
- **스레드 생성**: 블루스카이의 포스트는 한 개당 300자로 제한되어 있습니다. 본 봇은 300자를 초과하는 내용을 자동으로 스레드 형태로 연결하여 게시합니다.
- **이미지 자동 첨부** : quotes 폴더 내에 이미지 파일 포맷과 이미지 파일을 넣으면 텍스트 안의 이미지 파일명을 읽어 이미지 파일을 업로드하는 기능입니다. 
- **이미지 크기 조정 및 압축** : 블루스카이는 2048px 이하, 1mg 이하의 이미지만을 허용합니다. 따라서 이미지가 너무 크거나 고용량이면 업로드에 실패할 수 있습니다. 해당 기능은 Pillow 모듈을 활용해 이미지의 크기와 용량을 자동으로 줄여 블루스카이의 규격에 맞게 업로드를 해줍니다. 

## 필요 사항
 * 파이썬 모듈 : atprototools (설치법 : 블루스카이 봇을 정리한 폴더 내에 CMD, Powershell로 "pip install atprototools"를 입력하고 엔터), PIL
 * 폴더 : quotes(봇에 구현할 텍스트와 이미지 파일을 넣는 폴더)
 * 프로그램 : Docker Desktop (AWS Lambda는 Linux x86_64용 바이너리만 허용하기 때문에 Window의 PIL과 연동되지 않음.즉 Docker로 빌드해서 연동해야 함.)
 * 연동 서비스 : AWS Lambda, IAM, CloudWatch
   - Lambda의 환경변수에 "BLUESKY_APP_PASSWORD", "BLUESKY_DID", "BLUESKY_HANDLE"은 추가할 것.
   - IAM에는 AllowPublishLayerVersion와 AWSLambda_FullAccess을 추가. 
 * 압축파일 생성 프로그램 : zip_builder.py (반디집으로 압축해도 상관없으나 에러가 날 확률이 있어 zip_builder.py를 추천함.)


