# web/utils/access_control.py
"""
Модуль контроля доступа
"""

import ipaddress
from functools import wraps
from datetime import datetime, timedelta
from typing import List, Set, Dict
from flask import request, render_template, jsonify, current_app

from core.config.db_config import ALLOWED_IPS
from web.utils.logging_helper import logging_helper


class AccessController:
    """Класс для контроля доступа"""
    
    def __init__(self):
        self.allowed_ips: Set[str] = set(ALLOWED_IPS)
        self.blocked_ips: Set[str] = set()
        self.rate_limits: Dict[str, List[datetime]] = {}
        self.failed_attempts: Dict[str, int] = {}
        self.max_requests_per_minute = 60
        self.max_failed_attempts = 5
        self.block_duration_minutes = 30
    
    def is_ip_allowed(self, ip: str) -> bool:
        """
        Проверяет, разрешен ли доступ для IP
        
        Args:
            ip: IP адрес
            
        Returns:
            bool: True если доступ разрешен
        """
        if ip in self.blocked_ips:
            return False
        
        # Проверяем прямое совпадение
        if ip in self.allowed_ips:
            return True
        
        # Проверяем подсети
        try:
            ip_obj = ipaddress.ip_address(ip)
            for allowed_ip in self.allowed_ips:
                try:
                    if '/' in allowed_ip:  # Подсеть
                        network = ipaddress.ip_network(allowed_ip, strict=False)
                        if ip_obj in network:
                            return True
                    elif ip == allowed_ip:  # Точное совпадение
                        return True
                except ValueError:
                    continue
        except ValueError:
            return False
        
        return False
    
    def check_rate_limit(self, ip: str) -> bool:
        """
        Проверяет лимит запросов
        
        Args:
            ip: IP адрес
            
        Returns:
            bool: True если лимит не превышен
        """
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        # Инициализируем список для IP если его нет
        if ip not in self.rate_limits:
            self.rate_limits[ip] = []
        
        # Удаляем старые записи
        self.rate_limits[ip] = [
            timestamp for timestamp in self.rate_limits[ip] 
            if timestamp > minute_ago
        ]
        
        # Проверяем лимит
        if len(self.rate_limits[ip]) >= self.max_requests_per_minute:
            return False
        
        # Добавляем текущий запрос
        self.rate_limits[ip].append(now)
        return True
    
    def record_failed_attempt(self, ip: str):
        """
        Записывает неудачную попытку доступа
        
        Args:
            ip: IP адрес
        """
        self.failed_attempts[ip] = self.failed_attempts.get(ip, 0) + 1
        
        if self.failed_attempts[ip] >= self.max_failed_attempts:
            self.block_ip(ip, f"Превышено количество неудачных попыток: {self.failed_attempts[ip]}")
    
    def block_ip(self, ip: str, reason: str = ""):
        """
        Блокирует IP адрес
        
        Args:
            ip: IP адрес
            reason: Причина блокировки
        """
        self.blocked_ips.add(ip)
        logging_helper.log_security_event(
            "ip_blocked",
            f"IP {ip} заблокирован. Причина: {reason}",
            "WARNING"
        )
    
    def unblock_ip(self, ip: str):
        """
        Разблокирует IP адрес
        
        Args:
            ip: IP адрес
        """
        self.blocked_ips.discard(ip)
        self.failed_attempts.pop(ip, None)
        logging_helper.log_security_event(
            "ip_unblocked",
            f"IP {ip} разблокирован",
            "INFO"
        )
    
    def add_allowed_ip(self, ip: str):
        """
        Добавляет IP в список разрешенных
        
        Args:
            ip: IP адрес или подсеть
        """
        self.allowed_ips.add(ip)
        logging_helper.log_security_event(
            "ip_whitelisted",
            f"IP {ip} добавлен в белый список",
            "INFO"
        )
    
    def remove_allowed_ip(self, ip: str):
        """
        Удаляет IP из списка разрешенных
        
        Args:
            ip: IP адрес
        """
        self.allowed_ips.discard(ip)
        logging_helper.log_security_event(
            "ip_removed_from_whitelist",
            f"IP {ip} удален из белого списка",
            "INFO"
        )
    
    def clean_old_records(self):
        """Очищает старые записи"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        
        # Очищаем старые записи rate limit
        for ip in list(self.rate_limits.keys()):
            self.rate_limits[ip] = [
                timestamp for timestamp in self.rate_limits[ip] 
                if timestamp > hour_ago
            ]
            if not self.rate_limits[ip]:
                del self.rate_limits[ip]
    
    def get_stats(self) -> Dict:
        """Получает статистику доступа"""
        return {
            'allowed_ips_count': len(self.allowed_ips),
            'blocked_ips_count': len(self.blocked_ips),
            'rate_limited_ips': len(self.rate_limits),
            'failed_attempts': dict(self.failed_attempts),
            'blocked_ips': list(self.blocked_ips)
        }


# Глобальный экземпляр контроллера доступа
access_controller = AccessController()


def require_ip_access(f):
    """
    Декоратор для проверки IP адреса
    
    Args:
        f: Функция-обработчик маршрута
        
    Returns:
        Обёрнутая функция с проверкой доступа
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        
        # Проверяем IP доступ
        if not access_controller.is_ip_allowed(client_ip):
            logging_helper.log_security_event(
                "access_denied",
                f"Доступ запрещен для IP {client_ip}",
                "WARNING"
            )
            return render_template('site/error.html', remote_addr=client_ip), 403
        
        # Проверяем rate limit
        if not access_controller.check_rate_limit(client_ip):
            logging_helper.log_security_event(
                "rate_limit_exceeded",
                f"Превышен лимит запросов для IP {client_ip}",
                "WARNING"
            )
            return jsonify({'error': 'Превышен лимит запросов'}), 429
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_api_access(f):
    """
    Декоратор для проверки доступа к API
    
    Args:
        f: Функция-обработчик API
        
    Returns:
        Обёрнутая функция с проверкой доступа
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        client_ip = request.remote_addr
        
        # Проверяем IP доступ
        if not access_controller.is_ip_allowed(client_ip):
            logging_helper.log_api_request(
                endpoint=request.endpoint,
                method=request.method,
                response_code=403,
                error="IP доступ запрещен"
            )
            return jsonify({'error': 'Доступ запрещен'}), 403
        
        # Проверяем rate limit
        if not access_controller.check_rate_limit(client_ip):
            logging_helper.log_api_request(
                endpoint=request.endpoint,
                method=request.method,
                response_code=429,
                error="Превышен лимит запросов"
            )
            return jsonify({'error': 'Превышен лимит запросов'}), 429
        
        return f(*args, **kwargs)
    
    return decorated_function


def check_ip_access(client_ip: str) -> bool:
    """
    Проверка доступа по IP
    
    Args:
        client_ip: IP адрес для проверки
        
    Returns:
        bool: True если доступ разрешён
    """
    return access_controller.is_ip_allowed(client_ip)


def log_access_attempt(client_ip: str, page: str, success: bool = True, details: str = ""):
    """
    Логирование попытки доступа
    
    Args:
        client_ip: IP адрес
        page: Страница
        success: Успешность доступа
        details: Дополнительные детали
    """
    if success:
        logging_helper.log_user_access(page, f"Успешный доступ к {page}")
    else:
        access_controller.record_failed_attempt(client_ip)
        logging_helper.log_security_event(
            "access_denied",
            f"Отказ в доступе к {page}. {details}",
            "WARNING"
        )


def validate_user_agent(user_agent: str) -> bool:
    """
    Проверяет корректность User-Agent
    
    Args:
        user_agent: Строка User-Agent
        
    Returns:
        bool: True если User-Agent валидный
    """
    if not user_agent:
        return False
    
    # Проверяем на подозрительные паттерны
    suspicious_patterns = [
        'bot', 'crawler', 'spider', 'scraper', 'wget', 'curl'
    ]
    
    ua_lower = user_agent.lower()
    return not any(pattern in ua_lower for pattern in suspicious_patterns)


def check_request_headers() -> bool:
    """
    Проверяет заголовки запроса на подозрительность
    
    Returns:
        bool: True если заголовки нормальные
    """
    # Проверяем наличие обязательных заголовков для браузера
    if request.headers.get('Accept'):
        return True
    
    # Для API запросов проверяем Content-Type
    if request.is_json or request.headers.get('Content-Type'):
        return True
    
    return False
