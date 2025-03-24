#해당 코드는 수동으로 일일히 .zip로 압축하기 귀찮아하는 분을 위해 구현화한 코드입니다. AWS Lambda에서 필요한 폴더, 파일만 압축해줍니다. 
#압축 시 제외할 키워드와 확장자, 특정 파일은 예제입니다. 해당 코드에 기재된 키워드들은 제 PC에 맞추어져있기에 사용자 분의 PC 환경에 맞춰주세요.
# 사용법 : CMD(명령 프롬프트)나 Powersell을 열고 Python zip_builder.py나 py zip_builder.py를 입력하시고 엔터를 누르면 됩니다. 

import zipfile
import os

# 제외할 키워드 (폴더/경로에 포함되면 무조건 제외)
EXCLUDE_KEYWORDS = {
    "PIL", "python", "lambda_build_temp", "lambda_lib",
    "build", "build_temp", "bin", "tests", "__pycache__",
    "백업", "backup"
}

# 제외할 확장자
EXCLUDE_SUFFIX = {".dist-info", ".pyd"}

# 제외할 특정 파일
EXCLUDE_FILES = {"python.zip", "deployment.zip", "zip_python_layer.py", "zip_builder.py", "build_lambda_zip.py"}

def should_exclude(path: str) -> bool:
    path_parts = path.split(os.sep)
    
    # 키워드가 경로 중 하나에 포함되면 제외
    if any(keyword in path_parts for keyword in EXCLUDE_KEYWORDS):
        return True
    # 지정된 확장자로 끝나면 제외
    if any(path.endswith(suffix) for suffix in EXCLUDE_SUFFIX):
        return True
    # 특정 파일 이름과 일치하면 제외
    if any(path.endswith(file) for file in EXCLUDE_FILES):
        return True
    return False

def zip_dir_utf8(folder_path, zip_path):
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(folder_path):
            if should_exclude(root):
                continue
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, os.path.dirname(folder_path))
                if should_exclude(relative_path):
                    continue
                info = zipfile.ZipInfo(relative_path)
                info.flag_bits |= 0x800  # UTF-8 인코딩 지정
                with open(full_path, "rb") as f:
                    zipf.writestr(info, f.read())
                print(f"📦 추가됨: {relative_path}")

zip_dir_utf8(".", "deployment.zip")
print("✅ deployment.zip 생성 완료 (UTF-8 인코딩, 필요한 파일만 포함됨)")
