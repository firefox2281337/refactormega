# web/blueprints/admin_auth.py
"""
Аутентификация и авторизация для админ панели
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from datetime import datetime

from web.utils.admin_security import admin_security, security_check
from web.utils.logging_helper import logging_helper

auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin')


@auth_bp.route('/login', methods=['GET', 'POST'])
@security_check
def admin_login():
    """Страница входа в админ панель"""
    # Если пользователь уже авторизован, перенаправляем в дашборд
    if admin_security.validate_session():
        return redirect(url_for('admin.admin_dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        client_ip = admin_security.get_client_ip()
        
        # Валидация входных данных
        if not username or not password:
            flash('Введите имя пользователя и пароль', 'error')
            return render_template('admin/login.html')
        
        # Проверяем, не заблокирован ли IP
        if admin_security.is_ip_blocked(client_ip):
            logging_helper.log_security_event(
                event_type="login_blocked_ip",
                details=f"Попытка входа с заблокированного IP: {client_ip}",
                severity="WARNING"
            )
            flash('Ваш IP адрес заблокирован', 'error')
            return render_template('admin/login.html')
        
        # Проверяем учетные данные
        if admin_security.verify_password(username, password):
            # Успешный вход
            admin_security.record_login_attempt(client_ip, success=True, username=username)
            session_id = admin_security.create_session(username, client_ip)
            
            logging_helper.log_security_event(
                event_type="admin_login_success",
                details=f"Успешный вход администратора: {username}",
                severity="INFO"
            )
            
            flash('Добро пожаловать в админ панель!', 'success')
            
            # Перенаправляем на изначально запрошенную страницу или дашборд
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            else:
                return redirect(url_for('admin.admin_dashboard'))
        else:
            # Неудачная попытка
            admin_security.record_login_attempt(client_ip, success=False, username=username)
            
            logging_helper.log_security_event(
                event_type="admin_login_failed",
                details=f"Неудачная попытка входа для пользователя: {username}",
                severity="WARNING"
            )
            
            flash('Неверные учетные данные', 'error')
    
    return render_template('admin/login.html')


@auth_bp.route('/logout', methods=['GET', 'POST'])
def admin_logout():
    """Выход из админ панели"""
    user = session.get('admin_user', 'Unknown')
    
    admin_security.destroy_session()
    
    logging_helper.log_security_event(
        event_type="admin_logout",
        details=f"Администратор вышел из системы: {user}",
        severity="INFO"
    )
    
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('admin_auth.admin_login'))


@auth_bp.route('/security-status')
@security_check
def security_status():
    """API для получения статуса безопасности"""
    try:
        security_stats = admin_security.get_security_stats()
        
        # Определяем уровень безопасности
        security_level = 'high'
        if security_stats['blocked_ips'] > 0:
            security_level = 'medium'
        if security_stats['recent_critical_events'] > 5:
            security_level = 'low'
        
        return jsonify({
            'success': True,
            'data': {
                **security_stats,
                'security_level': security_level,
                'last_update': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения статуса безопасности: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статуса безопасности'
        }), 500


@auth_bp.route('/session-info')
def session_info():
    """Информация о текущей сессии"""
    if not admin_security.validate_session():
        return jsonify({
            'success': False,
            'authenticated': False
        })
    
    session_id = session.get('admin_session_id')
    session_data = admin_security.active_sessions.get(session_id, {})
    
    return jsonify({
        'success': True,
        'authenticated': True,
        'user': session.get('admin_user'),
        'role': session.get('admin_role'),
        'ip': session.get('admin_ip'),
        'session_created': session_data.get('created'),
        'last_activity': session_data.get('last_activity'),
        'session_timeout': admin_security.SESSION_TIMEOUT
    })


@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Изменение пароля"""
    if not admin_security.validate_session():
        return redirect(url_for('admin_auth.admin_login'))
    
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        username = session.get('admin_user')
        
        # Валидация
        if not all([current_password, new_password, confirm_password]):
            flash('Заполните все поля', 'error')
            return render_template('admin/change_password.html')
        
        if new_password != confirm_password:
            flash('Новые пароли не совпадают', 'error')
            return render_template('admin/change_password.html')
        
        if len(new_password) < 8:
            flash('Пароль должен содержать минимум 8 символов', 'error')
            return render_template('admin/change_password.html')
        
        # Проверяем текущий пароль
        if not admin_security.verify_password(username, current_password):
            flash('Неверный текущий пароль', 'error')
            return render_template('admin/change_password.html')
        
        # Изменяем пароль
        if admin_security.change_password(username, new_password):
            logging_helper.log_security_event(
                event_type="password_changed",
                details=f"Пароль изменен для пользователя: {username}",
                severity="INFO"
            )
            flash('Пароль успешно изменен', 'success')
            return redirect(url_for('admin.admin_dashboard'))
        else:
            flash('Ошибка изменения пароля', 'error')
    
    return render_template('admin/change_password.html')


@auth_bp.route('/check-session', methods=['POST'])
def check_session():
    """AJAX проверка валидности сессии"""
    try:
        is_valid = admin_security.validate_session()
        
        return jsonify({
            'valid': is_valid,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка проверки сессии: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Ошибка проверки сессии'
        }), 500


@auth_bp.before_request
def before_request():
    """Выполняется перед каждым запросом"""
    # Очищаем старые данные безопасности
    admin_security.cleanup_old_data()


@auth_bp.errorhandler(429)
def rate_limit_handler(e):
    """Обработчик превышения лимита запросов"""
    logging_helper.log_security_event(
        event_type="rate_limit_auth",
        details="Превышен лимит запросов к аутентификации",
        severity="WARNING"
    )
    
    if request.is_json:
        return jsonify({
            'error': 'Превышен лимит запросов. Попробуйте позже.'
        }), 429
    else:
        flash('Слишком много запросов. Попробуйте позже.', 'error')
        return render_template('admin/login.html'), 429


@auth_bp.errorhandler(403)
def access_denied_handler(e):
    """Обработчик отказа в доступе"""
    if request.is_json:
        return jsonify({
            'error': 'Доступ запрещен'
        }), 403
    else:
        flash('Доступ запрещен', 'error')
        return render_template('admin/login.html'), 403
