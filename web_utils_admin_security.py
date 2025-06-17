# web/utils/admin_security.py
"""
Система безопасности админ панели
Многоуровневая защита доступа
"""

import hashlib
import secrets
import time
import json
import os
import logging
from functools import wraps
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional

from flask import request, session, redirect, url_for, abort, current_app
from werkzeug.security import check_password_hash, generate_password_hash

from web.utils.logging_helper import logging_helper

logger = logging.getLogger(__name__)


class AdminSecurity:
    """Класс для управления безопасностью админ панели"""
    
    def __init__(self):
        # Словари для отслеживания безопасности
        self.login_attempts: Dict[str, Dict] = {}
        self.active_sessions: Dict[str, Dict] = {}
        self.allowed_ips: Set[str] = set()
        self.blocked_ips: Set[str] = set()
        self.security_events: List[Dict] = []
        self.request_counts: Dict[str, List[float]] = {}
        
        # Настройки безопасности
        self.MAX_LOGIN_ATTEMPTS = 5
        self.BLOCK_DURATION = 900  # 15 минут блокировки
        self.SESSION_TIMEOUT = 3600  # 1 час таймаут сессии
        self.ADMIN_SECRET_KEY = os.environ.get('ADMIN_SECRET_KEY', 'change-me-in-production')
        self.MAX_REQUESTS_PER_MINUTE = 100
        self.MAX_SECURITY_EVENTS = 1000
        
        # Данные пользователей (в продакшене должно быть в БД)
        self.admin_users = {
            'admin': {
                'password_hash': generate_password_hash('admin123!@#'),
                'role': 'admin',
                'created': datetime.now().isoformat()
            },
            'superuser': {
                'password_hash': generate_password_hash('super456!@#'),
                'role': 'superuser',
                'created': datetime.now().isoformat()
            }
        }
        
        # Загружаем настройки из файла
        self.load_security_config()
    
    def load_security_config(self):
        """Загрузка конфигурации безопасности"""
        try:
            config_path = 'security_config.json'
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.allowed_ips = set(config.get('allowed_ips', []))
                    self.blocked_ips = set(config.get('blocked_ips', []))
                    self.MAX_LOGIN_ATTEMPTS = config.get('max_login_attempts', 5)
                    self.BLOCK_DURATION = config.get('block_duration', 900)
                    self.SESSION_TIMEOUT = config.get('session_timeout', 3600)
                    logger.info("Security configuration loaded")
        except Exception as e:
            logger.error(f"Error loading security config: {e}")
    
    def save_security_config(self):
        """Сохранение конфигурации безопасности"""
        try:
            config = {
                'allowed_ips': list(self.allowed_ips),
                'blocked_ips': list(self.blocked_ips),
                'max_login_attempts': self.MAX_LOGIN_ATTEMPTS,
                'block_duration': self.BLOCK_DURATION,
                'session_timeout': self.SESSION_TIMEOUT,
                'updated': datetime.now().isoformat()
            }
            with open('security_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            logger.info("Security configuration saved")
        except Exception as e:
            logger.error(f"Error saving security config: {e}")
    
    def log_security_event(self, event_type: str, message: str, severity: str = 'info', ip: Optional[str] = None):
        """Логирование событий безопасности"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'severity': severity,
            'ip': ip or self.get_client_ip(),
            'user_agent': request.headers.get('User-Agent', 'Unknown') if request else 'System',
            'user': session.get('admin_user', 'Anonymous') if session else 'System'
        }
        
        self.security_events.append(event)
        
        # Оставляем только последние события
        if len(self.security_events) > self.MAX_SECURITY_EVENTS:
            self.security_events = self.security_events[-self.MAX_SECURITY_EVENTS:]
        
        # Логируем через основную систему логирования
        logging_helper.log_security_event(event_type, message, severity.upper())
    
    def get_client_ip(self) -> str:
        """Получение реального IP клиента"""
        if not request:
            return "127.0.0.1"
        
        # Проверяем заголовки прокси
        forwarded_ips = request.headers.get('X-Forwarded-For')
        if forwarded_ips:
            return forwarded_ips.split(',')[0].strip()
        
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        return request.remote_addr or "127.0.0.1"
    
    def is_ip_blocked(self, ip: str) -> bool:
        """Проверка, заблокирован ли IP"""
        current_time = time.time()
        
        # Проверяем черный список
        if ip in self.blocked_ips:
            return True
        
        # Проверяем временную блокировку за превышение попыток входа
        if ip in self.login_attempts:
            attempt_data = self.login_attempts[ip]
            if 'blocked_until' in attempt_data and current_time < attempt_data['blocked_until']:
                return True
        
        return False
    
    def is_ip_allowed(self, ip: str) -> bool:
        """Проверка, разрешен ли IP (если используется белый список)"""
        if not self.allowed_ips:  # Если белый список пуст, разрешаем всем
            return True
        return ip in self.allowed_ips
    
    def record_login_attempt(self, ip: str, success: bool = False, username: Optional[str] = None):
        """Запись попытки входа"""
        current_time = time.time()
        
        if ip not in self.login_attempts:
            self.login_attempts[ip] = {'attempts': 0, 'last_attempt': current_time}
        
        attempt_data = self.login_attempts[ip]
        
        if success:
            # Успешный вход - сбрасываем счетчик
            self.login_attempts[ip] = {'attempts': 0, 'last_attempt': current_time}
            self.log_security_event(
                'login_success', 
                f'Successful admin login for user: {username}', 
                'info', 
                ip
            )
        else:
            # Неудачная попытка
            attempt_data['attempts'] += 1
            attempt_data['last_attempt'] = current_time
            
            self.log_security_event(
                'login_failed', 
                f'Failed admin login attempt for user: {username or "unknown"}', 
                'warning', 
                ip
            )
            
            # Блокируем IP если превышено количество попыток
            if attempt_data['attempts'] >= self.MAX_LOGIN_ATTEMPTS:
                attempt_data['blocked_until'] = current_time + self.BLOCK_DURATION
                self.blocked_ips.add(ip)  # Добавляем в постоянный черный список
                self.save_security_config()
                
                self.log_security_event(
                    'ip_blocked', 
                    f'IP blocked due to {self.MAX_LOGIN_ATTEMPTS} failed login attempts', 
                    'high', 
                    ip
                )
    
    def create_session(self, username: str, ip: str) -> str:
        """Создание безопасной сессии"""
        session_id = secrets.token_urlsafe(32)
        current_time = time.time()
        
        # Сохраняем информацию о сессии
        self.active_sessions[session_id] = {
            'user': username,
            'ip': ip,
            'created': current_time,
            'last_activity': current_time,
            'user_role': self.admin_users.get(username, {}).get('role', 'user')
        }
        
        # Устанавливаем сессию Flask
        session['admin_session_id'] = session_id
        session['admin_user'] = username
        session['admin_ip'] = ip
        session['admin_role'] = self.admin_users.get(username, {}).get('role', 'user')
        session.permanent = True
        
        self.log_security_event(
            'session_created', 
            f'Admin session created for user: {username}', 
            'info', 
            ip
        )
        
        return session_id
    
    def validate_session(self) -> bool:
        """Проверка валидности текущей сессии"""
        if not session or 'admin_session_id' not in session:
            return False
        
        session_id = session['admin_session_id']
        current_ip = self.get_client_ip()
        current_time = time.time()
        
        # Проверяем существование сессии
        if session_id not in self.active_sessions:
            return False
        
        session_data = self.active_sessions[session_id]
        
        # Проверяем IP адрес (защита от hijacking)
        if session_data['ip'] != current_ip:
            self.log_security_event(
                'session_hijack_attempt', 
                f'Session hijack attempt detected. Original IP: {session_data["ip"]}, Current IP: {current_ip}', 
                'high', 
                current_ip
            )
            self.destroy_session(session_id)
            return False
        
        # Проверяем таймаут сессии
        if current_time - session_data['last_activity'] > self.SESSION_TIMEOUT:
            self.log_security_event(
                'session_expired', 
                f'Admin session expired for user: {session_data["user"]}', 
                'info', 
                current_ip
            )
            self.destroy_session(session_id)
            return False
        
        # Обновляем время последней активности
        session_data['last_activity'] = current_time
        
        return True
    
    def destroy_session(self, session_id: Optional[str] = None):
        """Уничтожение сессии"""
        if session_id is None and session:
            session_id = session.get('admin_session_id')
        
        if session_id and session_id in self.active_sessions:
            user = self.active_sessions[session_id]['user']
            ip = self.active_sessions[session_id]['ip']
            
            del self.active_sessions[session_id]
            
            self.log_security_event(
                'session_destroyed', 
                f'Admin session destroyed for user: {user}', 
                'info', 
                ip
            )
        
        # Очищаем Flask сессию
        if session:
            session.pop('admin_session_id', None)
            session.pop('admin_user', None)
            session.pop('admin_ip', None)
            session.pop('admin_role', None)
    
    def verify_password(self, username: str, password: str) -> bool:
        """Проверка пароля администратора"""
        if username not in self.admin_users:
            return False
        
        user_data = self.admin_users[username]
        return check_password_hash(user_data['password_hash'], password)
    
    def check_rate_limit(self, ip: str) -> bool:
        """Проверка ограничения частоты запросов"""
        current_time = time.time()
        
        if ip not in self.request_counts:
            self.request_counts[ip] = []
        
        # Удаляем старые запросы (старше 1 минуты)
        self.request_counts[ip] = [
            req_time for req_time in self.request_counts[ip] 
            if current_time - req_time < 60
        ]
        
        # Добавляем текущий запрос
        self.request_counts[ip].append(current_time)
        
        # Проверяем лимит
        if len(self.request_counts[ip]) > self.MAX_REQUESTS_PER_MINUTE:
            self.log_security_event(
                'rate_limit_exceeded', 
                f'Rate limit exceeded: {len(self.request_counts[ip])} requests in 1 minute', 
                'high', 
                ip
            )
            return False
        
        return True
    
    def detect_suspicious_activity(self) -> bool:
        """Обнаружение подозрительной активности"""
        if not request:
            return False
        
        suspicious_patterns = [
            'script>', '<iframe', 'javascript:', 'eval(',
            'union select', 'or 1=1', '../', '.env',
            'passwd', '/etc/', 'cmd.exe', 'powershell',
            'base64_decode', 'exec(', 'system(',
            'DROP TABLE', 'DELETE FROM'
        ]
        
        # Проверяем URL и параметры на подозрительные паттерны
        check_strings = [
            request.url,
            str(request.args),
            str(request.form),
            request.headers.get('User-Agent', ''),
            request.headers.get('Referer', ''),
            str(request.get_json(silent=True) or {})
        ]
        
        for check_str in check_strings:
            check_str_lower = check_str.lower()
            for pattern in suspicious_patterns:
                if pattern in check_str_lower:
                    self.log_security_event(
                        'suspicious_activity', 
                        f'Suspicious pattern detected: {pattern} in {check_str[:100]}', 
                        'high'
                    )
                    return True
        
        return False
    
    def add_user(self, username: str, password: str, role: str = 'admin') -> bool:
        """Добавление нового пользователя"""
        if username in self.admin_users:
            return False
        
        self.admin_users[username] = {
            'password_hash': generate_password_hash(password),
            'role': role,
            'created': datetime.now().isoformat()
        }
        
        self.log_security_event(
            'user_added',
            f'New admin user added: {username} with role: {role}',
            'info'
        )
        
        return True
    
    def remove_user(self, username: str) -> bool:
        """Удаление пользователя"""
        if username not in self.admin_users:
            return False
        
        # Не позволяем удалить последнего админа
        admin_count = sum(1 for user in self.admin_users.values() if user['role'] == 'admin')
        if admin_count <= 1 and self.admin_users[username]['role'] == 'admin':
            return False
        
        del self.admin_users[username]
        
        self.log_security_event(
            'user_removed',
            f'Admin user removed: {username}',
            'info'
        )
        
        return True
    
    def change_password(self, username: str, new_password: str) -> bool:
        """Изменение пароля пользователя"""
        if username not in self.admin_users:
            return False
        
        self.admin_users[username]['password_hash'] = generate_password_hash(new_password)
        
        self.log_security_event(
            'password_changed',
            f'Password changed for user: {username}',
            'info'
        )
        
        return True
    
    def get_security_stats(self) -> Dict:
        """Получение статистики безопасности"""
        current_time = time.time()
        
        # Считаем активные блокировки
        active_blocks = 0
        for ip, attempt_data in self.login_attempts.items():
            if 'blocked_until' in attempt_data and current_time < attempt_data['blocked_until']:
                active_blocks += 1
        
        # Последние события
        recent_events = [
            event for event in self.security_events[-10:]
            if event['severity'] in ['warning', 'high', 'critical']
        ]
        
        return {
            'active_sessions': len(self.active_sessions),
            'blocked_ips': len(self.blocked_ips),
            'active_blocks': active_blocks,
            'total_users': len(self.admin_users),
            'recent_critical_events': len(recent_events),
            'total_security_events': len(self.security_events)
        }
    
    def cleanup_old_data(self):
        """Очистка старых данных"""
        current_time = time.time()
        
        # Очищаем старые попытки входа
        for ip in list(self.login_attempts.keys()):
            attempt_data = self.login_attempts[ip]
            if current_time - attempt_data['last_attempt'] > 86400:  # 24 часа
                del self.login_attempts[ip]
        
        # Очищаем старые счетчики запросов
        for ip in list(self.request_counts.keys()):
            self.request_counts[ip] = [
                req_time for req_time in self.request_counts[ip] 
                if current_time - req_time < 3600  # 1 час
            ]
            if not self.request_counts[ip]:
                del self.request_counts[ip]


# Создаем глобальный экземпляр
admin_security = AdminSecurity()


# Декораторы безопасности
def admin_required(f):
    """Декоратор для проверки доступа администратора"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = admin_security.get_client_ip()
        
        # Проверяем заблокирован ли IP
        if admin_security.is_ip_blocked(client_ip):
            admin_security.log_security_event(
                'blocked_access_attempt', 
                'Access attempt from blocked IP', 
                'high', 
                client_ip
            )
            abort(403)  # Forbidden
        
        # Проверяем белый список (если используется)
        if not admin_security.is_ip_allowed(client_ip):
            admin_security.log_security_event(
                'unauthorized_ip_access', 
                'Access attempt from unauthorized IP', 
                'high', 
                client_ip
            )
            abort(403)  # Forbidden
        
        # Проверяем rate limiting
        if not admin_security.check_rate_limit(client_ip):
            abort(429)  # Too Many Requests
        
        # Проверяем подозрительную активность
        if admin_security.detect_suspicious_activity():
            abort(403)  # Forbidden
        
        # Проверяем валидность сессии
        if not admin_security.validate_session():
            return redirect(url_for('admin_auth.admin_login'))
        
        return f(*args, **kwargs)
    return decorated_function


def security_check(f):
    """Легкий декоратор для базовых проверок безопасности"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = admin_security.get_client_ip()
        
        # Базовые проверки
        if admin_security.is_ip_blocked(client_ip):
            abort(403)
        
        if not admin_security.check_rate_limit(client_ip):
            abort(429)
        
        return f(*args, **kwargs)
    return decorated_function


def require_role(required_role: str):
    """Декоратор для проверки роли пользователя"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not session or 'admin_role' not in session:
                abort(403)
            
            user_role = session['admin_role']
            
            # Иерархия ролей: superuser > admin > user
            role_hierarchy = {'superuser': 3, 'admin': 2, 'user': 1}
            
            if role_hierarchy.get(user_role, 0) < role_hierarchy.get(required_role, 0):
                admin_security.log_security_event(
                    'insufficient_privileges',
                    f'User {session.get("admin_user")} attempted to access {required_role} only function',
                    'warning'
                )
                abort(403)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
