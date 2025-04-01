import os
import io
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List

import docx
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# The scope we need is drive.readonly to search and download files
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
TOKEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../token.json')
CREDENTIALS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../client_secret_1054911966299-ntoekdnpbnl07lr76fjsnkjh0c288r72.apps.googleusercontent.com.json')


class GoogleDriveService:
    """Service for interacting with Google Drive API."""
    
    def __init__(self):
        """Initialize the GoogleDriveService with Google Drive API credentials."""
        self.credentials = self._get_credentials()
        self.service = build('drive', 'v3', credentials=self.credentials)
        
    def _get_credentials(self) -> Credentials:
        """
        Get and refresh the user's credentials.
        
        Returns:
            Credentials: The OAuth2 credentials for API access.
        """
        creds = None
        
        # Check if token.json file exists
        if os.path.exists(TOKEN_PATH):
            try:
                import json
                with open(TOKEN_PATH, 'r') as token_file:
                    token_json = json.load(token_file)
                creds = Credentials.from_authorized_user_info(token_json, SCOPES)
            except Exception as e:
                logging.error(f"Error loading credentials: {e}")
                creds = None
            
        # If credentials don't exist or are invalid, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Start OAuth2 flow for user authorization
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=65030)
                
            # Save credentials for future use
            with open(TOKEN_PATH, 'w') as token:
                token.write(creds.to_json())
                
        return creds
    
    def search_file(self, file_name: str) -> Optional[str]:
        """
        Search for a file in Google Drive by name.
        
        Args:
            file_name: The name of the file to search for.
            
        Returns:
            The file ID if found, None otherwise.
        """
        query = f"name contains '{file_name}' and trashed = false"
        
        # Search for the file
        results = self.service.files().list(
            q=query,
            spaces='drive',
            fields='files(id, name, mimeType)'
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            logging.info(f"No files found with name '{file_name}'")
            return None
        
        # Return the ID of the first matching file
        logging.info(f"Found file: {items[0]['name']} ({items[0]['id']})")
        return items[0]['id']
    
    def download_file(self, file_id: str) -> Tuple[str, str, bytes]:
        """
        Download a file from Google Drive by its ID.
        
        Args:
            file_id: The ID of the file to download.
            
        Returns:
            Tuple containing (file_name, mime_type, file_content_bytes)
        """
        # Get file metadata
        file_metadata = self.service.files().get(fileId=file_id, fields='name,mimeType').execute()
        file_name = file_metadata['name']
        mime_type = file_metadata['mimeType']
        
        file_content = io.BytesIO()
        
        # Handle Google Docs differently than regular files
        if mime_type == 'application/vnd.google-apps.document':
            # Export Google Doc as plain text
            request = self.service.files().export(fileId=file_id, mimeType='text/plain')
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    logging.info(f"Exporting Google Doc: {int(status.progress() * 100)}%")
                except Exception as e:
                    logging.warning(f"Encountered {str(e)}")
                    raise
                
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Export Google Sheet as CSV
            request = self.service.files().export(fileId=file_id, mimeType='text/csv')
            downloader = MediaIoBaseDownload(file_content, request)
            
            done = False
            while not done:
                try:
                    status, done = downloader.next_chunk()
                    logging.info(f"Exporting Google Sheet: {int(status.progress() * 100)}%")
                except Exception as e:
                    logging.warning(f"Encountered {str(e)}")
                    raise
                
        else:
            # Regular file download
            try:
                request = self.service.files().get_media(fileId=file_id)
                downloader = MediaIoBaseDownload(file_content, request)
                
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    logging.info(f"Download {int(status.progress() * 100)}%")
            except Exception as e:
                logging.warning(f"Encountered {e.__class__.__name__} {str(e)}")
                raise
            
        file_content.seek(0)
        return file_name, mime_type, file_content.read()
    
    def extract_text_from_file(self, file_id: str, mime_type: str, content: bytes) -> str:
        """
        Extract text content from downloaded file.
        
        Args:
            file_id: The ID of the file in Google Drive.
            mime_type: The MIME type of the file.
            content: The file content in bytes.
            
        Returns:
            The extracted text content.
        """
        if mime_type == 'application/vnd.google-apps.document':
            # Google Docs are already exported as plain text in download_file
            return content.decode('utf-8')
        elif mime_type == 'application/vnd.google-apps.spreadsheet':
            # Google Sheets are already exported as CSV in download_file
            return content.decode('utf-8')
        elif mime_type == 'application/pdf':
            return self._extract_text_from_pdf(content)
        elif mime_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
            return self._extract_text_from_docx(content)
        elif 'text/' in mime_type:
            return content.decode('utf-8')
        else:
            logging.warning(f"Unsupported file type: {mime_type}")
            return ""
    
    def _extract_text_from_google_doc(self, doc_id: str) -> str:
        """Extract text from a Google Doc using the Drive API."""
        request = self.service.files().export(fileId=doc_id, mimeType='text/plain')
        file_content = io.BytesIO()
        downloader = MediaIoBaseDownload(file_content, request)
        
        done = False
        while not done:
            status, done = downloader.next_chunk()
            
        file_content.seek(0)
        return file_content.read().decode('utf-8')
    
    def _extract_text_from_pdf(self, content: bytes) -> str:
        """Extract text from a PDF file."""
        # For simplicity, let's just return a placeholder
        # In a real implementation, you would use a PDF library like PyPDF2 or pdfminer
        logging.warning("PDF text extraction is not fully implemented. Consider adding PyPDF2 to requirements.")
        return "PDF text extraction not fully implemented."
    
    def _extract_text_from_docx(self, content: bytes) -> str:
        """Extract text from a DOCX file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
            
        try:
            doc = docx.Document(temp_file_path)
            full_text = [paragraph.text for paragraph in doc.paragraphs]
            return '\n'.join(full_text)
        except Exception as e:
            logging.error(f"Error extracting text from DOCX: {e}")
            return ""
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)