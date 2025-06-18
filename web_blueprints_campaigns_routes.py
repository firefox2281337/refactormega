# web/blueprints/campaigns_routes.py
"""
Blueprint для маршрутов проверки кампаний.
Обрабатывает загрузку и проверку файлов кампаний.
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime

from web.services.campaigns_service import campaigns_service
from web.utils.validators import validate_file_upload
from web.utils.logging_helper import log_user_access

# Создаем blueprint
campaigns_bp = Blueprint('campaigns', __name__, url_prefix='/campaigns')


@campaigns_bp.route('/process', methods=['POST'])
def process_campaigns_file():
    """
    Обработка загруженного файла кампаний
    
    Expected form data:
        file: файл кампаний (должен начинаться с 'cgr')
    
    Returns:
        JSON: результат обработки
    """
    try:
        # Проверяем наличие файла
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        client_ip = request.remote_addr
        
        # Логируем запрос
        log_user_access(
            page="Campaigns Upload",
            client_ip=client_ip,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Попытка загрузки файла: {file.filename}"
        )
        
        # Запускаем обработку через сервис
        success, message = campaigns_service.process_file(file, client_ip)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'task_id': campaigns_service.current_task.task_id
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_campaigns_file: {str(e)}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@campaigns_bp.route('/status', methods=['GET'])
def get_processing_status():
    """
    Получение статуса текущей обработки
    
    Returns:
        JSON: статус обработки
    """
    try:
        status = campaigns_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Ошибка в get_processing_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """
    Отмена текущей обработки
    
    Returns:
        JSON: результат отмены
    """
    try:
        result = campaigns_service.cancel_processing()
        
        # Логируем отмену
        log_user_access(
            page="Campaigns Cancel",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Отмена обработки кампаний"
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка в cancel_processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/download', methods=['GET'])
def download_result():
    """
    Скачивание файла результата обработки
    
    Returns:
        File: файл результата или JSON с ошибкой
    """
    try:
        result_file = campaigns_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        # Логируем скачивание
        log_user_access(
            page="Campaigns Download",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Скачивание результата: {Path(result_file).name}"
        )
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        print(f"Ошибка в download_result: {str(e)}")
        return jsonify({'error': str(e)}), 500


@campaigns_bp.route('/reset', methods=['POST'])
def reset_task():
    """
    Сброс текущей задачи (только если она не выполняется)
    
    Returns:
        JSON: результат сброса
    """
    try:
        success = campaigns_service.reset_task()
        
        if success:
            log_user_access(
                page="Campaigns Reset",
                client_ip=request.remote_addr,
                current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                message="Сброс задачи обработки кампаний"
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


@campaigns_bp.route('/info', methods=['GET'])
def get_info():
    """
    Получение информации о модуле проверки кампаний
    
    Returns:
        JSON: информация о модуле
    """
    return jsonify({
        'module': 'Проверка кампаний',
        'description': 'Модуль для обработки и проверки файлов кампаний',
        'supported_formats': list(campaigns_service.ALLOWED_EXTENSIONS),
        'file_prefix': 'cgr',
        'endpoints': [
            'POST /campaigns/process - Обработка файла',
            'GET /campaigns/status - Статус обработки',
            'POST /campaigns/cancel - Отмена обработки',
            'GET /campaigns/download - Скачивание результата',
            'POST /campaigns/reset - Сброс задачи',
            'GET /campaigns/info - Информация о модуле'
        ],
        'version': '2.0.0'
    })
