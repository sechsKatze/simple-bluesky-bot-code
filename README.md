# KOR - 간단한 블루스카이 봇 코드
해당 코드는 AWS Lambda와 연동된 파이썬 기반 블루스카이 봇을 구현하는 코드입니다. 300자 기준으로 스레드를 생성하는 기능, 폴더에서 이미지를 자동으로 첨부하는 기능, 블루스카이의 규격에 맞게 이미지 크기 조정 및 압축하는 기능이 포함되어 있습니다.

## 해당 코드가 구현하는 기능들
### 스레드 기능
 * 블루스카이는 한 포스트 당 300자만 작성할 수 있습니다. 300자가 넘어가면 첫 번째 포스트의 밑에 두 번째 포스트가 작성되어 스레드 형태로 연결할 수 있습니다. 

### 이미지 첨부 기능
 * 해당 코드는 quotes 폴더 내에 이미지 파일 포맷과 이미지 파일을 넣으면 텍스트 안의 이미지 파일명을 읽어 이미지 파일을 업로드하는 기능입니다. 

### 이미지 리사이즈
 * 블루스카이는 2048px 이하, 1mg 이하의 이미지만을 허용합니다. 따라서 이미지가 너무 크거나 고용량이면 업로드에 실패할 수 있습니다. 해당 기능은 Pillow 모듈을 활용해 이미지의 크기와 용량을 자동으로 줄여 블루스카이의 규격에 맞게 업로드를 해줍니다. 

## 준비물
 * 파이썬 모듈 : atprototools
 * 폴더 : quotes(봇에 구현할 텍스트와 이미지 파일을 넣는 폴더)
 * 연동 서비스 : AWS Lambda, IAM, CloudWatch

---
# ENG - simple-bluesky-bot-code
This is a Python-based Bluesky bot code integrated with AWS Lambda. It includes a feature to create threaded posts based on 300 characters, automatic image attachment from a folder, and resizing and compressing images to meet Bluesky's requirements.
 


