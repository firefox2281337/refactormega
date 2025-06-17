# web/api/settings_api.py
"""
API для работы с настройками
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from web.services.settings_service import settings_service
from web.utils.validators import validate_required_fields

settings_api_bp = Blueprint('settings_api', __name__)


@settings_api_bp.route('/<string:register_type>')
def get_settings(register_type):
    """
    Получение настроек для типа регистрации
    
    Args:
        register_type: Тип регистрации (например, 'Ипотека', 'КАСКО')
    """
    try:
        settings = settings_service.get_settings(register_type)
        
        return jsonify({
            'success': True,
            'register_type': register_type,
            'settings': settings,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения настроек для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка получения настроек: {str(e)}'}), 500


@settings_api_bp.route('/<string:register_type>', methods=['PUT'])
def save_settings(register_type):
    """
    Сохранение настроек для типа регистрации
    
    Args:
        register_type: Тип регистрации
        
    Body:
    {
        "settings": {
            "key1": "value1",
            "key2": "value2"
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'settings' not in data:
            return jsonify({'error': 'Поле settings обязательно'}), 400
        
        settings = data['settings']
        
        if not isinstance(settings, dict):
            return jsonify({'error': 'settings должен быть объектом'}), 400
        
        success = settings_service.save_settings(register_type, settings)
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type,
                'message': 'Настройки успешно сохранены',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Ошибка сохранения настроек'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Ошибка сохранения настроек для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка сохранения настроек: {str(e)}'}), 500


@settings_api_bp.route('/<string:register_type>/<string:key>')
def get_setting(register_type, key):
    """
    Получение отдельной настройки
    
    Args:
        register_type: Тип регистрации
        key: Ключ настройки
    """
    try:
        default_value = request.args.get('default', '')
        value = settings_service.get_setting(register_type, key, default_value)
        
        return jsonify({
            'success': True,
            'register_type': register_type,
            'key': key,
            'value': value,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения настройки {key} для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка получения настройки: {str(e)}'}), 500


@settings_api_bp.route('/<string:register_type>/<string:key>', methods=['PUT'])
def update_setting(register_type, key):
    """
    Обновление отдельной настройки
    
    Args:
        register_type: Тип регистрации
        key: Ключ настройки
        
    Body:
    {
        "value": "new_value"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'value' not in data:
            return jsonify({'error': 'Поле value обязательно'}), 400
        
        value = data['value']
        success = settings_service.update_setting(register_type, key, str(value))
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type,
                'key': key,
                'value': value,
                'message': 'Настройка успешно обновлена',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Ошибка обновления настройки'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления настройки {key} для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка обновления настройки: {str(e)}'}), 500


@settings_api_bp.route('/')
def get_all_settings():
    """Получение всех настроек"""
    try:
        all_settings = settings_service.get_all_sections()
        
        return jsonify({
            'success': True,
            'settings': all_settings,
            'sections_count': len(all_settings),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения всех настроек: {str(e)}")
        return jsonify({'error': f'Ошибка получения настроек: {str(e)}'}), 500


@settings_api_bp.route('/<string:register_type>', methods=['DELETE'])
def delete_settings(register_type):
    """
    Удаление всех настроек для типа регистрации
    
    Args:
        register_type: Тип регистрации
    """
    try:
        success = settings_service.delete_section(register_type)
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type,
                'message': 'Настройки успешно удалены',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Секция настроек не найдена'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления настроек для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка удаления настроек: {str(e)}'}), 500
