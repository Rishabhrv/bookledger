# import streamlit as st
# from googleapiclient.discovery import build
# from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
# from google_auth_oauthlib.flow import InstalledAppFlow
# from google.auth.transport.requests import Request
# import io
# import os
# import pickle

# # Scopes for full Drive access
# SCOPES  = st.secrets["google_drive"]["SCOPES"]
# CLIENT_SECRETS_FILE  = st.secrets["google_drive"]["CLIENT_SECRETS_FILE"]
# TOKEN_FILE  = st.secrets["google_drive"]["TOKEN_FILE"]

# def get_drive_service():
#     """Authenticates the user and returns the Drive service object."""
#     creds = None
#     # The file token.pickle stores the user's access and refresh tokens
#     if os.path.exists(TOKEN_FILE):
#         with open(TOKEN_FILE, 'rb') as token:
#             creds = pickle.load(token)
    
#     # If there are no (valid) credentials available, let the user log in.
#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             try:
#                 creds.refresh(Request())
#             except Exception:
#                 creds = None
        
#         if not creds:
#             if not os.path.exists(CLIENT_SECRETS_FILE):
#                 st.error(f"Error: '{CLIENT_SECRETS_FILE}' not found. Please download OAuth 2.0 Client ID (Desktop App) from GCP Console and rename it to 'credentials.json'.")
#                 return None
            
#             # Using run_local_server for a seamless browser-based login
#             flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
#             creds = flow.run_local_server(port=0)
        
#         # Save the credentials for the next run
#         with open(TOKEN_FILE, 'wb') as token:
#             pickle.dump(creds, token)

#     return build("drive", "v3", credentials=creds)

# def upload_to_drive(file_bytes, filename, folder_id=None):
#     """Uploads a file to Google Drive."""
#     service = get_drive_service()
#     if not service: return None

#     file_metadata = {"name": filename}
#     if folder_id:
#         file_metadata["parents"] = [folder_id]

#     media = MediaIoBaseUpload(
#         io.BytesIO(file_bytes),
#         mimetype="application/octet-stream",
#         resumable=True,
#     )

#     try:
#         file = service.files().create(
#             body=file_metadata,
#             media_body=media,
#             fields="id"
#         ).execute()
#         return file.get("id")
#     except Exception as e:
#         st.error(f"Upload Error: {e}")
#         return None

# def list_files_in_drive(folder_id=None):
#     """Lists files in a specific folder or root."""
#     service = get_drive_service()
#     if not service: return []

#     query = "trashed = false"
#     if folder_id:
#         query = f"'{folder_id}' in parents and trashed = false"

#     try:
#         results = service.files().list(
#             q=query,
#             pageSize=20, 
#             fields="nextPageToken, files(id, name)"
#         ).execute()
#         return results.get("files", [])
#     except Exception as e:
#         st.error(f"Listing Error: {e}")
#         return []

# def download_from_drive(file_id, filename):
#     """Downloads a file from Google Drive."""
#     service = get_drive_service()
#     if not service: return None

#     try:
#         request = service.files().get_media(fileId=file_id)
#         file_stream = io.BytesIO()
#         downloader = MediaIoBaseDownload(file_stream, request)
#         done = False
#         while not done:
#             status, done = downloader.next_chunk()
        
#         file_stream.seek(0)
#         return file_stream.read()
#     except Exception as e:
#         st.error(f"Download Error: {e}")
#         return None

# # --- Streamlit UI ---
# st.title("Google Drive Integration (OAuth 2.0)")

# # 1. Authentication Section
# st.header("1. Authentication")
# if os.path.exists(TOKEN_FILE):
#     st.success("Authenticated with Google Account")
#     if st.button("Logout / Reset Login"):
#         os.remove(TOKEN_FILE)
#         st.rerun()
# else:
#     st.warning("Not Authenticated. Click the button below to log in via your browser.")
#     if st.button("Log in to Google Drive"):
#         service = get_drive_service()
#         if service:
#             st.success("Login Successful!")
#             st.rerun()

# st.divider()

# # 2. Folder Configuration
# st.header("2. Folder Configuration")
# # Defaulting to your 'mis test' folder ID
# folder_id_input = st.text_input("Folder ID (Optional - leave blank for Root)")

# # 3. Upload Section
# st.header("3. Upload File")
# uploaded_file = st.file_uploader("Choose a file to upload")
# if uploaded_file is not None:
#     if st.button("Upload to Drive"):
#         with st.spinner("Uploading..."):
#             file_id = upload_to_drive(uploaded_file.getvalue(), uploaded_file.name, folder_id=folder_id_input if folder_id_input else None)
#             if file_id:
#                 st.success(f"File uploaded successfully! File ID: {file_id}")

# st.divider()

# # 4. Download Section
# st.header("4. Download File")
# if st.button("Refresh File List"):
#     st.session_state.drive_files = list_files_in_drive(folder_id_input if folder_id_input else None)

# if 'drive_files' not in st.session_state:
#     st.session_state.drive_files = list_files_in_drive(folder_id_input if folder_id_input else None)

# if st.session_state.drive_files:
#     selected_file = st.selectbox("Select a file from Drive", st.session_state.drive_files, format_func=lambda x: x['name'])
#     if st.button("Download from Drive"):
#         with st.spinner("Downloading..."):
#             file_data = download_from_drive(selected_file['id'], selected_file['name'])
#             if file_data:
#                 st.download_button(
#                     label=f"Click here to save {selected_file['name']} to your computer",
#                     data=file_data,
#                     file_name=selected_file['name'],
#                     mime="application/octet-stream"
#                 )
#                 st.success("Download ready!")
# else:
#     st.info("No files found in this folder or folder not accessible.")
