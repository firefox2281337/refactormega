# web/utils/logging_helper.py
"""
Вспомогательный модуль для логирования
"""

import hashlib
import logging
from datetime import datetime
from typing import Optional
from flask import current_app, request

from core.config.logger_config import setup_logger


class LoggingHelper:
    """Класс для упрощения логирования"""
    
    def __init__(self):
        self.logger = setup_logger()
    
    def log_user_access(self, page: str, message: str, level: str = "INFO"):
        """
        Логирует доступ пользователя к странице
        
        Args:
            page: Название страницы
            message: Сообщение для лога
            level: Уровень логирования
        """
        try:
            client_ip = request.remote_addr if request else "Unknown"
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            {message}:
                СТРАНИЦА: {page}
                ВРЕМЯ: {current_time}
                IP-адрес: {client_ip}"""
            
            self._log_with_level(log_message, level)
            self._emit_signal(log_message, level)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования доступа пользователя: {str(e)}")
    
    def log_api_request(self, endpoint: str, method: str, data: dict = None, 
                       response_code: int = None, error: str = None):
        """
        Логирует API запрос
        
        Args:
            endpoint: Конечная точка API
            method: HTTP метод
            data: Данные запроса
            response_code: Код ответа
            error: Ошибка (если есть)
        """
        try:
            client_ip = request.remote_addr if request else "Unknown"
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            API Запрос:
                ENDPOINT: {endpoint}
                МЕТОД: {method}
                ВРЕМЯ: {current_time}
                IP-адрес: {client_ip}"""
            
            if data:
                data_str = str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
                log_message += f"\n                ДАННЫЕ: {data_str}"
            
            if response_code:
                log_message += f"\n                КОД ОТВЕТА: {response_code}"
            
            if error:
                log_message += f"\n                ОШИБКА: {error}"
                level = "ERROR"
            else:
                level = "INFO"
            
            self._log_with_level(log_message, level)
            self._emit_signal(log_message, level)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования API запроса: {str(e)}")
    
    def log_query_info(self, database: str, sql_query: str = None, 
                      rows_count: int = None, error: str = None, 
                      execution_time: float = None):
        """
        Логирует информацию о SQL запросе
        
        Args:
            database: База данных
            sql_query: SQL запрос
            rows_count: Количество строк в результате
            error: Ошибка (если есть)
            execution_time: Время выполнения в секундах
        """
        try:
            client_ip = request.remote_addr if request else "Unknown"
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            if sql_query:
                sql_hash = hashlib.md5(sql_query.encode('utf-8')).hexdigest()[:16]
                log_message = f"""
                SQL Запрос:
                    ВРЕМЯ: {current_time}
                    IP-адрес: {client_ip}
                    БД: {database}
                    HASH: {sql_hash}"""
                
                if rows_count is not None:
                    log_message += f"\n                    СТРОК: {rows_count}"
                
                if execution_time is not None:
                    log_message += f"\n                    ВРЕМЯ ВЫПОЛНЕНИЯ: {execution_time:.3f}с"
                
                if error:
                    log_message += f"\n                    ОШИБКА: {error}"
                    level = "ERROR"
                else:
                    level = "INFO"
            else:
                log_message = f"""
                Запрос к БД:
                    ВРЕМЯ: {current_time}
                    IP-адрес: {client_ip}
                    БД: {database}"""
                level = "INFO"
            
            self._log_with_level(log_message, level)
            self._emit_signal(log_message, level)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования SQL запроса: {str(e)}")
    
    def log_file_operation(self, operation: str, filepath: str, 
                          success: bool = True, error: str = None,
                          file_size: int = None):
        """
        Логирует операции с файлами
        
        Args:
            operation: Тип операции (upload, download, delete, etc.)
            filepath: Путь к файлу
            success: Успешность операции
            error: Ошибка (если есть)
            file_size: Размер файла в байтах
        """
        try:
            client_ip = request.remote_addr if request else "Unknown"
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            Файловая операция:
                ОПЕРАЦИЯ: {operation}
                ФАЙЛ: {filepath}
                ВРЕМЯ: {current_time}
                IP-адрес: {client_ip}"""
            
            if file_size is not None:
                log_message += f"\n                РАЗМЕР: {file_size} байт"
            
            if not success and error:
                log_message += f"\n                ОШИБКА: {error}"
                level = "ERROR"
            else:
                log_message += f"\n                СТАТУС: {'УСПЕШНО' if success else 'НЕУДАЧА'}"
                level = "INFO" if success else "WARNING"
            
            self._log_with_level(log_message, level)
            self._emit_signal(log_message, level)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования файловой операции: {str(e)}")
    
    def log_security_event(self, event_type: str, details: str, 
                          severity: str = "INFO", user_agent: str = None):
        """
        Логирует события безопасности
        
        Args:
            event_type: Тип события
            details: Детали события
            severity: Серьезность (INFO, WARNING, ERROR, CRITICAL)
            user_agent: User Agent браузера
        """
        try:
            client_ip = request.remote_addr if request else "Unknown"
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            СОБЫТИЕ БЕЗОПАСНОСТИ:
                ТИП: {event_type}
                ВРЕМЯ: {current_time}
                IP-адрес: {client_ip}
                ДЕТАЛИ: {details}"""
            
            if user_agent:
                log_message += f"\n                USER-AGENT: {user_agent}"
            
            self._log_with_level(log_message, severity.upper())
            self._emit_signal(log_message, severity.upper())
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования события безопасности: {str(e)}")
    
    def log_processing_event(self, task_name: str, status: str, 
                           progress: int = None, message: str = None,
                           duration: float = None):
        """
        Логирует события обработки
        
        Args:
            task_name: Название задачи
            status: Статус (started, progress, completed, error)
            progress: Прогресс в процентах
            message: Дополнительное сообщение
            duration: Продолжительность в секундах
        """
        try:
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            Обработка:
                ЗАДАЧА: {task_name}
                СТАТУС: {status}
                ВРЕМЯ: {current_time}"""
            
            if progress is not None:
                log_message += f"\n                ПРОГРЕСС: {progress}%"
            
            if message:
                log_message += f"\n                СООБЩЕНИЕ: {message}"
            
            if duration is not None:
                log_message += f"\n                ДЛИТЕЛЬНОСТЬ: {duration:.3f}с"
            
            level = "ERROR" if status == "error" else "INFO"
            self._log_with_level(log_message, level)
            self._emit_signal(log_message, level)
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования события обработки: {str(e)}")
    
    def log_error(self, message: str, client_ip: Optional[str] = None, 
                 traceback_info: Optional[str] = None, context: Optional[dict] = None):
        """
        Логирует ошибку
        
        Args:
            message: Сообщение об ошибке
            client_ip: IP адрес клиента
            traceback_info: Информация о трассировке
            context: Дополнительный контекст
        """
        try:
            if not client_ip:
                client_ip = request.remote_addr if request else "Unknown"
                
            current_time = datetime.now().strftime("%Y.%m.%d %H:%M:%S")
            
            log_message = f"""
            ОШИБКА:
                СООБЩЕНИЕ: {message}
                ВРЕМЯ: {current_time}
                IP-адрес: {client_ip}"""
            
            if context:
                log_message += f"\n                КОНТЕКСТ: {str(context)}"
            
            if traceback_info:
                log_message += f"\n                ТРАССИРОВКА: {traceback_info}"
            
            self._log_with_level(log_message, "ERROR")
            self._emit_signal(log_message, "ERROR")
            
        except Exception as e:
            self.logger.error(f"Ошибка логирования ошибки: {str(e)}")
    
    def _log_with_level(self, message: str, level: str):
        """Логирует сообщение с указанным уровнем"""
        level = level.upper()
        if level == "DEBUG":
            self.logger.debug(message)
        elif level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "CRITICAL":
            self.logger.critical(message)
        else:
            self.logger.info(message)
    
    def _emit_signal(self, message: str, level: str):
        """Отправляет сигнал логирования"""
        try:
            log_signal_emitter = current_app.config.get('LOG_SIGNAL_EMITTER') if current_app else None
            if log_signal_emitter and hasattr(log_signal_emitter, 'log_signal'):
                log_signal_emitter.log_signal.emit(message, level)
        except Exception:
            # Игнорируем ошибки отправки сигналов
            pass


# Глобальный экземпляр логгера
logging_helper = LoggingHelper()

# Удобные функции для обратной совместимости
def log_user_access(page: str, client_ip: str, current_time: str, message: str, level: str = "INFO"):
    """Логирует доступ пользователя (для обратной совместимости)"""
    logging_helper.log_user_access(page, message, level)

def log_query_info(client_ip: str, current_time: str, data: dict, 
                  sql_query: str = None, database: str = None, 
                  rows_count: int = None, error: str = None):
    """Логирует SQL запрос (для обратной совместимости)"""
    logging_helper.log_query_info(database, sql_query, rows_count, error)

def log_error(message: str, client_ip: str = None, traceback_info: str = None):
    """Логирует ошибку (для обратной совместимости)"""
    logging_helper.log_error(message, client_ip, traceback_info)

def setup_simple_logger():
    """Настройка простого логгера"""
    logger = logging.getLogger('admin_panel')
    logger.setLevel(logging.INFO)
    
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger
