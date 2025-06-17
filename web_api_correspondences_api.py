# web/api/correspondences_api.py
"""
API для работы с соответствиями заголовков
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from web.services.correspondences_service import correspondences_service
from web.utils.validators import validate_required_fields

correspondences_api_bp = Blueprint('correspondences_api', __name__)


@correspondences_api_bp.route('/auto-map', methods=['POST'])
def auto_map_headers():
    """
    Автоматическое сопоставление заголовков
    
    Body:
    {
        "register_type": "ипотека",
        "template_headers": ["Номер договора", "ФИО", ...],
        "file_headers": ["contract_number", "full_name", ...]
    }
    """
    try:
        data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['register_type', 'template_headers', 'file_headers']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        register_type = data.get('register_type', '').lower()
        template_headers = data.get('template_headers', [])
        file_headers = data.get('file_headers', [])
        
        if not isinstance(template_headers, list):
            return jsonify({'error': 'template_headers должен быть списком'}), 400
        
        if not isinstance(file_headers, list):
            return jsonify({'error': 'file_headers должен быть списком'}), 400
        
        if not template_headers:
            return jsonify({'error': 'template_headers не может быть пустым'}), 400

        # Выполняем автоматическое сопоставление
        mappings = correspondences_service.auto_map_headers(
            register_type, template_headers, file_headers
        )

        return jsonify({
            'success': True,
            'register_type': register_type,
            'mappings': mappings,
            'mapped_count': len(mappings),
            'total_template_headers': len(template_headers),
            'timestamp': datetime.now().isoformat()
        })

    except Exception as e:
        current_app.logger.error(f"Ошибка в auto_map_headers: {str(e)}")
        return jsonify({'error': f'Ошибка автосопоставления: {str(e)}'}), 500


@correspondences_api_bp.route('/', methods=['PUT'])
def save_correspondences():
    """
    Сохранение соответствий заголовков
    
    Body:
    {
        "register_type": "ипотека",
        "mappings": {
            "Номер договора": "contract_number",
            "ФИО": "full_name"
        }
    }
    """
    try:
        data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['register_type', 'mappings']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        register_type = data.get('register_type', '').lower()
        mappings = data.get('mappings', {})
        
        if not isinstance(mappings, dict):
            return jsonify({'error': 'mappings должен быть объектом'}), 400
        
        # Сохраняем соответствия
        success = correspondences_service.save_correspondences(register_type, mappings)
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type,
                'saved_mappings': len(mappings),
                'message': 'Соответствия успешно сохранены',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Ошибка при сохранении соответствий'}), 500
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в save_correspondences: {str(e)}")
        return jsonify({'error': f'Ошибка сохранения соответствий: {str(e)}'}), 500


@correspondences_api_bp.route('/<string:register_type>')
def get_correspondences(register_type):
    """
    Получение соответствий для типа регистра
    
    Args:
        register_type: Тип регистра
    """
    try:
        correspondences = correspondences_service.load_correspondences(register_type.lower())
        
        return jsonify({
            'success': True,
            'register_type': register_type.lower(),
            'correspondences': correspondences,
            'mappings_count': len(correspondences),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения соответствий для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка получения соответствий: {str(e)}'}), 500


@correspondences_api_bp.route('/')
def get_all_correspondences():
    """Получение всех соответствий"""
    try:
        all_correspondences = correspondences_service.get_all_correspondences()
        
        return jsonify({
            'success': True,
            'correspondences': all_correspondences,
            'register_types_count': len(all_correspondences),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения всех соответствий: {str(e)}")
        return jsonify({'error': f'Ошибка получения соответствий: {str(e)}'}), 500


@correspondences_api_bp.route('/<string:register_type>', methods=['DELETE'])
def delete_correspondences(register_type):
    """
    Удаление соответствий для типа регистра
    
    Args:
        register_type: Тип регистра
    """
    try:
        success = correspondences_service.delete_correspondences(register_type.lower())
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type.lower(),
                'message': 'Соответствия успешно удалены',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Соответствия не найдены'
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Ошибка удаления соответствий для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка удаления соответствий: {str(e)}'}), 500


@correspondences_api_bp.route('/<string:register_type>/mapping', methods=['PUT'])
def update_correspondence(register_type):
    """
    Обновление отдельного соответствия
    
    Args:
        register_type: Тип регистра
        
    Body:
    {
        "template_header": "Номер договора",
        "file_header": "contract_number"
    }
    """
    try:
        data = request.get_json()
        
        # Валидация обязательных полей
        required_fields = ['template_header', 'file_header']
        validation_error = validate_required_fields(data, required_fields)
        if validation_error:
            return jsonify({'error': validation_error}), 400
        
        template_header = data.get('template_header')
        file_header = data.get('file_header')
        
        success = correspondences_service.update_correspondence(
            register_type.lower(), template_header, file_header
        )
        
        if success:
            return jsonify({
                'success': True,
                'register_type': register_type.lower(),
                'template_header': template_header,
                'file_header': file_header,
                'message': 'Соответствие успешно обновлено',
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({'error': 'Ошибка обновления соответствия'}), 500
            
    except Exception as e:
        current_app.logger.error(f"Ошибка обновления соответствия для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка обновления соответствия: {str(e)}'}), 500


@correspondences_api_bp.route('/templates/<string:register_type>')
def get_template_headers(register_type):
    """
    Получение шаблонных заголовков для типа регистра
    
    Args:
        register_type: Тип регистра
    """
    try:
        template_headers = correspondences_service.get_template_headers(register_type.lower())
        
        return jsonify({
            'success': True,
            'register_type': register_type.lower(),
            'template_headers': template_headers,
            'headers_count': len(template_headers),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения шаблонных заголовков для {register_type}: {str(e)}")
        return jsonify({'error': f'Ошибка получения шаблонных заголовков: {str(e)}'}), 500
