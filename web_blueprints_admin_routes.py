# web/blueprints/admin_routes.py
"""
Blueprint для административных маршрутов
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session

from web.utils.admin_security import admin_required, admin_security, require_role
from web.services.system_service import system_service
from web.utils.logging_helper import logging_helper

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.before_request
def before_request():
    """Проверка доступа перед каждым запросом к админке"""
    # Проверяем, не является ли это страницей входа
    if request.endpoint in ['admin_auth.admin_login', 'admin_auth.admin_logout']:
        return
    
    if not admin_security.validate_session():
        return redirect(url_for('admin_auth.admin_login'))


@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    """Главная страница дашборда"""
    try:
        # Получаем системную статистику
        system_stats = system_service.get_detailed_system_stats()
        
        # Добавляем статистику безопасности
        security_stats = admin_security.get_security_stats()
        
        # Объединяем все данные
        dashboard_data = {
            **system_stats,
            'security': security_stats,
            'current_user': session.get('admin_user', 'Unknown'),
            'user_role': session.get('admin_role', 'user')
        }
        
        logging_helper.log_user_access(
            page="admin/dashboard",
            message=f"Админ {session.get('admin_user')} зашел в дашборд"
        )
        
        return render_template('admin/dashboard.html', stats=dashboard_data)
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки дашборда: {str(e)}")
        flash('Ошибка загрузки дашборда', 'error')
        return redirect(url_for('admin_auth.admin_login'))


@admin_bp.route('/performance')
@admin_required
def performance_monitor():
    """Страница мониторинга производительности"""
    logging_helper.log_user_access(
        page="admin/performance",
        message="Просмотр мониторинга производительности"
    )
    return render_template('admin/performance.html')


@admin_bp.route('/logs')
@admin_required
def logs_viewer():
    """Страница просмотра логов"""
    logging_helper.log_user_access(
        page="admin/logs",
        message="Просмотр логов системы"
    )
    return render_template('admin/logs.html')


@admin_bp.route('/system')
@admin_required
def system_info():
    """Страница информации о системе"""
    try:
        system_stats = system_service.get_detailed_system_stats()
        
        return render_template('admin/system.html', stats=system_stats)
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки системной информации: {str(e)}")
        flash('Ошибка загрузки системной информации', 'error')
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/code-editor')
@admin_required
@require_role('admin')
def code_editor():
    """Редактор кода (только для админов)"""
    logging_helper.log_security_event(
        event_type="code_editor_access",
        details=f"Пользователь {session.get('admin_user')} получил доступ к редактору кода",
        severity="WARNING"
    )
    return render_template('admin/code_editor.html')


@admin_bp.route('/terminal')
@admin_required
@require_role('superuser')
def web_terminal():
    """Веб-терминал (только для суперпользователей)"""
    logging_helper.log_security_event(
        event_type="terminal_access",
        details=f"Суперпользователь {session.get('admin_user')} получил доступ к терминалу",
        severity="WARNING"
    )
    return render_template('admin/terminal.html')


@admin_bp.route('/config')
@admin_required
@require_role('admin')
def config_editor():
    """Редактор конфигурации"""
    logging_helper.log_security_event(
        event_type="config_editor_access",
        details=f"Админ {session.get('admin_user')} открыл редактор конфигурации",
        severity="INFO"
    )
    return render_template('admin/config.html')


@admin_bp.route('/security')
@admin_required
def security_center():
    """Центр безопасности"""
    try:
        security_data = {
            'active_sessions': len(admin_security.active_sessions),
            'blocked_ips': list(admin_security.blocked_ips),
            'recent_events': admin_security.security_events[-20:],
            'login_attempts': len(admin_security.login_attempts),
            'system_health': system_service.calculate_system_health(),
            'security_stats': admin_security.get_security_stats()
        }
        
        return render_template('admin/security.html', security_data=security_data)
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка загрузки центра безопасности: {str(e)}")
        flash('Ошибка загрузки центра безопасности', 'error')
        return redirect(url_for('admin.admin_dashboard'))


@admin_bp.route('/users')
@admin_required
@require_role('admin')
def user_management():
    """Управление пользователями"""
    users_data = {
        'users': admin_security.admin_users,
        'total_users': len(admin_security.admin_users),
        'active_sessions': len(admin_security.active_sessions)
    }
    
    return render_template('admin/users.html', users_data=users_data)


@admin_bp.route('/backup')
@admin_required
@require_role('admin')
def backup_manager():
    """Управление резервными копиями"""
    logging_helper.log_user_access(
        page="admin/backup",
        message="Доступ к менеджеру резервных копий"
    )
    return render_template('admin/backup.html')


@admin_bp.route('/scheduler')
@admin_required
@require_role('admin')
def task_scheduler():
    """Планировщик задач"""
    return render_template('admin/scheduler.html')


@admin_bp.route('/plugins')
@admin_required
@require_role('superuser')
def plugin_manager():
    """Менеджер плагинов"""
    return render_template('admin/plugins.html')


@admin_bp.route('/analytics')
@admin_required
def analytics_dashboard():
    """Аналитический дашборд"""
    # Заглушка для аналитических данных
    analytics_data = {
        'page_views': {
            'today': 156,
            'week': 1203,
            'month': 4567
        },
        'api_calls': {
            'today': 89,
            'week': 678,
            'month': 2340
        },
        'top_pages': [
            {'page': '/dashboard', 'visits': 156},
            {'page': '/nexus', 'visits': 89},
            {'page': '/files', 'visits': 67}
        ]
    }
    
    return render_template('admin/analytics.html', analytics_data=analytics_data)


@admin_bp.route('/settings')
@admin_required
@require_role('admin')
def admin_settings():
    """Настройки админ панели"""
    current_settings = {
        'session_timeout': admin_security.SESSION_TIMEOUT,
        'max_login_attempts': admin_security.MAX_LOGIN_ATTEMPTS,
        'block_duration': admin_security.BLOCK_DURATION,
        'max_requests_per_minute': admin_security.MAX_REQUESTS_PER_MINUTE
    }
    
    return render_template('admin/settings.html', settings=current_settings)


@admin_bp.errorhandler(403)
def admin_access_denied(error):
    """Обработчик ошибки доступа в админке"""
    logging_helper.log_security_event(
        event_type="admin_access_denied",
        details=f"Отказано в доступе к {request.url}",
        severity="WARNING"
    )
    flash('Недостаточно прав доступа', 'error')
    return render_template('admin/error.html', error_code=403), 403


@admin_bp.errorhandler(500)
def admin_internal_error(error):
    """Обработчик внутренних ошибок админки"""
    logging_helper.log_error(
        f"Внутренняя ошибка в админке: {str(error)}",
        context={'url': request.url, 'user': session.get('admin_user')}
    )
    flash('Внутренняя ошибка сервера', 'error')
    return render_template('admin/error.html', error_code=500), 500
