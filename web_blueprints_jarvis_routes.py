# web/blueprints/jarvis_routes.py
"""
Blueprint для маршрутов обработки Джарвиса.
Обрабатывает файлы продаж, не пролонгированных договоров и сотрудников.
"""

from flask import Blueprint, request, jsonify, send_file
from pathlib import Path
import os
from datetime import datetime

from web.services.jarvis_service import jarvis_service
from web.utils.logging_helper import log_user_access

# Создаем blueprint
jarvis_bp = Blueprint('jarvis', __name__, url_prefix='/jarvis')


@jarvis_bp.route('/process', methods=['POST'])
def process_jarvis_files():
    """
    Обработка загруженных файлов Джарвиса
    
    Expected form data:
        files: список файлов (Prodagi_VSK*, не+прол*, employ*)
    
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
            page="Jarvis Upload",
            client_ip=client_ip,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Попытка загрузки {len(filenames)} файлов для Джарвиса"
        )
        
        # Запускаем обработку через сервис
        success, message = jarvis_service.process_files(files, client_ip)
        
        if success:
            return jsonify({
                'success': True,
                'message': message,
                'task_id': jarvis_service.current_task.task_id
            })
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        print(f"Ошибка в process_jarvis_files: {str(e)}")
        return jsonify({'error': f'Внутренняя ошибка сервера: {str(e)}'}), 500


@jarvis_bp.route('/status', methods=['GET'])
def get_processing_status():
    """
    Получение статуса текущей обработки
    
    Returns:
        JSON: статус обработки
    """
    try:
        status = jarvis_service.get_status()
        return jsonify(status)
    except Exception as e:
        print(f"Ошибка в get_processing_status: {str(e)}")
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/cancel', methods=['POST'])
def cancel_processing():
    """
    Отмена текущей обработки
    
    Returns:
        JSON: результат отмены
    """
    try:
        result = jarvis_service.cancel_processing()
        
        # Логируем отмену
        log_user_access(
            page="Jarvis Cancel",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message="Отмена обработки Джарвиса"
        )
        
        return jsonify(result)
    except Exception as e:
        print(f"Ошибка в cancel_processing: {str(e)}")
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/download', methods=['GET'])
def download_result():
    """
    Скачивание файла результата обработки
    
    Returns:
        File: файл результата или JSON с ошибкой
    """
    try:
        result_file = jarvis_service.get_result_file()
        
        if not result_file or not os.path.exists(result_file):
            return jsonify({'error': 'Файл результата не найден'}), 404
        
        # Логируем скачивание
        log_user_access(
            page="Jarvis Download",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Скачивание результата Джарвиса: {Path(result_file).name}"
        )
        
        return send_file(
            result_file,
            as_attachment=True,
            download_name=Path(result_file).name
        )
        
    except Exception as e:
        print(f"Ошибка в download_result: {str(e)}")
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/reset', methods=['POST'])
def reset_task():
    """
    Сброс текущей задачи (только если она не выполняется)
    
    Returns:
        JSON: результат сброса
    """
    try:
        success = jarvis_service.reset_task()
        
        if success:
            log_user_access(
                page="Jarvis Reset",
                client_ip=request.remote_addr,
                current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                message="Сброс задачи обработки Джарвиса"
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


@jarvis_bp.route('/requirements', methods=['GET'])
def get_file_requirements():
    """
    Получение требований к файлам
    
    Returns:
        JSON: требования к файлам
    """
    try:
        requirements = jarvis_service.get_file_requirements()
        return jsonify({
            'requirements': requirements,
            'description': 'Требования к файлам для обработки Джарвиса',
            'total_files_minimum': 3
        })
    except Exception as e:
        print(f"Ошибка в get_file_requirements: {str(e)}")
        return jsonify({'error': str(e)}), 500


@jarvis_bp.route('/info', methods=['GET'])
def get_info():
    """
    Получение информации о модуле Джарвиса
    
    Returns:
        JSON: информация о модуле
    """
    return jsonify({
        'module': 'Джарвис',
        'description': 'Модуль для обработки файлов продаж, не пролонгированных договоров и сотрудников',
        'supported_formats': list(jarvis_service.ALLOWED_EXTENSIONS),
        'required_files': [
            'Prodagi_VSK* (файлы продаж, может быть несколько)',
            'не+прол* (файл не пролонгированных, один)',
            'employ* (файл сотрудников, один)'
        ],
        'endpoints': [
            'POST /jarvis/process - Обработка файлов',
            'GET /jarvis/status - Статус обработки',
            'POST /jarvis/cancel - Отмена обработки',
            'GET /jarvis/download - Скачивание результата',
            'POST /jarvis/reset - Сброс задачи',
            'GET /jarvis/requirements - Требования к файлам',
            'GET /jarvis/info - Информация о модуле'
        ],
        'version': '2.0.0'
    })
