# web/blueprints/registry_routes.py
"""
Blueprint для маршрутов обработки реестра сделок.
Обрабатывает файлы сделок, проверки и сотрудников.
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime

from web.services.registry_service import registry_service
from web.utils.logging_helper import log_user_access

# Создаем blueprint
registry_bp = Blueprint('registry', __name__, url_prefix='/registry')


@registry_bp.route('/process', methods=['POST'])
def process_registry_files():
    """
    Обработка загруженных файлов реестра
    
    Expected form data:
        files: список файлов (Сделки*, Проверка*, empl*)
    
    Returns:
        JSON: результат обработки
    """
    try:
        # Проверяем наличие файлов
        if 'files' not in request.files:
            return jsonify({'error': 'Файлы не найдены'}), 400
        
        files = request.files.getlist('files')
        client_ip = request.remote_addr
        
        # Логируем запрос
        filenames = [f.filename for f in files if f.filename]
        log_user_access(
            page="Registry Upload",
            client_ip=client_ip,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Попытка загрузки {len(filenames)} файлов для реестра"
        )
        
        # Валидируем и группируем файлы
        valid, error_msg, grouped_files = registry_service.validate_files(files)
        if not valid:
            return jsonify({'error': error_msg}), 400
        
        # Запускаем обработку через сервис
        success, message = registry_service.process_files(
            grouped_files['deals'], 
            grouped_files['check'], 
            grouped_files['employee'],
            client_ip
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'task_id': registry_service.current_task.task_id
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_registry_files: {str(e)}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@registry_bp.route('/status', methods=['GET'])
def get_processing_status():
    """
    Получение статуса текущей обработки
    
    Returns:
        JSON: статус обработки
    """
    try:
        status = registry_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Ошибка в get_processing_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """
    Отмена текущей обработки
    
    Returns:
        JSON: результат отмены
    """
    try:
        result = registry_service.cancel_processing()
        
        # Логируем отмену
        log_user_access(
            page="Registry Cancel",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Отмена обработки реестра"
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка в cancel_processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/download', methods=['GET'])
def download_result():
    """
    Скачивание файла результата обработки
    
    Returns:
        File: файл результата или JSON с ошибкой
    """
    try:
        result_file = registry_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        # Логируем скачивание
        log_user_access(
            page="Registry Download",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Скачивание результата реестра: {Path(result_file).name}"
        )
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        print(f"Ошибка в download_result: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/reset', methods=['POST'])
def reset_task():
    """
    Сброс текущей задачи (только если она не выполняется)
    
    Returns:
        JSON: результат сброса
    """
    try:
        success = registry_service.reset_task()
        
        if success:
            log_user_access(
                page="Registry Reset",
                client_ip=request.remote_addr,
                current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                message="Сброс задачи обработки реестра"
            )
            return jsonify({
                'success': True,
                'message': 'Задача сброшена'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Невозможно сбросить выполняющуюся задачу'
            }), 400
            
    except Exception as e:
        print(f"Ошибка в reset_task: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/requirements', methods=['GET'])
def get_file_requirements():
    """
    Получение требований к файлам
    
    Returns:
        JSON: требования к файлам
    """
    try:
        requirements = registry_service.get_file_requirements()
        return jsonify({
            'requirements': requirements,
            'description': 'Требования к файлам для обработки реестра сделок',
            'total_files_required': 3
        })
    except Exception as e:
        print(f"Ошибка в get_file_requirements: {str(e)}")
        return jsonify({'error': str(e)}), 500


@registry_bp.route('/info', methods=['GET'])
def get_info():
    """
    Получение информации о модуле реестра
    
    Returns:
        JSON: информация о модуле
    """
    return jsonify({
        'module': 'Реестр сделок',
        'description': 'Модуль для обработки файлов сделок, проверки и сотрудников',
        'supported_formats': list(registry_service.ALLOWED_EXTENSIONS),
        'required_files': [
            'Сделки* (файл сделок)',
            'Проверка* (файл проверки)',
            'empl* (файл сотрудников)'
        ],
        'endpoints': [
            'POST /registry/process - Обработка файлов',
            'GET /registry/status - Статус обработки',
            'POST /registry/cancel - Отмена обработки',
            'GET /registry/download - Скачивание результата',
            'POST /registry/reset - Сброс задачи',
            'GET /registry/requirements - Требования к файлам',
            'GET /registry/info - Информация о модуле'
        ],
        'version': '2.0.0'
    })
