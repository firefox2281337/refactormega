# web/blueprints/file_routes.py
"""
Blueprint для работы с файлами
"""

import os
from datetime import datetime
from collections import defaultdict
from flask import Blueprint, render_template, request, send_file, send_from_directory, jsonify, abort, flash, redirect, url_for

from web.services.file_service import file_service
from web.utils.logging_helper import logging_helper
from web.utils.access_control import require_ip_access
from web.utils.validators import validate_file_extension, sanitize_string

file_bp = Blueprint('files', __name__)


@file_bp.route('/software', methods=['GET', 'POST'])
@require_ip_access
def software_page():
    """Страница загрузки программного обеспечения"""
    try:
        last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        current_year = datetime.now().year
        
        # Получаем список файлов
        files = file_service.get_all_files()
        
        # Группируем файлы по категориям
        grouped_files = defaultdict(list)
        for file_info in files:
            grouped_files[file_info['category']].append(file_info)
        
        grouped_files = dict(grouped_files)
        
        # Логируем доступ
        logging_helper.log_user_access(
            page="site/software.html",
            message="Пользователь зашёл на страницу загрузки ПО"
        )
        
        return render_template(
            'site/software_download.html',
            current_year=current_year,
            last_check=last_check,
            grouped_files=grouped_files,
            total_files=len(files)
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки страницы ПО: {str(e)}")
        flash('Ошибка загрузки файлов', 'error')
        return render_template('site/error.html'), 500


@file_bp.route('/download/<file_id>')
@require_ip_access
def download_file(file_id):
    """Скачивание файла по ID"""
    try:
        # Валидируем ID файла
        file_id = sanitize_string(file_id, max_length=50)
        
        # Получаем информацию о файле
        file_info = file_service.get_file_by_id(file_id)
        
        if not file_info:
            logging_helper.log_file_operation(
                operation="download",
                filepath=f"file_id:{file_id}",
                success=False,
                error="Файл не найден"
            )
            abort(404)
        
        # Проверяем существование файла
        file_path = file_service.get_file_path(file_info['filename'])
        if not os.path.exists(file_path):
            logging_helper.log_file_operation(
                operation="download",
                filepath=file_path,
                success=False,
                error="Физический файл не найден"
            )
            abort(404)
        
        # Логируем скачивание
        file_size = os.path.getsize(file_path)
        logging_helper.log_file_operation(
            operation="download",
            filepath=file_info['filename'],
            success=True,
            file_size=file_size
        )
        
        # Увеличиваем счетчик скачиваний
        file_service.increment_download_count(file_id)
        
        return send_from_directory(
            file_service.files_dir,
            file_info['filename'],
            as_attachment=True,
            download_name=file_info.get('display_name', file_info['filename'])
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка скачивания файла {file_id}: {str(e)}")
        abort(500)


@file_bp.route('/preview/<file_id>')
@require_ip_access
def preview_file(file_id):
    """Превью файла"""
    try:
        # Валидируем ID файла
        file_id = sanitize_string(file_id, max_length=50)
        
        # Создаем превью
        preview_data = file_service.create_preview(file_id)
        
        if not preview_data:
            return jsonify({
                'success': False,
                'error': 'Файл не найден или не поддерживается предварительный просмотр'
            }), 404
        
        # Логируем просмотр превью
        logging_helper.log_file_operation(
            operation="preview",
            filepath=f"file_id:{file_id}",
            success=True
        )
        
        return jsonify({
            'success': True,
            'data': preview_data
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка создания превью для {file_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка создания превью'
        }), 500


@file_bp.route('/raw/<file_id>')
@require_ip_access
def raw_file(file_id):
    """Возвращает сырой файл для просмотра в браузере"""
    try:
        # Валидируем ID файла
        file_id = sanitize_string(file_id, max_length=50)
        
        file_info = file_service.get_file_by_id(file_id)
        if not file_info:
            abort(404)
        
        file_path = file_service.get_file_path(file_info['filename'])
        if not os.path.exists(file_path):
            abort(404)
        
        # Проверяем безопасность типа файла для просмотра в браузере
        safe_extensions = ['.txt', '.md', '.json', '.xml', '.csv', '.log']
        if not validate_file_extension(file_info['filename'], safe_extensions):
            # Для небезопасных файлов возвращаем как attachment
            return send_file(file_path, as_attachment=True)
        
        # Логируем просмотр
        logging_helper.log_file_operation(
            operation="view_raw",
            filepath=file_info['filename'],
            success=True
        )
        
        return send_file(file_path)
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка просмотра raw файла {file_id}: {str(e)}")
        abort(500)


@file_bp.route('/info/<file_id>')
@require_ip_access
def file_info(file_id):
    """Получение информации о файле"""
    try:
        # Валидируем ID файла
        file_id = sanitize_string(file_id, max_length=50)
        
        file_info = file_service.get_file_info(file_id)
        
        if not file_info:
            return jsonify({
                'success': False,
                'error': 'Файл не найден'
            }), 404
        
        return jsonify({
            'success': True,
            'data': file_info
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения информации о файле {file_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения информации о файле'
        }), 500


@file_bp.route('/search')
@require_ip_access
def search_files():
    """Поиск файлов"""
    try:
        query = request.args.get('q', '').strip()
        category = request.args.get('category', '').strip()
        file_type = request.args.get('type', '').strip()
        
        if not query and not category and not file_type:
            return jsonify({
                'success': False,
                'error': 'Не указаны параметры поиска'
            }), 400
        
        # Выполняем поиск
        search_results = file_service.search_files(
            query=query,
            category=category,
            file_type=file_type
        )
        
        logging_helper.log_user_access(
            page="files/search",
            message=f"Поиск файлов: '{query}', категория: '{category}', тип: '{file_type}'"
        )
        
        return jsonify({
            'success': True,
            'data': search_results,
            'count': len(search_results),
            'query': {
                'text': query,
                'category': category,
                'type': file_type
            }
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка поиска файлов: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка поиска файлов'
        }), 500


@file_bp.route('/categories')
@require_ip_access
def get_categories():
    """Получение списка категорий файлов"""
    try:
        categories = file_service.get_categories()
        
        return jsonify({
            'success': True,
            'data': categories
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения категорий: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения категорий'
        }), 500


@file_bp.route('/stats')
@require_ip_access
def file_stats():
    """Статистика файлов"""
    try:
        stats = file_service.get_file_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения статистики файлов: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статистики'
        }), 500


@file_bp.errorhandler(404)
def file_not_found(error):
    """Обработчик ошибки 404 для файлов"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Файл не найден'
        }), 404
    else:
        return render_template('site/error.html', 
                             error_code=404, 
                             error_message="Запрашиваемый файл не найден"), 404


@file_bp.errorhandler(500)
def file_server_error(error):
    """Обработчик ошибки 500 для файлов"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка сервера'
        }), 500
    else:
        return render_template('site/error.html', 
                             error_code=500, 
                             error_message="Ошибка сервера при работе с файлами"), 500
