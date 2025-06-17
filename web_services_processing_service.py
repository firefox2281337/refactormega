# web/services/processing_service.py
"""
Сервис для обработки файлов и фоновых задач
"""

import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from enum import Enum

from web.utils.logging_helper import log_error


class ProcessingStatus(Enum):
    """Статусы обработки"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"
    CANCELLED = "cancelled"


class ProcessingTask:
    """Класс для управления задачей обработки"""
    
    def __init__(self):
        self.status = ProcessingStatus.IDLE
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.cancel_event = threading.Event()
        self.thread = None
    
    def reset(self):
        """Сбрасывает состояние задачи"""
        self.status = ProcessingStatus.IDLE
        self.progress = 0
        self.message = ""
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.cancel_event.clear()
        self.thread = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразует задачу в словарь для API ответов"""
        return {
            'status': self.status.value,
            'progress': self.progress,
            'message': self.message,
            'result': self.result,
            'error': self.error,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else None
        }


class ProcessingService:
    """Сервис для обработки файлов и управления фоновыми задачами"""
    
    def __init__(self):
        self.current_task = ProcessingTask()
        self.task_history = []
        self.max_history = 50
    
    def start_processing(
        self, 
        process_func: Callable,
        *args, 
        **kwargs
    ) -> bool:
        """
        Запускает обработку в фоновом потоке
        
        Args:
            process_func: Функция для выполнения
            *args: Аргументы для функции
            **kwargs: Именованные аргументы для функции
            
        Returns:
            bool: True если задача запущена успешно
        """
        if self.current_task.status == ProcessingStatus.PROCESSING:
            return False  # Уже выполняется другая задача
        
        self.current_task.reset()
        self.current_task.status = ProcessingStatus.PROCESSING
        self.current_task.start_time = datetime.now()
        self.current_task.message = "Инициализация обработки..."
        
        # Запускаем обработку в отдельном потоке
        self.current_task.thread = threading.Thread(
            target=self._run_processing,
            args=(process_func, args, kwargs),
            daemon=True
        )
        self.current_task.thread.start()
        
        return True
    
    def cancel_processing(self) -> bool:
        """
        Отменяет текущую обработку
        
        Returns:
            bool: True если отмена успешна
        """
        if self.current_task.status != ProcessingStatus.PROCESSING:
            return False
        
        self.current_task.cancel_event.set()
        self.current_task.status = ProcessingStatus.CANCELLED
        self.current_task.end_time = datetime.now()
        self.current_task.message = "Обработка отменена"
        
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Получает текущий статус обработки
        
        Returns:
            dict: Статус текущей задачи
        """
        return self.current_task.to_dict()
    
    def update_progress(self, progress: int, message: str = ""):
        """
        Обновляет прогресс текущей задачи
        
        Args:
            progress: Прогресс от 0 до 100
            message: Сообщение о текущем состоянии
        """
        if self.current_task.status == ProcessingStatus.PROCESSING:
            self.current_task.progress = min(max(progress, 0), 100)
            if message:
                self.current_task.message = message
    
    def is_processing(self) -> bool:
        """Проверяет, выполняется ли обработка"""
        return self.current_task.status == ProcessingStatus.PROCESSING
    
    def is_cancelled(self) -> bool:
        """Проверяет, была ли отменена обработка"""
        return self.current_task.cancel_event.is_set()
    
    def get_history(self, limit: Optional[int] = None) -> list:
        """
        Получает историю задач
        
        Args:
            limit: Максимальное количество записей
            
        Returns:
            list: История выполненных задач
        """
        if limit:
            return self.task_history[-limit:]
        return self.task_history
    
    def _run_processing(self, process_func: Callable, args: tuple, kwargs: dict):
        """
        Выполняет обработку в фоновом потоке
        
        Args:
            process_func: Функция для выполнения
            args: Аргументы функции
            kwargs: Именованные аргументы функции
        """
        try:
            # Передаем self в kwargs чтобы функция могла обновлять прогресс
            kwargs['processing_service'] = self
            
            # Выполняем функцию
            result = process_func(*args, **kwargs)
            
            # Проверяем, не была ли отменена обработка
            if self.current_task.cancel_event.is_set():
                self.current_task.status = ProcessingStatus.CANCELLED
                self.current_task.message = "Обработка отменена"
            else:
                self.current_task.status = ProcessingStatus.COMPLETED
                self.current_task.progress = 100
                self.current_task.message = "Обработка завершена успешно"
                self.current_task.result = result
                
        except Exception as e:
            self.current_task.status = ProcessingStatus.ERROR
            self.current_task.error = str(e)
            self.current_task.message = f"Ошибка обработки: {str(e)}"
            log_error(f"Ошибка в фоновой обработке: {str(e)}")
            
        finally:
            self.current_task.end_time = datetime.now()
            
            # Добавляем в историю
            self._add_to_history()
    
    def _add_to_history(self):
        """Добавляет текущую задачу в историю"""
        task_copy = {
            'id': len(self.task_history) + 1,
            'status': self.current_task.status.value,
            'message': self.current_task.message,
            'start_time': self.current_task.start_time.isoformat() if self.current_task.start_time else None,
            'end_time': self.current_task.end_time.isoformat() if self.current_task.end_time else None,
            'duration': (self.current_task.end_time - self.current_task.start_time).total_seconds() 
                       if self.current_task.start_time and self.current_task.end_time else None,
            'error': self.current_task.error
        }
        
        self.task_history.append(task_copy)
        
        # Ограничиваем размер истории
        if len(self.task_history) > self.max_history:
            self.task_history = self.task_history[-self.max_history:]


def demo_processing_function(data, processing_service=None):
    """
    Демонстрационная функция обработки
    
    Args:
        data: Данные для обработки
        processing_service: Сервис обработки для обновления прогресса
    """
    if processing_service:
        processing_service.update_progress(10, "Начало обработки данных...")
        time.sleep(1)
        
        if processing_service.is_cancelled():
            return None
            
        processing_service.update_progress(30, "Валидация данных...")
        time.sleep(1)
        
        if processing_service.is_cancelled():
            return None
            
        processing_service.update_progress(60, "Обработка записей...")
        time.sleep(2)
        
        if processing_service.is_cancelled():
            return None
            
        processing_service.update_progress(90, "Формирование результата...")
        time.sleep(1)
        
        if processing_service.is_cancelled():
            return None
    
    return {"processed_records": 100, "success": True}


# Глобальный экземпляр сервиса
processing_service = ProcessingService()
