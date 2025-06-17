# web/blueprints/sql_routes.py
"""
Blueprint для SQL операций и работы с базами данных
"""

import json
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file

from web.services.sql_service import sql_service
from web.services.excel_service import excel_service
from web.utils.access_control import require_ip_access
from web.utils.logging_helper import logging_helper
from web.utils.validators import sanitize_string
from core.config.db_config import DATABASES

sql_bp = Blueprint('sql', __name__)


@sql_bp.route('/queries')
@require_ip_access
def sql_queries_page():
    """Страница для выполнения SQL-запросов"""
    try:
        last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        logging_helper.log_user_access(
            page="site/sql_queries.html",
            message="Пользователь зашёл на страницу SQL запросов"
        )
        
        # Получаем информацию о доступных базах данных
        db_info = {}
        for db_name, db_config in DATABASES.items():
            db_info[db_name] = {
                'name': db_name,
                'type': db_config.get('type', 'unknown'),
                'description': db_config.get('description', f'База данных {db_name}')
            }
        
        return render_template(
            'site/sql_queries.html',
            databases=db_info,
            last_check=last_check,
            total_databases=len(DATABASES)
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки страницы SQL запросов: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки страницы SQL"), 500


@sql_bp.route('/execute', methods=['POST'])
@require_ip_access
def execute_sql_query():
    """API endpoint для выполнения SQL запроса через веб-интерфейс"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не переданы'}), 400
        
        sql_query = data.get('sql_query', '').strip()
        database = data.get('database', '').strip()
        limit = data.get('limit', 1000)
        
        # Валидация входных данных
        if not sql_query:
            return jsonify({'error': 'SQL-запрос не может быть пустым'}), 400
        
        if not database:
            return jsonify({'error': 'База данных должна быть выбрана'}), 400
        
        if database not in DATABASES:
            return jsonify({'error': 'Неизвестная база данных'}), 400
        
        # Очищаем запрос
        sql_query = sanitize_string(sql_query, max_length=10000)
        
        # Логируем запрос
        logging_helper.log_query_info(
            database=database,
            sql_query=sql_query
        )
        
        # Выполняем запрос
        start_time = datetime.now()
        results = sql_service.execute_query(sql_query, database, limit=limit)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Логируем результат
        rows_count = len(results.get('rows', [])) if results.get('success') else 0
        logging_helper.log_query_info(
            database=database,
            sql_query=sql_query,
            rows_count=rows_count,
            execution_time=execution_time,
            error=results.get('error') if not results.get('success') else None
        )
        
        if results.get('success'):
            return jsonify({
                'success': True,
                'columns': results.get('columns', []),
                'rows': results.get('rows', []),
                'total_rows': rows_count,
                'execution_time': execution_time,
                'database': database
            })
        else:
            return jsonify({
                'success': False,
                'error': results.get('error', 'Неизвестная ошибка')
            }), 400
            
    except Exception as e:
        logging_helper.log_error(f"Ошибка выполнения SQL запроса: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Ошибка выполнения запроса: {str(e)}'
        }), 500


@sql_bp.route('/save-excel', methods=['POST'])
@require_ip_access
def save_query_results_to_excel():
    """API endpoint для сохранения результатов запроса в Excel"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не переданы'}), 400
        
        table_data = data.get('table_data')
        filename = data.get('filename', 'sql_results.xlsx')
        
        if not table_data or len(table_data) < 2:
            return jsonify({'error': 'Данные таблицы не предоставлены или неполные'}), 400
        
        # Очищаем имя файла
        filename = sanitize_string(filename, max_length=100)
        if not filename.endswith('.xlsx'):
            filename += '.xlsx'
        
        # Создаем Excel файл
        excel_file = excel_service.save_to_excel(table_data, filename)
        
        logging_helper.log_file_operation(
            operation="export_sql_to_excel",
            filepath=filename,
            success=True,
            file_size=len(excel_file.getvalue())
        )
        
        return send_file(
            excel_file,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка сохранения результатов в Excel: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Ошибка сохранения Excel: {str(e)}'
        }), 500


@sql_bp.route('/query', methods=['POST'])
def api_execute_query():
    """API endpoint для выполнения SQL запроса (внешний API)"""
    try:
        # Проверяем Content-Type
        if request.is_json:
            data = request.get_json()
        else:
            # Пробуем парсить как JSON из текста
            try:
                data = json.loads(request.data.decode('utf-8'))
            except:
                return jsonify({"error": "Неверный формат данных. Ожидается JSON"}), 400
        
        if not data:
            return jsonify({"error": "Данные не предоставлены"}), 400
        
        sql_query = data.get('query', '').strip()
        database = data.get('database', '').strip()
        
        # Валидация
        if not sql_query:
            return jsonify({"error": "SQL-запрос не предоставлен"}), 400
        
        if not database:
            return jsonify({"error": "База данных не указана"}), 400
        
        if database not in DATABASES:
            return jsonify({"error": f"Неизвестная база данных: {database}"}), 400
        
        # Логируем API запрос
        logging_helper.log_api_request(
            endpoint="sql/query",
            method="POST",
            data={'database': database, 'query_length': len(sql_query)}
        )
        
        # Выполняем запрос
        start_time = datetime.now()
        result = sql_service.execute_query_for_api(sql_query, database)
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Логируем результат
        if result.get('success'):
            rows_count = len(result.get('results', [{}])[0].get('rows', []))
            logging_helper.log_query_info(
                database=database,
                sql_query=sql_query,
                rows_count=rows_count,
                execution_time=execution_time
            )
        else:
            logging_helper.log_query_info(
                database=database,
                sql_query=sql_query,
                execution_time=execution_time,
                error=result.get('error')
            )
        
        return jsonify(result)
        
    except json.JSONDecodeError as e:
        logging_helper.log_api_request(
            endpoint="sql/query",
            method="POST",
            response_code=400,
            error="JSON decode error"
        )
        return jsonify({"error": f"Ошибка парсинга JSON: {str(e)}"}), 400
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка API выполнения запроса: {str(e)}")
        logging_helper.log_api_request(
            endpoint="sql/query",
            method="POST",
            response_code=500,
            error=str(e)
        )
        return jsonify({"error": f"Ошибка выполнения запроса: {str(e)}"}), 500


@sql_bp.route('/databases')
@require_ip_access
def get_databases_info():
    """API для получения информации о доступных базах данных"""
    try:
        db_info = {}
        
        for db_name, db_config in DATABASES.items():
            # Проверяем статус подключения
            connection_status = sql_service.test_connection(db_name)
            
            db_info[db_name] = {
                'name': db_name,
                'type': db_config.get('type', 'unknown'),
                'description': db_config.get('description', f'База данных {db_name}'),
                'status': 'connected' if connection_status else 'disconnected',
                'last_check': datetime.now().isoformat()
            }
        
        return jsonify({
            'success': True,
            'databases': db_info,
            'total': len(DATABASES)
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения информации о БД: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения информации о базах данных'
        }), 500


@sql_bp.route('/query-history')
@require_ip_access
def get_query_history():
    """API для получения истории запросов"""
    try:
        limit = request.args.get('limit', 50, type=int)
        database = request.args.get('database')
        
        # Получаем историю через сервис
        history = sql_service.get_query_history(limit=limit, database=database)
        
        return jsonify({
            'success': True,
            'history': history,
            'total': len(history)
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения истории запросов: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения истории запросов'
        }), 500


@sql_bp.route('/saved-queries')
@require_ip_access
def get_saved_queries():
    """API для получения сохраненных запросов"""
    try:
        saved_queries = sql_service.get_saved_queries()
        
        return jsonify({
            'success': True,
            'queries': saved_queries,
            'total': len(saved_queries)
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения сохраненных запросов: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения сохраненных запросов'
        }), 500


@sql_bp.route('/save-query', methods=['POST'])
@require_ip_access
def save_query():
    """API для сохранения запроса"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не переданы'}), 400
        
        query_name = data.get('name', '').strip()
        sql_query = data.get('query', '').strip()
        description = data.get('description', '').strip()
        database = data.get('database', '').strip()
        
        if not query_name or not sql_query:
            return jsonify({'error': 'Название и запрос обязательны'}), 400
        
        # Сохраняем запрос
        success = sql_service.save_query(query_name, sql_query, description, database)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Запрос успешно сохранен'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ошибка сохранения запроса'
            }), 500
            
    except Exception as e:
        logging_helper.log_error(f"Ошибка сохранения запроса: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка сохранения запроса'
        }), 500


@sql_bp.errorhandler(404)
def sql_not_found(error):
    """Обработчик ошибки 404 для SQL"""
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'SQL endpoint не найден'
        }), 404
    else:
        return render_template('site/error.html', 
                             error_code=404, 
                             error_message="SQL страница не найдена"), 404


@sql_bp.errorhandler(500)
def sql_server_error(error):
    """Обработчик ошибки 500 для SQL"""
    logging_helper.log_error(
        f"Внутренняя ошибка в SQL модуле: {str(error)}",
        context={'url': request.url, 'method': request.method}
    )
    
    if request.is_json:
        return jsonify({
            'success': False,
            'error': 'Внутренняя ошибка SQL сервера'
        }), 500
    else:
        return render_template('site/error.html', 
                             error_code=500, 
                             error_message="Ошибка SQL сервера"), 500
