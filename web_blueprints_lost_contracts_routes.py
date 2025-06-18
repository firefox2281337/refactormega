# web/blueprints/lost_contracts_routes.py
"""
Blueprint для маршрутов обработки потерянных договоров.
Обрабатывает файлы с информацией о потерянных договорах.
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime

from web.services.lost_contracts_service import lost_contracts_service
from web.utils.logging_helper import log_user_access

# Создаем blueprint
lost_contracts_bp = Blueprint('lost_contracts', __name__, url_prefix='/lost_contracts')


@lost_contracts_bp.route('/process', methods=['POST'])
def process_lost_contracts_file():
    """
    Обработка загруженного файла потерянных договоров
    
    Expected form data:
        file: файл договоров (должен начинаться с 'Договора+по')
    
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
            page="Lost Contracts Upload",
            client_ip=client_ip,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Попытка загрузки файла потерянных договоров: {file.filename}"
        )
        
        # Запускаем обработку через сервис
        success, message = lost_contracts_service.process_file(file, client_ip)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'task_id': lost_contracts_service.current_task.task_id
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_lost_contracts_file: {str(e)}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@lost_contracts_bp.route('/status', methods=['GET'])
def get_processing_status():
    """
    Получение статуса текущей обработки
    
    Returns:
        JSON: статус обработки
    """
    try:
        status = lost_contracts_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Ошибка в get_processing_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """
    Отмена текущей обработки
    
    Returns:
        JSON: результат отмены
    """
    try:
        result = lost_contracts_service.cancel_processing()
        
        # Логируем отмену
        log_user_access(
            page="Lost Contracts Cancel",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Отмена обработки потерянных договоров"
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка в cancel_processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/download', methods=['GET'])
def download_result():
    """
    Скачивание файла результата обработки
    
    Returns:
        File: файл результата или JSON с ошибкой
    """
    try:
        result_file = lost_contracts_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        # Логируем скачивание
        log_user_access(
            page="Lost Contracts Download",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Скачивание результата потерянных договоров: {Path(result_file).name}"
        )
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        print(f"Ошибка в download_result: {str(e)}")
        return jsonify({'error': str(e)}), 500


@lost_contracts_bp.route('/reset', methods=['POST'])
def reset_task():
    """
    Сброс текущей задачи (только если она не выполняется)
    
    Returns:
        JSON: результат сброса
    """
    try:
        success = lost_contracts_service.reset_task()
        
        if success:
            log_user_access(
                page="Lost Contracts Reset",
                client_ip=request.remote_addr,
                current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                message="Сброс задачи обработки потерянных договоров"
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


@lost_contracts_bp.route('/info', methods=['GET'])
def get_info():
    """
    Получение информации о модуле потерянных договоров
    
    Returns:
        JSON: информация о модуле
    """
    return jsonify({
        'module': 'Потерянные договора',
        'description': 'Модуль для обработки файлов с информацией о потерянных договорах',
        'supported_formats': list(lost_contracts_service.ALLOWED_EXTENSIONS),
        'file_prefix': lost_contracts_service.FILE_PREFIX,
        'endpoints': [
            'POST /lost_contracts/process - Обработка файла',
            'GET /lost_contracts/status - Статус обработки',
            'POST /lost_contracts/cancel - Отмена обработки',
            'GET /lost_contracts/download - Скачивание результата',
            'POST /lost_contracts/reset - Сброс задачи',
            'GET /lost_contracts/info - Информация о модуле'
        ],
        'version': '2.0.0'
    })
