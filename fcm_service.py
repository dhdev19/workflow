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
            current_app.logger.error(f"FCM Notification FAILED - Firebase not initialized. Title: '{title}', Body: '{body}'")
            return False
        
        # Configure Android notification - let channel handle sound settings
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='task_notifications',  # Should match channel ID in Android app
                priority='high',
                # Don't specify sound here - let the notification channel handle it
                # The channel is configured with sound in MainApplication.kt
            )
        )
        
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            token=fcm_token,
            android=android_config,
        )
        
        response = messaging.send(message)
        # Log to production log (INFO) and error log (ERROR)
        current_app.logger.info(f"FCM Notification SENT - Title: '{title}', Body: '{body}', Token: {fcm_token[:20]}..., Response: {response}")
        current_app.logger.error(f"FCM Notification SENT - Title: '{title}', Body: '{body}', Token: {fcm_token[:20]}..., Response: {response}")
        return True
    except Exception as e:
        # Log failures to both logs
        current_app.logger.error(f"FCM Notification FAILED - Title: '{title}', Body: '{body}', Token: {fcm_token[:20] if fcm_token else 'None'}..., Error: {str(e)}")
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
            current_app.logger.error(f"FCM Notification MULTICAST FAILED - Firebase not initialized. Title: '{title}', Body: '{body}', Tokens: {len(valid_tokens)}")
            return {'success': 0, 'failure': len(valid_tokens)}
        
        # Configure Android notification - let channel handle sound settings
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='task_notifications',  # Should match channel ID in Android app
                priority='high',
                # Don't specify sound here - let the notification channel handle it
                # The channel is configured with sound in MainApplication.kt
            )
        )
        
        # Configure Android notification - let channel handle sound settings
        android_config = messaging.AndroidConfig(
            priority='high',
            notification=messaging.AndroidNotification(
                channel_id='task_notifications',  # Should match channel ID in Android app
                priority='high',
                # Don't specify sound here - let the notification channel handle it
                # The channel is configured with sound in MainApplication.kt
            )
        )
        
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            data=data or {},
            tokens=valid_tokens,
            android=android_config,
        )
        
        response = messaging.send_multicast(message)
        # Log to production log (INFO) and error log (ERROR)
        current_app.logger.info(f"FCM Notification MULTICAST - Title: '{title}', Body: '{body}', Tokens: {len(valid_tokens)}, Success: {response.success_count}, Failed: {response.failure_count}")
        current_app.logger.error(f"FCM Notification MULTICAST - Title: '{title}', Body: '{body}', Tokens: {len(valid_tokens)}, Success: {response.success_count}, Failed: {response.failure_count}")
        return {'success': response.success_count, 'failure': response.failure_count}
    except Exception as e:
        # Log failures to both logs
        current_app.logger.error(f"FCM Notification MULTICAST FAILED - Title: '{title}', Body: '{body}', Tokens: {len(valid_tokens)}, Error: {str(e)}")
        return {'success': 0, 'failure': len(valid_tokens)}

