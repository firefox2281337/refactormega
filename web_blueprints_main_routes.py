# web/blueprints/main_routes.py
"""
Blueprint для основных маршрутов приложения
"""

from flask import Blueprint, render_template, request, send_from_directory
from datetime import datetime

from web.services.system_service import system_service
from web.utils.logging_helper import logging_helper

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def server_status():
    """Главная страница с информацией о статусе сервера"""
    try:
        # Получаем кэшированные данные системы
        system_data = system_service.get_cached_system_info()
        db_statuses = system_service.get_cached_db_statuses()
        
        # Логируем доступ
        logging_helper.log_user_access(
            page="site/index.html",
            message="Пользователь зашёл на главную страницу"
        )
        
        return render_template(
            'site/index.html',
            system_info=system_data.get("system_info", {}),
            db_statuses=db_statuses,
            last_check=system_data.get("last_check", "Неизвестно")
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка на главной странице: {str(e)}")
        return render_template(
            'site/error.html',
            error_message="Ошибка загрузки главной страницы"
        ), 500


@main_bp.route('/server.ico')
def favicon():
    """Возвращает иконку сервера"""
    return send_from_directory('static', 'server.ico', mimetype='image/x-icon')


@main_bp.route('/about')
def about():
    """Страница о системе"""
    system_stats = system_service.get_detailed_system_stats()
    
    return render_template(
        'site/about.html',
        stats=system_stats,
        version="2.0.0",
        last_update=datetime.now().strftime("%d.%m.%Y")
    )


@main_bp.route('/status')
def detailed_status():
    """Детальная страница статуса"""
    try:
        # Получаем подробную информацию о системе
        system_stats = system_service.get_detailed_system_stats()
        db_statuses = system_service.get_database_statuses()
        
        return render_template(
            'site/status.html',
            system_stats=system_stats,
            db_statuses=db_statuses,
            timestamp=datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы статуса: {str(e)}")
        return render_template(
            'site/error.html',
            error_message="Ошибка загрузки страницы статуса"
        ), 500


@main_bp.errorhandler(404)
def not_found_error(error):
    """Обработчик ошибки 404"""
    logging_helper.log_user_access(
        page="404",
        message=f"Страница не найдена: {request.url}"
    )
    return render_template('site/error.html', error_code=404), 404


@main_bp.errorhandler(500)
def internal_error(error):
    """Обработчик ошибки 500"""
    logging_helper.log_error(
        f"Внутренняя ошибка сервера: {str(error)}",
        context={'url': request.url, 'method': request.method}
    )
    return render_template('site/error.html', error_code=500), 500
