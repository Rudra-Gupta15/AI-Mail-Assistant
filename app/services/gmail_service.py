import os
import os.path
import base64
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GmailService:
    def __init__(self):
        self.creds = None
        self.token_path = 'token.json'
        self.credentials_path = 'credentials.json'
        self._authenticate()

    def _authenticate(self):
        """Authenticates with Gmail API using OAuth2."""
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        # If there are no (valid) credentials available, let the user log in.
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    self.creds = None
            
            # Note: For a web app, we'll use a redirect-based flow in the routes.
            # This init-time check is mostly for local/dev use.
            if not self.creds:
                logger.warning("Gmail credentials not initialized. Authentication required via API.")

    def get_service(self):
        """Returns the Gmail API service object."""
        if not self.creds or not self.creds.valid:
            return None
        return build('gmail', 'v1', credentials=self.creds)

    def fetch_unread_emails(self, max_results=5):
        """Fetches unread emails from the inbox."""
        service = self.get_service()
        if not service:
            return []

        try:
            # Query: unread messages specifically in the INBOX to be more inclusive
            query = 'label:INBOX is:unread'
            results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                txt = service.users().messages().get(userId='me', id=msg['id']).execute()
                payload = txt.get('payload', {})
                headers = payload.get('headers', [])
                
                email_data = {
                    'id': msg['id'],
                    'threadId': txt['threadId'],
                    'subject': '',
                    'sender': '',
                    'body': '',
                    'timestamp': int(txt.get('internalDate', 0)) // 1000  # Convert to seconds
                }
                
                for header in headers:
                    if header['name'] == 'Subject':
                        email_data['subject'] = header['value']
                    if header['name'] == 'From':
                        email_data['sender'] = header['value']
                
                # Extract body
                parts = payload.get('parts', [])
                if not parts:
                    data = payload.get('body', {}).get('data', '')
                else:
                    # Simple extraction: take the first part
                    data = parts[0].get('body', {}).get('data', '')
                
                if data:
                    decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                    email_data['body'] = decoded_data
                
                emails.append(email_data)
            
            return emails

        except HttpError as error:
            logger.error(f'An error occurred: {error}')
            return []

    def send_reply(self, original_email_id, thread_id, reply_text):
        """Sends a reply to an existing email thread."""
        service = self.get_service()
        if not service:
            return False

        try:
            # First, fetch the original message to get headers for threading
            original_msg = service.users().messages().get(userId='me', id=original_email_id).execute()
            headers = original_msg['payload']['headers']
            
            subject = ''
            to = ''
            msg_id = ''
            
            for header in headers:
                if header['name'] == 'Subject':
                    subject = header['value']
                    if not subject.startswith('Re:'):
                        subject = 'Re: ' + subject
                if header['name'] == 'From':
                    to = header['value']
                if header['name'] == 'Message-ID':
                    msg_id = header['value']

            # Create the MIME message
            from email.mime.text import MIMEText
            message = MIMEText(reply_text)
            message['to'] = to
            message['subject'] = subject
            message['In-Reply-To'] = msg_id
            message['References'] = msg_id
            
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            send_results = service.users().messages().send(
                userId='me', 
                body={'raw': raw, 'threadId': thread_id}
            ).execute()
            
            # Mark the original as read
            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': [original_email_id],
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
            return True
        except Exception as e:
            logger.error(f"Error sending reply: {e}")
            return False

    def send_new_email(self, recipient, subject, body):
        """Sends a new email."""
        service = self.get_service()
        if not service:
            return False
        try:
            from email.mime.text import MIMEText
            message = MIMEText(body)
            message['to'] = recipient
            message['subject'] = subject
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            service.users().messages().send(userId='me', body={'raw': raw}).execute()
            return True
        except Exception as e:
            logger.error(f"Error sending new email: {e}")
            return False

gmail_service = GmailService()
