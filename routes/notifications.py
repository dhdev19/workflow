from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from models import db, User, FCMDevice
from utils import role_required
from datetime import datetime

notifications_bp = Blueprint('notifications', __name__)

@notifications_bp.route('/register-token', methods=['POST'])
@login_required
def register_fcm_token():
    """Register or update FCM token for the current user"""
    try:
        data = request.get_json()
        fcm_token = data.get('fcm_token')
        device_name = data.get('device_name', 'Unknown Device')
        device_type = data.get('device_type', 'unknown')
        
        if not fcm_token:
            return jsonify({'success': False, 'message': 'FCM token is required'}), 400
        
        # Check if token already exists for this user
        existing_device = FCMDevice.query.filter_by(
            user_id=current_user.id,
            fcm_token=fcm_token
        ).first()
        
        if existing_device:
            # Update last active time
            existing_device.last_active = datetime.utcnow()
            if device_name:
                existing_device.device_name = device_name
            if device_type:
                existing_device.device_type = device_type
        else:
            # Check if token exists for another user (shouldn't happen, but handle it)
            token_exists = FCMDevice.query.filter_by(fcm_token=fcm_token).first()
            if token_exists:
                # Remove old token (device was reassigned)
                db.session.delete(token_exists)
            
            # Create new device entry
            device = FCMDevice(
                user_id=current_user.id,
                fcm_token=fcm_token,
                device_name=device_name,
                device_type=device_type,
                last_active=datetime.utcnow()
            )
            db.session.add(device)
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'FCM token registered successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/remove-token', methods=['POST'])
@login_required
def remove_fcm_token():
    """Remove FCM token for the current user"""
    try:
        data = request.get_json()
        fcm_token = data.get('fcm_token')
        
        if fcm_token:
            # Remove specific device
            device = FCMDevice.query.filter_by(
                user_id=current_user.id,
                fcm_token=fcm_token
            ).first()
            if device:
                db.session.delete(device)
        else:
            # Remove all devices for user
            FCMDevice.query.filter_by(user_id=current_user.id).delete()
        
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'FCM token(s) removed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@notifications_bp.route('/devices', methods=['GET'])
@login_required
def get_user_devices():
    """Get all FCM devices for the current user"""
    try:
        devices = FCMDevice.query.filter_by(user_id=current_user.id).all()
        devices_list = [{
            'id': device.id,
            'device_name': device.device_name,
            'device_type': device.device_type,
            'last_active': device.last_active.isoformat() if device.last_active else None,
            'created_at': device.created_at.isoformat() if device.created_at else None
        } for device in devices]
        
        return jsonify({'success': True, 'devices': devices_list}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

