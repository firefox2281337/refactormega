# web/services/registry_service.py
"""
Сервис для управления обработкой реестра сделок.
Обрабатывает файлы сделок, проверки и сотрудников.
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path
import re
import uuid
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List

from web.utils.logging_helper import log_user_access


class RegistryTask:
    """Класс для управления задачей обработки реестра"""
    
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
        self.processed_files = []

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
        self.processed_files = []

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

    def add_processed_file(self, filename: str, file_type: str):
        """Добавление обработанного файла"""
        self.processed_files.append({
            'filename': filename,
            'type': file_type,
            'timestamp': datetime.now().isoformat()
        })


class RegistryService:
    """Сервис для обработки файлов реестра сделок"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.autoreg.logic.registry_logic"
    TEMP_DIR = Path("temp_uploads")
    RESULTS_DIR = Path("results")
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    
    # Типы файлов реестра
    FILE_TYPES = {
        'deals': {'prefix': 'Сделки', 'required': True, 'multiple': False},
        'check': {'prefix': 'Проверка', 'required': True, 'multiple': False},
        'employee': {'prefix': 'empl', 'required': True, 'multiple': False}
    }
    
    def __init__(self):
        self.current_task = RegistryTask()
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
    
    def _allowed_file(self, filename: str) -> bool:
        """Проверка допустимого расширения файла"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def _identify_file_type(self, filename: str) -> Optional[str]:
        """Определение типа файла по имени"""
        for file_type, config in self.FILE_TYPES.items():
            if filename.startswith(config['prefix']):
                return file_type
        return None
    
    def validate_files(self, files) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Валидация загружаемых файлов
        
        Args:
            files: Список файлов для валидации
            
        Returns:
            Tuple[bool, str, Dict]: (валидны, сообщение об ошибке, группированные файлы)
        """
        if not files or len(files) < 3:
            return False, 'Необходимо загрузить минимум 3 файла', {}
        
        grouped_files = {
            'deals': None,
            'check': None,
            'employee': None,
            'unknown': []
        }
        
        for file in files:
            if not file or file.filename == '':
                continue
                
            if not self._allowed_file(file.filename):
                continue
            
            file_type = self._identify_file_type(file.filename)
            if file_type:
                if grouped_files[file_type] is None:
                    grouped_files[file_type] = file
                else:
                    return False, f'Найдено несколько файлов типа {file_type}', {}
            else:
                grouped_files['unknown'].append(file)
        
        # Проверяем наличие всех необходимых типов файлов
        missing_types = []
        for file_type, config in self.FILE_TYPES.items():
            if config['required'] and grouped_files[file_type] is None:
                missing_types.append(f'{config["prefix"]}*')
        
        if missing_types:
            return False, f'Не найдены файлы: {", ".join(missing_types)}', {}
        
        return True, '', grouped_files
    
    def process_files(self, deals_file, check_file, employee_file, client_ip: str = None) -> Tuple[bool, str]:
        """
        Запуск обработки файлов в отдельном потоке
        
        Args:
            deals_file: Файл сделок
            check_file: Файл проверки
            employee_file: Файл сотрудников
            client_ip: IP адрес клиента для логирования
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        # Проверяем не выполняется ли уже задача
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        # Валидируем файлы через список
        files = [deals_file, check_file, employee_file]
        valid, error_msg, grouped_files = self.validate_files(files)
        if not valid:
            return False, error_msg
        
        # Логируем начало обработки
        filenames = [f.filename for f in files if f.filename]
        log_user_access(
            page="Registry Processing",
            client_ip=client_ip or "Unknown",
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Начало обработки реестра: {', '.join(filenames)}"
        )
        
        # Сохраняем файлы временно
        temp_files = self._save_temp_files(grouped_files)
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.start()
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(temp_files,),
            name=f"RegistryProcessing-{self.current_task.task_id}"
        )
        thread.daemon = True
        thread.start()
        
        return True, f"Обработка начата (ID: {self.current_task.task_id})"
    
    def _save_temp_files(self, grouped_files: Dict[str, Any]) -> Dict[str, Path]:
        """Сохранение временных файлов"""
        temp_files = {}
        
        try:
            # Сохраняем файл сделок
            if grouped_files['deals']:
                file = grouped_files['deals']
                safe_filename = self._create_safe_filename(file.filename)
                file_path = self.TEMP_DIR / safe_filename
                file.save(file_path)
                temp_files['deals_path'] = file_path
                self.current_task.add_processed_file(file.filename, 'deals')
            
            # Сохраняем файл проверки
            if grouped_files['check']:
                file = grouped_files['check']
                safe_filename = self._create_safe_filename(file.filename)
                file_path = self.TEMP_DIR / safe_filename
                file.save(file_path)
                temp_files['check_path'] = file_path
                self.current_task.add_processed_file(file.filename, 'check')
            
            # Сохраняем файл сотрудников
            if grouped_files['employee']:
                file = grouped_files['employee']
                safe_filename = self._create_safe_filename(file.filename)
                file_path = self.TEMP_DIR / safe_filename
                file.save(file_path)
                temp_files['employee_path'] = file_path
                self.current_task.add_processed_file(file.filename, 'employee')
            
            print(f"Сохранили файлы:")
            print(f"  Сделки: {temp_files.get('deals_path')}")
            print(f"  Проверка: {temp_files.get('check_path')}")
            print(f"  Сотрудники: {temp_files.get('employee_path')}")
            
        except Exception as e:
            raise Exception(f"Ошибка сохранения файлов: {str(e)}")
        
        return temp_files
    
    def _run_processing(self, temp_files: Dict[str, Path]):
        """Внутренний метод для выполнения обработки"""
        try:
            print(f"Начинаем обработку файлов реестра")
            
            # Перезагружаем бизнес-логику перед выполнением
            self.current_task.update_status("Загрузка бизнес-логики...")
            if not self.reload_business_logic():
                self.current_task.finish(success=False, error="Ошибка перезагрузки модуля")
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Запускаем обработку
            self.current_task.update_status("Обработка файлов...")
            result_file = business_logic.process_registry_files(
                temp_files['deals_path'], 
                temp_files['check_path'],
                temp_files['employee_path'],
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
            self._cleanup_temp_files(temp_files)
    
    def _cleanup_temp_files(self, temp_files: Dict[str, Path]):
        """Очистка временных файлов"""
        for file_type, file_path in temp_files.items():
            try:
                if file_path and Path(file_path).exists():
                    Path(file_path).unlink()
                    print(f"Удален временный файл {file_type}: {file_path}")
            except Exception as e:
                print(f"Ошибка при удалении временного файла {file_type}: {e}")
    
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
            'processed_files': self.current_task.processed_files
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
    
    def get_file_requirements(self) -> Dict[str, Dict]:
        """Получение требований к файлам"""
        return self.FILE_TYPES


# Создаем глобальный экземпляр сервиса
registry_service = RegistryService()
