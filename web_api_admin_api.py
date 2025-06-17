# web/api/admin_api.py
"""
API для административных функций
"""

import os
import sys
import time
import subprocess
import shutil
from datetime import datetime
from flask import Blueprint, jsonify, request, current_app

from web.services.system_service import system_service
from web.utils.admin_security import admin_security, admin_required
from web.utils.logging_helper import log_error

admin_api_bp = Blueprint('admin_api', __name__)


@admin_api_bp.route('/stats')
@admin_required
def get_admin_stats():
    """Получение детальной статистики для админки"""
    try:
        stats = system_service.get_detailed_system_stats()
        
        # Добавляем данные безопасности
        security_data = {
            'active_sessions': len(admin_security.active_sessions),
            'blocked_ips': list(admin_security.blocked_ips),
            'recent_events': admin_security.security_events[-20:],
            'login_attempts': len(admin_security.login_attempts),
            'system_health': system_service.calculate_system_health()
        }
        
        # Добавляем моковые данные для демонстрации
        mock_data = {
            'databases': {
                'connection_pools': {
                    'main_db': {'connected': True, 'response_time': 12},
                    'cache_db': {'connected': True, 'response_time': 8},
                    'log_db': {'connected': False, 'response_time': None}
                }
            },
            'users': {
                'active_users_24h': 42,
                'top_pages': [
                    {'page': '/dashboard', 'visits': 156},
                    {'page': '/nexus', 'visits': 89},
                    {'page': '/files', 'visits': 67},
                    {'page': '/api/data', 'visits': 45},
                    {'page': '/processing', 'visits': 23}
                ]
            }
        }
        
        return jsonify({
            'success': True,
            'system': stats.get('system', {}),
            'storage': stats.get('storage', {}),
            'security': security_data,
            'databases': mock_data['databases'],
            'users': mock_data['users'],
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения админ статистики: {str(e)}")
        return jsonify({'error': 'Ошибка получения статистики'}), 500


@admin_api_bp.route('/performance-data')
@admin_required
def get_performance_data():
    """Получение данных производительности для графиков"""
    try:
        timeframe = request.args.get('timeframe', '1h')
        data = system_service.get_performance_data(timeframe)
        
        return jsonify({
            'success': True,
            'timeframe': timeframe,
            'data': data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения данных производительности: {str(e)}")
        return jsonify({'error': 'Ошибка получения данных производительности'}), 500


@admin_api_bp.route('/security/events')
@admin_required
def get_security_events():
    """Получение событий безопасности"""
    try:
        limit = request.args.get('limit', 50, type=int)
        events = admin_security.security_events[-limit:]
        
        return jsonify({
            'success': True,
            'events': events,
            'total_events': len(admin_security.security_events),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения событий безопасности: {str(e)}")
        return jsonify({'error': 'Ошибка получения событий безопасности'}), 500


@admin_api_bp.route('/security/block-ip', methods=['POST'])
@admin_required
def block_ip():
    """Блокировка IP адреса"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP адрес не указан'}), 400
        
        admin_security.blocked_ips.add(ip)
        admin_security.save_security_config()
        
        admin_security.log_security_event(
            'ip_blocked_manually',
            f'IP {ip} blocked by admin via API',
            'medium'
        )
        
        return jsonify({
            'success': True,
            'message': f'IP {ip} заблокирован',
            'blocked_ips': list(admin_security.blocked_ips),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка блокировки IP: {str(e)}")
        return jsonify({'error': 'Ошибка блокировки IP'}), 500


@admin_api_bp.route('/security/unblock-ip', methods=['POST'])
@admin_required
def unblock_ip():
    """Разблокировка IP адреса"""
    try:
        data = request.get_json()
        ip = data.get('ip')
        
        if not ip:
            return jsonify({'error': 'IP адрес не указан'}), 400
        
        admin_security.blocked_ips.discard(ip)
        admin_security.save_security_config()
        
        admin_security.log_security_event(
            'ip_unblocked',
            f'IP {ip} unblocked by admin via API',
            'info'
        )
        
        return jsonify({
            'success': True,
            'message': f'IP {ip} разблокирован',
            'blocked_ips': list(admin_security.blocked_ips),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка разблокировки IP: {str(e)}")
        return jsonify({'error': 'Ошибка разблокировки IP'}), 500


@admin_api_bp.route('/files')
@admin_required
def list_files():
    """Получение списка файлов"""
    try:
        path = request.args.get('path', '.')
        
        if not os.path.exists(path):
            return jsonify({'error': 'Путь не существует'}), 404
        
        files = []
        for item in os.listdir(path):
            item_path = os.path.join(path, item)
            files.append({
                'name': item,
                'type': 'directory' if os.path.isdir(item_path) else 'file',
                'size': os.path.getsize(item_path) if os.path.isfile(item_path) else 0,
                'modified': os.path.getmtime(item_path)
            })
        
        return jsonify({
            'success': True,
            'files': files,
            'current_path': path,
            'count': len(files),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения списка файлов: {str(e)}")
        return jsonify({'error': f'Ошибка получения списка файлов: {str(e)}'}), 500


@admin_api_bp.route('/file-content')
@admin_required
def get_file_content():
    """Получение содержимого файла"""
    try:
        filepath = request.args.get('path')
        
        if not filepath:
            return jsonify({'error': 'Путь к файлу не указан'}), 400
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Файл не найден'}), 404
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'content': content,
            'size': len(content),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка чтения файла: {str(e)}")
        return jsonify({'error': f'Ошибка чтения файла: {str(e)}'}), 500


@admin_api_bp.route('/save-file', methods=['POST'])
@admin_required
def save_file():
    """Сохранение файла"""
    try:
        data = request.get_json()
        filepath = data.get('path')
        content = data.get('content')
        
        if not filepath or content is None:
            return jsonify({'error': 'Путь и содержимое файла обязательны'}), 400
        
        # Создаем бэкап
        if os.path.exists(filepath):
            backup_path = f"{filepath}.backup.{int(time.time())}"
            shutil.copy2(filepath, backup_path)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return jsonify({
            'success': True,
            'filepath': filepath,
            'backup_created': os.path.exists(backup_path) if 'backup_path' in locals() else False,
            'message': 'Файл успешно сохранен',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка сохранения файла: {str(e)}")
        return jsonify({'error': f'Ошибка сохранения файла: {str(e)}'}), 500


@admin_api_bp.route('/execute', methods=['POST'])
@admin_required
def execute_command():
    """Выполнение команды терминала"""
    try:
        data = request.get_json()
        command = data.get('command', '')
        
        if not command:
            return jsonify({'error': 'Команда не указана'}), 400
        
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        return jsonify({
            'success': True,
            'command': command,
            'output': result.stdout,
            'error': result.stderr,
            'returncode': result.returncode,
            'timestamp': datetime.now().isoformat()
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Команда превысила лимит времени (30с)'}), 408
    except Exception as e:
        current_app.logger.error(f"Ошибка выполнения команды: {str(e)}")
        return jsonify({'error': f'Ошибка выполнения команды: {str(e)}'}), 500


@admin_api_bp.route('/system/restart', methods=['POST'])
@admin_required
def restart_system():
    """Перезагрузка системы"""
    try:
        # Логируем действие
        current_app.logger.info("Система перезагружается через API")
        
        # Запускаем перезагрузку в отдельном потоке
        import threading
        
        def restart_system_delayed():
            time.sleep(2)
            os.execv(sys.executable, ['python'] + sys.argv)
        
        thread = threading.Thread(target=restart_system_delayed, daemon=True)
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Система перезагружается...',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка перезагрузки системы: {str(e)}")
        return jsonify({'error': f'Ошибка перезагрузки системы: {str(e)}'}), 500


@admin_api_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """Создание резервной копии"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Копируем важные файлы и директории
        important_dirs = ['core', 'web', 'gui']
        important_files = ['main.py', 'requirements.txt', 'settings_nexus.ini']
        
        copied_items = []
        
        for dir_name in important_dirs:
            if os.path.exists(dir_name):
                shutil.copytree(dir_name, os.path.join(backup_dir, dir_name))
                copied_items.append(dir_name)
        
        for file_name in important_files:
            if os.path.exists(file_name):
                shutil.copy2(file_name, backup_dir)
                copied_items.append(file_name)
        
        backup_size = system_service._get_directory_size(backup_dir)
        
        return jsonify({
            'success': True,
            'backup_path': backup_dir,
            'backup_size': backup_size,
            'copied_items': copied_items,
            'message': f'Бэкап создан: {backup_dir}',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка создания бэкапа: {str(e)}")
        return jsonify({'error': f'Ошибка создания бэкапа: {str(e)}'}), 500


@admin_api_bp.route('/logs')
@admin_required
def get_logs():
    """Получение логов"""
    try:
        page = request.args.get('page', 1, type=int)
        level = request.args.get('level', 'all')
        limit = request.args.get('limit', 50, type=int)
        
        # Заглушка для логов (в реальном приложении здесь будет чтение файлов логов)
        sample_logs = [
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Система запущена успешно',
                'source': 'main.py'
            },
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'WARNING',
                'message': 'Высокая загрузка CPU',
                'source': 'monitor.py'
            },
            {
                'timestamp': datetime.now().isoformat(),
                'level': 'ERROR',
                'message': 'Ошибка подключения к базе данных',
                'source': 'db_utils.py'
            }
        ]
        
        # Фильтрация по уровню
        if level != 'all':
            sample_logs = [log for log in sample_logs if log['level'].lower() == level.lower()]
        
        # Пагинация
        start = (page - 1) * limit
        end = start + limit
        
        return jsonify({
            'success': True,
            'logs': sample_logs[start:end],
            'total': len(sample_logs),
            'page': page,
            'pages': (len(sample_logs) + limit - 1) // limit,
            'level': level,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка получения логов: {str(e)}")
        return jsonify({'error': f'Ошибка получения логов: {str(e)}'}), 500
