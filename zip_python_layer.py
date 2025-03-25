# Docker를 사용하여 Lambda 호환 환경에서 PIL(Pillow) 설치 시 파일을 압축해야 하는데 Window에는 압축 명령어인 "zip -r python.zip python"를 사용할 수 없습니다. 
# 따라서 해당 코드는 AWS Lambda에 연동할 Docker로 생성한 python 폴더를 "python.zip" 으로 압축해주는 코드입니다. 
# 사용법은 CMD(명령 프롬프트)나 Powershell을 열고 "Python zip_python_layer.py" 나 "py zip_python_layer.py" 을 입력하고 엔터.

import zipfile
import os

def zip_dir(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, os.path.dirname(folder_path))
                zipf.write(full_path, arcname=relative_path)
                print(f"📦 추가됨: {relative_path}")

zip_dir("python", "python.zip")
print("✅ python.zip 압축 완료!")
