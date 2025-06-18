# web/services/lost_contracts_service.py
"""
Сервис для управления обработкой потерянных договоров.
Обрабатывает файлы с информацией о потерянных договорах.
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path
import re
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from web.utils.logging_helper import log_user_access


class LostContractsTask:
    """Класс для управления задачей обработки потерянных договоров"""
    
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_file = None
        self.cancelled = False
        self.start_time = None
        self.end_time = None
        self.task_id = None
        self.input_filename = None

    def reset(self):
        """Сброс состояния задачи"""
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_file = None
        self.cancelled = False
        self.start_time = None
        self.end_time = None
        self.task_id = str(uuid.uuid4())[:8]
        self.input_filename = None

    def start(self):
        """Запуск задачи"""
        self.is_running = True
        self.start_time = datetime.now()
        self.task_id = str(uuid.uuid4())[:8]

    def finish(self, success: bool = True, error: str = None):
        """Завершение задачи"""
        self.is_running = False
        self.end_time = datetime.now()
        if not success and error:
            self.error = error
            self.status = f"Ошибка: {error}"
        elif success:
            self.status = "Успешно выполнено!"
            self.progress = 100

    def update_progress(self, value: int):
        """Обновление прогреса выполнения"""
        self.progress = max(0, min(100, value))

    def update_status(self, status: str):
        """Обновление статуса выполнения"""
        self.status = status

    def cancel(self):
        """Отмена выполнения задачи"""
        self.cancelled = True
        self.status = "Отменено пользователем"
        self.finish(success=False)

    def get_duration(self) -> Optional[float]:
        """Получение длительности выполнения в секундах"""
        if self.start_time:
            end = self.end_time or datetime.now()
            return (end - self.start_time).total_seconds()
        return None

    def set_input_filename(self, filename: str):
        """Установка имени входного файла"""
        self.input_filename = filename


class LostContractsService:
    """Сервис для обработки файлов потерянных договоров"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.autoreg.logic.lost_contracts_logic"
    TEMP_DIR = Path("temp_uploads")
    RESULTS_DIR = Path("results")
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    FILE_PREFIX = 'Договора+по'
    
    def __init__(self):
        self.current_task = LostContractsTask()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        self.TEMP_DIR.mkdir(exist_ok=True)
        self.RESULTS_DIR.mkdir(exist_ok=True)
    
    def reload_business_logic(self) -> bool:
        """Динамическая перезагрузка модуля с бизнес-логикой"""
        try:
            if self.BUSINESS_LOGIC_MODULE in sys.modules:
                importlib.reload(sys.modules[self.BUSINESS_LOGIC_MODULE])
            else:
                importlib.import_module(self.BUSINESS_LOGIC_MODULE)
            return True
        except Exception as e:
            print(f"Ошибка при перезагрузке модуля: {e}")
            return False
    
    def _create_safe_filename(self, original_filename: str) -> str:
        """
        Создает безопасное имя файла с сохранением расширения
        
        Args:
            original_filename: Исходное имя файла
            
        Returns:
            str: Безопасное имя файла
        """
        # Получаем расширение
        if '.' in original_filename:
            name, ext = original_filename.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name = original_filename
            ext = ""
        
        # Убираем опасные символы
        safe_name = re.sub(r'[<>:"/\\|?*]', '', name)
        safe_name = re.sub(r'\s+', '_', safe_name.strip())
        
        # Если имя пустое после очистки, используем UUID
        if not safe_name:
            safe_name = str(uuid.uuid4())[:8]
        
        return safe_name + ext
    
    def validate_file(self, file) -> Tuple[bool, str]:
        """
        Валидация загружаемого файла
        
        Args:
            file: Файл для валидации
            
        Returns:
            Tuple[bool, str]: (валиден, сообщение об ошибке)
        """
        if not file or file.filename == '':
            return False, 'Файл не выбран'
            
        if not self._allowed_file(file.filename):
            return False, 'Недопустимый тип файла. Разрешены: ' + ', '.join(self.ALLOWED_EXTENSIONS)
        
        if not file.filename.startswith(self.FILE_PREFIX):
            return False, f'Файл должен начинаться с "{self.FILE_PREFIX}"'
            
        return True, ''
    
    def _allowed_file(self, filename: str) -> bool:
        """Проверка допустимого расширения файла"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def process_file(self, contracts_file, client_ip: str = None) -> Tuple[bool, str]:
        """
        Запуск обработки файла в отдельном потоке
        
        Args:
            contracts_file: Файл потерянных договоров
            client_ip: IP адрес клиента для логирования
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Проверяем не выполняется ли уже задача
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        # Валидируем файл
        valid, error_msg = self.validate_file(contracts_file)
        if not valid:
            return False, error_msg
        
        # Логируем начало обработки
        log_user_access(
            page="Lost Contracts Processing",
            client_ip=client_ip or "Unknown",
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Начало обработки потерянных договоров: {contracts_file.filename}"
        )
        
        # Сохраняем файл временно
        contracts_filename = self._create_safe_filename(contracts_file.filename)
        contracts_path = self.TEMP_DIR / contracts_filename
        
        try:
            contracts_file.save(contracts_path)
            print(f"Файл сохранен: {contracts_file.filename} -> {contracts_path}")
        except Exception as e:
            return False, f"Ошибка сохранения файла: {str(e)}"
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.set_input_filename(contracts_file.filename)
        self.current_task.start()
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(contracts_path,),
            name=f"LostContractsProcessing-{self.current_task.task_id}"
        )
        thread.daemon = True
        thread.start()
        
        return True, f"Обработка начата (ID: {self.current_task.task_id})"
    
    def _run_processing(self, contracts_path: Path):
        """Внутренний метод для выполнения обработки"""
        try:
            print(f"Начинаем обработку файла: {contracts_path}")
            
            # Перезагружаем бизнес-логику перед выполнением
            self.current_task.update_status("Загрузка бизнес-логики...")
            if not self.reload_business_logic():
                self.current_task.finish(success=False, error="Ошибка перезагрузки модуля")
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Запускаем обработку
            self.current_task.update_status("Обработка файла...")
            result_file = business_logic.process_lost_contracts(
                contracts_path,
                progress_callback=self.current_task.update_progress,
                status_callback=self.current_task.update_status,
                check_cancelled=lambda: self.current_task.cancelled
            )
            
            if self.current_task.cancelled:
                print("Обработка отменена пользователем")
                return
            
            self.current_task.result_file = result_file
            self.current_task.finish(success=True)
            
            print(f"Обработка завершена успешно. Результат: {result_file}")
            
        except Exception as e:
            error_msg = str(e)
            self.current_task.finish(success=False, error=error_msg)
            print(f"Ошибка при обработке: {error_msg}")
            print(traceback.format_exc())
        finally:
            # Очищаем временные файлы
            self._cleanup_temp_files(contracts_path)
    
    def _cleanup_temp_files(self, *file_paths):
        """Очистка временных файлов"""
        for file_path in file_paths:
            try:
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    print(f"Удален временный файл: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении временного файла {file_path}: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение текущего статуса обработки"""
        return {
            'is_running': self.current_task.is_running,
            'progress': self.current_task.progress,
            'status': self.current_task.status,
            'error': self.current_task.error,
            'has_result': self.current_task.result_file is not None,
            'task_id': self.current_task.task_id,
            'start_time': self.current_task.start_time.isoformat() if self.current_task.start_time else None,
            'duration': self.current_task.get_duration(),
            'cancelled': self.current_task.cancelled,
            'input_filename': self.current_task.input_filename
        }
    
    def cancel_processing(self) -> Dict[str, str]:
        """Отмена текущей обработки"""
        if not self.current_task.is_running:
            return {'message': 'Нет активной обработки для отмены', 'status': 'warning'}
        
        self.current_task.cancel()
        return {'message': 'Обработка отменена', 'status': 'success'}
    
    def get_result_file(self) -> Optional[str]:
        """Получение файла результата"""
        return self.current_task.result_file
    
    def reset_task(self):
        """Сброс текущей задачи"""
        if not self.current_task.is_running:
            self.current_task.reset()
            return True
        return False


# Создаем глобальный экземпляр сервиса
lost_contracts_service = LostContractsService()
