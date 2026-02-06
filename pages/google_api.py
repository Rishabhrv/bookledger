from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account
import io

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SERVICE_ACCOUNT_FILE = "service_account.json"

def upload_to_drive(file_bytes, filename, folder_id=None):
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype="application/octet-stream",
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id"
    ).execute()

    return file.get("id")
