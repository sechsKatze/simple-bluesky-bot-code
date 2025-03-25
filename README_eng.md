This project’s code is distributed under CC0 (Creative Commons Zero v1.0 Universal).<br/>
This English page was created using ChatGPT's AI translation.<br/>
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
  - IAM (Permissions: `AllowPublishLayerVersion`, `AWSLambda_FullAccess`)  
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
  - `zip_builder.py` (Although Bandizip can be used, it is recommended to use zip_builder.py to avoid errors.)
  - `zip_python_layer.py` (It is used to compress the Python folder created by Docker. Bandizip can also be used as an alternative.)



## Docker Usage Guidelines
Since AWS Lambda only allows Linux-specific binaries, it will not work by simply running pip install on local machines (Windows/macOS). In particular, you may encounter errors such as from PIL import Image. Therefore, it is necessary to use Docker to install Pillow in an Amazon Linux environment.

### 1. Why use Docker?
- Regular installation (pip install pillow) includes files (.pyd, .so) for Windows/macOS.
- AWS Lambda only supports binaries for Amazon Linux x86_64.
- Therefore, Docker is required to install the Pillow package in an Amazon Linux environment.

### 2. Preparation: Install Docker
- Install and run Docker Desktop.
- Creating an account is recommended (it may be needed for downloading images, etc.).
  
### 3. Run Docker Command
- Open the terminal (cmd or PowerShell) and enter the following command :
  ```bash
  docker run -v "%cd%:/var/task" public.ecr.aws/sam/build-runtime-settings:latest /bin/sh -c "pip install pillow -t python/lib/runtime-settings/site-packages"
  ```
- Note
  - "%cd%" is the command to link the current directory to the Docker container (Windows only).
  - runtime-settings : should be replaced with the version set in Lambda (e.g., python3.11).

### 4. Check Folder Structure
- After running the command, the following folder structure will be created inside the project folder.
- python/lib/runtime-settings/site-packages

### 5. Compress (Create Python.zip)
- Use compression tools such as Bandizip, 7-Zip,
- or an automatic compression script like [zip_python_layer.py](https://github.com/sechsKatze/simple-bluesky-bot-code/blob/main/zip_python_layer.py).


## AWS CLI Usage Guidelines
To upload image libraries (such as Pillow) to AWS Lambda, you need to register a Layer using AWS CLI. The process is as follows.

### 1. Why is AWS CLI necessary?
- To add **external libraries (such as Pillow)** to Lambda, you need to upload a ZIP file using the CLI.
- AWS CLI must be installed and configured to use the aws command in the terminal.

### 2. Create an IAM User & Set Permissions
- Go to the AWS Console → IAM service.
- Create a new user or select an existing user.
- Add the AWSLambdaFullAccess permission
  - "Permissions" → "Add permissions" → "Attach existing policies" → Search for and add AWSLambdaFullAccess
- Issue an Access Key
  - In the "Security Credentials" tab, generate the Access Key ID and Secret Access Key (be sure to save them in a text file or somewhere secure!)

### 3. CLI Configuration (aws configure)
- Open the console (cmd or PowerShell) and enter aws configure.
- Enter the following information in order:
  - AWS Access Key ID
  - AWS Secret Access Key
  - Default region name → Example: ap-northeast-2 (Seoul)
  - Default output format → JSON is commonly used.

### 4. When an Error Occurs (e.g., Insufficient Permissions)
- If you encounter an AccessDenied error when registering the Layer, it means the user does not have permissions to upload layers.
- You can resolve this by manually adding the inline policy using the [AllowPublishLambdaLayer.json](https://github.com/sechsKatze/simple-bluesky-bot-code/blob/main/AllowPublishLayerVersion.json) file

### 5. Layer Upload Command
- To upload the python.zip file containing the image processing library (such as Pillow) as a Layer to Lambda, use the following command
 - CMD :
   ```bash
   aws lambda publish-layer-version ^ --layer-name pillow-layer ^ --zip-file "fileb://python.zip" ^ --compatible-runtimes set_runtime
   ```
 - Powershell :
   ```bash
   aws lambda publish-layer-version --layer-name pillow-layer --zip-file "fileb://python.zip" --compatible-runtimes set_runtime
   ```
