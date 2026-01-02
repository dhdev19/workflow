import os
import firebase_admin
from firebase_admin import credentials, messaging
from flask import current_app

# Initialize Firebase Admin SDK
_firebase_app = None

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    global _firebase_app
    if _firebase_app is None:
        # Check for Firebase credentials file path from environment variable
        cred_path = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH', 'workflow-firebase.json')
        if os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            current_app.logger.warning(f"Firebase credentials file not found at {cred_path}. FCM notifications will be disabled.")
    return _firebase_app

def send_notification(fcm_token, title, body, data=None):
    """
    Send a push notification to a single device
    
    Args:
        fcm_token: FCM token of the device
        title: Notification title
        body: Notification body
        data: Optional dictionary of additional data
    
    Returns:
        bool: True if notification sent successfully, False otherwise
    """
    if not fcm_token:
        return False
    
    try:
        initialize_firebase()
        
        if _firebase_app is None:
            current_app.logger.warning("Firebase not initialized. Cannot send notification.")
            return False
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
        )
        
        response = messaging.send(message)
        current_app.logger.info(f"Successfully sent notification: {response}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error sending notification: {str(e)}")
        return False

def send_notification_to_multiple(tokens, title, body, data=None):
    """
    Send push notifications to multiple devices
    
    Args:
        tokens: List of FCM tokens
        title: Notification title
        body: Notification body
        data: Optional dictionary of additional data
    
    Returns:
        dict: Results with success and failure counts
    """
    if not tokens:
        return {'success': 0, 'failure': 0}
    
    # Filter out None/empty tokens
    valid_tokens = [token for token in tokens if token]
    if not valid_tokens:
        return {'success': 0, 'failure': 0}
    
    try:
        initialize_firebase()
        
        if _firebase_app is None:
            current_app.logger.warning("Firebase not initialized. Cannot send notifications.")
            return {'success': 0, 'failure': len(valid_tokens)}
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=valid_tokens,
        )
        
        response = messaging.send_multicast(message)
        current_app.logger.info(f"Successfully sent {response.success_count} notifications, {response.failure_count} failed")
        return {'success': response.success_count, 'failure': response.failure_count}
    except Exception as e:
        current_app.logger.error(f"Error sending notifications: {str(e)}")
        return {'success': 0, 'failure': len(valid_tokens)}

