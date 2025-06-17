# web/api/core_api.py
"""
Основные API endpoints
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from web.services.system_service import system_service
from web.services.processing_service import processing_service
from web.utils.logging_helper import log_user_access

core_api_bp = Blueprint('core_api', __name__)


@core_api_bp.route('/status')
def get_system_status():
    """Получение статуса системы и баз данных"""
    try:
        # Логируем доступ
        log_user_access(
            page="System Status API",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Запрос статуса системы"
        )
        
        # Получаем статусы БД
        db_statuses = system_service.get_database_statuses()
        
        # Получаем системную информацию
        system_info = system_service.get_cached_system_info()
        
        return jsonify({
            "databases": db_statuses,
            "system": system_info.get("system_info", {}),
            "last_check": system_info.get("last_check", "Неизвестно"),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в get_system_status: {str(e)}")
        return jsonify({'error': 'Ошибка получения статуса системы'}), 500


@core_api_bp.route('/health')
def health_check():
    """Простая проверка работоспособности API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '2.0.0'
    })


@core_api_bp.route('/processing/status')
def get_processing_status():
    """Получение статуса текущей обработки"""
    try:
        status = processing_service.get_status()
        return jsonify(status)
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения статуса обработки: {str(e)}")
        return jsonify({'error': 'Ошибка получения статуса обработки'}), 500


@core_api_bp.route('/processing/cancel', methods=['POST'])
def cancel_processing():
    """Отмена текущей обработки"""
    try:
        success = processing_service.cancel_processing()
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Обработка отменена'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Нет активной обработки для отмены'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Ошибка отмены обработки: {str(e)}")
        return jsonify({'error': 'Ошибка отмены обработки'}), 500


@core_api_bp.route('/processing/history')
def get_processing_history():
    """Получение истории обработки"""
    try:
        limit = request.args.get('limit', type=int)
        history = processing_service.get_history(limit)
        
        return jsonify({
            'history': history,
            'total': len(processing_service.task_history)
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения истории обработки: {str(e)}")
        return jsonify({'error': 'Ошибка получения истории обработки'}), 500


@core_api_bp.route('/info')
def get_api_info():
    """Получение информации об API"""
    return jsonify({
        'name': 'Сервер API',
        'version': '2.0.0',
        'description': 'Рефакторенный API для работы с данными',
        'endpoints': {
            'core': [
                'GET /api/status - Статус системы',
                'GET /api/health - Проверка работоспособности',
                'GET /api/info - Информация об API'
            ],
            'data': [
                'GET /api/data/kasko-prolongation - Данные пролонгации КАСКО',
            ],
            'settings': [
                'GET /api/settings/{type} - Получение настроек',
                'PUT /api/settings/{type} - Сохранение настроек'
            ],
            'correspondences': [
                'POST /api/correspondences/auto-map - Автосопоставление заголовков',
                'PUT /api/correspondences - Сохранение соответствий',
                'GET /api/correspondences/{type} - Получение соответствий'
            ],
            'processing': [
                'GET /api/processing/status - Статус обработки',
                'POST /api/processing/cancel - Отмена обработки',
                'GET /api/processing/history - История обработки'
            ]
        },
        'timestamp': datetime.now().isoformat()
    })
