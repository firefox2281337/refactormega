# web/blueprints/processing_routes.py
"""
Blueprint для маршрутов обработки файлов и данных
"""

import os
import io
import zipfile
from datetime import datetime, date
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, jsonify, send_file

from web.services.processing_service import processing_service, demo_processing_function
from web.services.data_service import data_service
from web.services.excel_service import excel_service
from web.services.file_service import file_service
from web.utils.access_control import require_ip_access
from web.utils.logging_helper import logging_helper
from web.utils.validators import validate_file_extension, sanitize_string

processing_bp = Blueprint('processing', __name__)

# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = ['.xlsx', '.xls']


@processing_bp.route('/status')
def get_processing_status():
    """Получение текущего статуса обработки"""
    try:
        status = processing_service.get_status()
        return jsonify({
            'success': True,
            'data': status
        })
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения статуса обработки: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статуса'
        }), 500


@processing_bp.route('/cancel', methods=['POST'])
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
        logging_helper.log_error(f"Ошибка отмены обработки: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка отмены обработки'
        }), 500


@processing_bp.route('/start-demo', methods=['POST'])
def start_demo_processing():
    """Запуск демонстрационной обработки"""
    try:
        data = request.get_json() or {}
        demo_data = data.get('data', 'test_data')
        
        # Запускаем демо-обработку
        success = processing_service.start_processing(demo_processing_function, demo_data)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Демо-обработка запущена'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Не удалось запустить обработку (возможно, уже выполняется другая задача)'
            }), 400
            
    except Exception as e:
        logging_helper.log_error(f"Ошибка запуска демо-обработки: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка запуска обработки'
        }), 500


@processing_bp.route('/history')
def get_processing_history():
    """Получение истории обработки"""
    try:
        limit = request.args.get('limit', type=int)
        history = processing_service.get_history(limit)
        
        return jsonify({
            'success': True,
            'data': history
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения истории обработки: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения истории'
        }), 500


@processing_bp.route('/kasko', methods=['GET', 'POST'])
@require_ip_access
def kasko_page():
    """Страница для сбора отчетов КАСКО"""
    try:
        current_year = datetime.now().year
        last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        
        if request.method == 'POST':
            selected_quarter = request.form.get('quarter')
            selected_year = request.form.get('year')
            selected_checkboxes = request.form.getlist('checkboxes')
            
            # Валидация данных
            if not selected_quarter or not selected_year:
                return jsonify({'error': 'Квартал и год обязательны для заполнения'}), 400
            
            # Логируем выгрузку
            logging_helper.log_user_access(
                page="KASKO Report",
                message=f"Выгрузка КАСКО: {selected_quarter}кв {selected_year}, филиалы: {selected_checkboxes}"
            )
            
            try:
                # Генерируем отчет через сервис
                report_file = excel_service.generate_kasko_report(
                    quarter=selected_quarter,
                    year=selected_year,
                    branches=selected_checkboxes
                )
                
                if report_file:
                    return send_file(
                        report_file,
                        as_attachment=True,
                        download_name=f'otchet_kasko_{selected_quarter}_kv_{selected_year}.xlsx',
                        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                    )
                else:
                    return jsonify({'error': 'Ошибка генерации отчёта'}), 500
                    
            except Exception as e:
                logging_helper.log_error(f"Ошибка генерации отчета КАСКО: {str(e)}")
                return jsonify({'error': f'Ошибка генерации отчёта: {str(e)}'}), 500
        
        # GET запрос - показываем страницу
        logging_helper.log_user_access(
            page="site/kasko.html",
            message="Пользователь зашёл на страницу КАСКО"
        )
        
        return render_template(
            'site/kasko.html',
            current_year=current_year,
            last_check=last_check
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы КАСКО: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки страницы КАСКО"), 500


@processing_bp.route('/megahelper', methods=['GET', 'POST'])
@require_ip_access
def megahelper_page():
    """Страница Megahelper для работы с данными"""
    try:
        last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        current_year = datetime.now().year
        
        if request.method == 'POST':
            # Обработка POST запросов для Megahelper
            try:
                # Получаем параметры запроса
                start_date = request.form.get('start_date')
                end_date = request.form.get('end_date')
                insurance_type = request.form.get('insurance_type')
                channel = request.form.get('channel')
                branch_code = request.form.get('branch_code')
                
                # Логируем запрос
                logging_helper.log_user_access(
                    page="Megahelper Data Request",
                    message=f"Запрос данных: {start_date} - {end_date}, тип: {insurance_type}"
                )
                
                # Получаем данные через сервис
                results = data_service.get_kasko_prolongation_data(
                    start_date=start_date,
                    end_date=end_date,
                    insurance_type=insurance_type.split(',') if insurance_type else None,
                    channel=channel,
                    branch_code=branch_code.split(',') if branch_code else None
                )
                
                if results:
                    return jsonify({
                        'success': True,
                        'data': results
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Данные не найдены'
                    }), 404
                    
            except Exception as e:
                logging_helper.log_error(f"Ошибка обработки запроса Megahelper: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': f'Ошибка обработки запроса: {str(e)}'
                }), 500
        
        # GET запрос - показываем страницу
        logging_helper.log_user_access(
            page="site/megahelper.html",
            message="Пользователь зашёл на страницу Megahelper"
        )
        
        return render_template(
            'site/megahelper.html',
            current_year=current_year,
            last_check=last_check
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы Megahelper: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки страницы Megahelper"), 500


@processing_bp.route('/metragi', methods=['GET', 'POST'])
@require_ip_access
def metragi_processing():
    """Обработка метражей"""
    try:
        if request.method == 'GET':
            last_check = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            
            logging_helper.log_user_access(
                page="site/metragi.html",
                message="Пользователь зашёл на страницу обработки метражей"
            )
            
            return render_template('site/metragi.html', last_check=last_check)
        
        # POST запрос - обработка файла
        if 'excel_file' not in request.files:
            return jsonify({'error': 'Файл не был загружен'}), 400
        
        file = request.files['excel_file']
        
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Валидация файла
        if not validate_file_extension(file.filename, ALLOWED_EXTENSIONS):
            return jsonify({'error': 'Недопустимый тип файла. Разрешены только .xlsx и .xls'}), 400
        
        try:
            # Логируем начало обработки
            logging_helper.log_file_operation(
                operation="process_metragi",
                filepath=file.filename,
                success=True
            )
            
            # Обрабатываем файл через сервис
            result_files = data_service.process_metragi_file(file)
            
            if result_files:
                # Создаём ZIP архив
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for filename, file_content in result_files:
                        zip_file.writestr(filename, file_content)
                zip_buffer.seek(0)
                
                logging_helper.log_user_access(
                    page="Metragi Processing",
                    message="Успешная обработка метражей"
                )
                
                today = date.today()
                return send_file(
                    zip_buffer,
                    as_attachment=True,
                    download_name=f"Метражи {today}.zip",
                    mimetype="application/zip"
                )
            else:
                return jsonify({'error': 'Ошибка обработки данных'}), 400
                
        except Exception as e:
            logging_helper.log_error(f"Ошибка обработки файла метражей: {str(e)}")
            return jsonify({'error': f'Ошибка обработки файла: {str(e)}'}), 400
            
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы метражей: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки страницы метражей"), 500


@processing_bp.route('/upload-file', methods=['POST'])
@require_ip_access
def upload_file():
    """Загрузка файла для обработки"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'Файл не найден'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Валидация файла
        if not validate_file_extension(file.filename, ALLOWED_EXTENSIONS):
            return jsonify({'error': 'Неподдерживаемый формат файла. Разрешены только .xlsx и .xls'}), 400
        
        # Сохраняем файл во временную папку
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{filename}"
        
        # Здесь должен быть код сохранения в temp директорию
        # Пока что возвращаем информацию о файле
        
        logging_helper.log_file_operation(
            operation="upload",
            filepath=filename,
            success=True
        )
        
        return jsonify({
            'success': True,
            'filename': filename,
            'session_id': timestamp,
            'message': f'Файл {filename} успешно загружен'
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки файла: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Ошибка загрузки файла: {str(e)}'
        }), 500


@processing_bp.route('/file-info/<session_id>')
@require_ip_access
def get_file_info(session_id):
    """Получение информации о загруженном файле"""
    try:
        # Валидация session_id
        session_id = sanitize_string(session_id, max_length=50)
        
        # Здесь должен быть код получения информации о файле по session_id
        # Пока что возвращаем заглушку
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'status': 'uploaded',
            'message': 'Файл готов к обработке'
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения информации о файле {session_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения информации о файле'
        }), 500


@processing_bp.route('/process-file', methods=['POST'])
@require_ip_access
def process_uploaded_file():
    """Обработка загруженного файла"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Данные не переданы'}), 400
        
        session_id = data.get('session_id')
        processing_type = data.get('type', 'default')
        options = data.get('options', {})
        
        if not session_id:
            return jsonify({'error': 'ID сессии не указан'}), 400
        
        # Здесь должен быть код запуска обработки файла
        # Пока что запускаем демо-обработку
        
        def file_processing_function(session_id, processing_type, options, processing_service=None):
            """Функция обработки файла"""
            if processing_service:
                processing_service.update_progress(10, "Загрузка файла...")
                
                # Имитация обработки
                import time
                for i in range(1, 10):
                    if processing_service.is_cancelled():
                        return {'success': False, 'error': 'Обработка отменена'}
                    
                    processing_service.update_progress(i * 10 + 10, f"Обработка этапа {i}...")
                    time.sleep(0.5)
                
                processing_service.update_progress(100, "Обработка завершена")
            
            return {
                'success': True,
                'message': 'Файл успешно обработан',
                'session_id': session_id,
                'type': processing_type,
                'results': {
                    'processed_records': 100,
                    'success_records': 95,
                    'error_records': 5
                }
            }
        
        # Запускаем обработку
        success = processing_service.start_processing(
            file_processing_function,
            session_id,
            processing_type, 
            options
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Обработка файла запущена'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Не удалось запустить обработку файла'
            }), 400
            
    except Exception as e:
        logging_helper.log_error(f"Ошибка обработки файла: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка обработки файла'
        }), 500


@processing_bp.route('/cleanup-temp', methods=['POST'])
@require_ip_access
def cleanup_temp_files():
    """Очистка временных файлов"""
    try:
        # Здесь должен быть код очистки временных файлов
        # Пока что возвращаем заглушку
        
        logging_helper.log_user_access(
            page="Cleanup Temp",
            message="Запрос очистки временных файлов"
        )
        
        return jsonify({
            'success': True,
            'message': 'Временные файлы очищены',
            'cleaned_files': 0,
            'cleaned_size_mb': 0
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка очистки временных файлов: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка очистки временных файлов'
        }), 500


@processing_bp.errorhandler(413)
def file_too_large(error):
    """Обработчик ошибки слишком большого файла"""
    return jsonify({
        'success': False,
        'error': 'Файл слишком большой. Максимальный размер: 16MB'
    }), 413


@processing_bp.errorhandler(400)
def bad_request(error):
    """Обработчик ошибки неверного запроса"""
    return jsonify({
        'success': False,
        'error': 'Неверный запрос'
    }), 400


@processing_bp.errorhandler(500)
def internal_server_error(error):
    """Обработчик внутренней ошибки сервера"""
    logging_helper.log_error(
        f"Внутренняя ошибка в processing: {str(error)}",
        context={'url': request.url, 'method': request.method}
    )
    return jsonify({
        'success': False,
        'error': 'Внутренняя ошибка сервера'
    }), 500
