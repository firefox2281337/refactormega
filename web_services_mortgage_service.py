# web/services/mortgage_service.py
"""
Сервис для управления обработкой ипотечных реестров.
Обрабатывает загрузку файлов, сопоставление заголовков и обработку реестров.
"""

import sys
import importlib
import threading
import traceback
from pathlib import Path
import re
import uuid
import json
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List

from web.utils.logging_helper import log_user_access

try:
    import polars as pl
except ImportError:
    pl = None


class MortgageTask:
    """Класс для управления задачей обработки ипотечного реестра"""
    
    def __init__(self):
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_files = []  # Список файлов для скачивания
        self.cancelled = False
        self.start_time = None
        self.end_time = None
        self.task_id = None
        self.task_number = None

    def reset(self):
        """Сброс состояния задачи"""
        self.is_running = False
        self.progress = 0
        self.status = "Ожидание..."
        self.error = None
        self.result_files = []
        self.cancelled = False
        self.start_time = None
        self.end_time = None
        self.task_id = str(uuid.uuid4())[:8]
        self.task_number = None

    def start(self, task_number: int):
        """Запуск задачи"""
        self.is_running = True
        self.start_time = datetime.now()
        self.task_id = str(uuid.uuid4())[:8]
        self.task_number = task_number

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


class MortgageService:
    """Сервис для обработки ипотечных реестров"""
    
    BUSINESS_LOGIC_MODULE = "web.templates.nexus.automortgage.logic.mortgage_logic"
    TEMP_DIR = Path("temp_uploads")
    RESULTS_DIR = Path("results")
    CORRESPONDENCES_DIR = Path("correspondences")
    ALLOWED_EXTENSIONS = {'xls', 'xlsx'}
    
    def __init__(self):
        self.current_task = MortgageTask()
        self.uploaded_file_path = None
        self.file_headers = []
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Создание необходимых директорий"""
        self.TEMP_DIR.mkdir(exist_ok=True)
        self.RESULTS_DIR.mkdir(exist_ok=True)
        self.CORRESPONDENCES_DIR.mkdir(exist_ok=True)
    
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
        if '.' in original_filename:
            name, ext = original_filename.rsplit('.', 1)
            ext = f".{ext}"
        else:
            name = original_filename
            ext = ""
        
        safe_name = re.sub(r'[<>:"/\\|?*]', '', name)
        safe_name = re.sub(r'\s+', '_', safe_name.strip())
        
        if not safe_name:
            safe_name = str(uuid.uuid4())[:8]
        
        return safe_name + ext
    
    def _allowed_file(self, filename: str) -> bool:
        """Проверка допустимого расширения файла"""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.ALLOWED_EXTENSIONS
    
    def upload_excel_file(self, excel_file, client_ip: str = None) -> Dict[str, Any]:
        """
        Загрузка Excel файла и извлечение заголовков
        
        Args:
            excel_file: Загруженный Excel файл
            client_ip: IP адрес клиента для логирования
            
        Returns:
            Dict: Результат с заголовками или ошибкой
        """
        try:
            if not self._allowed_file(excel_file.filename):
                return {
                    'success': False,
                    'error': 'Недопустимый тип файла. Разрешены: ' + ', '.join(self.ALLOWED_EXTENSIONS)
                }
            
            # Логируем загрузку
            if client_ip:
                log_user_access(
                    page="Mortgage Upload",
                    client_ip=client_ip,
                    current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                    message=f"Загрузка ипотечного файла: {excel_file.filename}"
                )
            
            # Создаем безопасное имя файла
            safe_filename = self._create_safe_filename(excel_file.filename)
            file_path = self.TEMP_DIR / safe_filename
            
            # Сохраняем файл
            excel_file.save(file_path)
            self.uploaded_file_path = str(file_path)
            
            print(f"Файл сохранен: {file_path}")
            
            # Проверяем наличие Polars
            if pl is None:
                return {
                    'success': False,
                    'error': 'Библиотека Polars не установлена. Требуется для обработки Excel файлов.'
                }
            
            # Читаем заголовки из первой строки
            try:
                df = pl.read_excel(file_path, read_options={"n_rows": 1})
                self.file_headers = df.columns
            except Exception as e:
                # Fallback для старых версий Polars
                try:
                    df = pl.read_excel(file_path)
                    self.file_headers = df.columns
                except Exception as e2:
                    return {
                        'success': False,
                        'error': f'Ошибка чтения Excel файла: {str(e2)}'
                    }
            
            print(f"Извлечены заголовки: {self.file_headers}")
            
            return {
                'success': True,
                'headers': self.file_headers,
                'message': f'Файл загружен, найдено {len(self.file_headers)} заголовков'
            }
            
        except Exception as e:
            error_msg = f"Ошибка загрузки файла: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def auto_map_headers(self, register_type: str, template_headers: List[str], file_headers: List[str]) -> Dict[str, Any]:
        """
        Автоматическое сопоставление заголовков
        
        Args:
            register_type: Тип реестра
            template_headers: Заголовки шаблона
            file_headers: Заголовки файла
            
        Returns:
            Dict: Результат автоматического сопоставления
        """
        try:
            mappings = {}
            
            # Простое автоматическое сопоставление по совпадению
            for template_header in template_headers:
                # Ищем точное совпадение
                if template_header in file_headers:
                    mappings[template_header] = template_header
                    continue
                
                # Ищем частичное совпадение (без учета регистра)
                template_lower = template_header.lower()
                for file_header in file_headers:
                    file_lower = file_header.lower()
                    if template_lower in file_lower or file_lower in template_lower:
                        mappings[template_header] = file_header
                        break
            
            print(f"Автоматически сопоставлено {len(mappings)} заголовков")
            
            return {
                'success': True,
                'mappings': mappings,
                'message': f'Автоматически сопоставлено {len(mappings)} заголовков'
            }
            
        except Exception as e:
            error_msg = f"Ошибка автоматического сопоставления: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def save_correspondences(self, register_type: str, mappings: Dict[str, str]) -> Dict[str, Any]:
        """
        Сохранение соответствий заголовков
        
        Args:
            register_type: Тип реестра
            mappings: Словарь соответствий
            
        Returns:
            Dict: Результат сохранения
        """
        try:
            correspondences_file = self.CORRESPONDENCES_DIR / f"{register_type.lower()}_mappings.json"
            
            with open(correspondences_file, 'w', encoding='utf-8') as f:
                json.dump(mappings, f, ensure_ascii=False, indent=2)
            
            print(f"Соответствия сохранены в {correspondences_file}")
            
            return {
                'success': True,
                'message': f'Соответствия для {register_type} успешно сохранены'
            }
            
        except Exception as e:
            error_msg = f"Ошибка сохранения соответствий: {str(e)}"
            print(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
    
    def process_registry(self, task_number: int, register_type: str = "Ипотека", client_ip: str = None) -> Tuple[bool, str]:
        """
        Запуск обработки реестра в отдельном потоке
        
        Args:
            task_number: Номер задачи
            register_type: Тип реестра
            client_ip: IP адрес клиента для логирования
            
        Returns:
            Tuple[bool, str]: (успех, сообщение)
        """
        if self.current_task.is_running:
            return False, "Обработка уже выполняется"
        
        if not self.uploaded_file_path:
            return False, "Файл не загружен"
        
        # Проверяем наличие соответствий
        correspondences_file = self.CORRESPONDENCES_DIR / f"{register_type.lower()}_mappings.json"
        if not correspondences_file.exists():
            return False, "Соответствия заголовков не установлены"
        
        # Логируем начало обработки
        if client_ip:
            log_user_access(
                page="Mortgage Processing",
                client_ip=client_ip,
                current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
                message=f"Начало обработки ипотечного реестра: задача {task_number}, тип {register_type}"
            )
        
        # Запускаем обработку в отдельном потоке
        self.current_task.reset()
        self.current_task.start(task_number)
        
        thread = threading.Thread(
            target=self._run_processing,
            args=(task_number, register_type, correspondences_file),
            name=f"MortgageProcessing-{self.current_task.task_id}"
        )
        thread.daemon = True
        thread.start()
        
        return True, f"Обработка начата (ID: {self.current_task.task_id})"
    
    def _run_processing(self, task_number: int, register_type: str, correspondences_file: Path):
        """Внутренний метод для выполнения обработки"""
        try:
            print(f"Начинаем обработку реестра {register_type}, задача {task_number}")
            
            # Перезагружаем бизнес-логику перед выполнением
            self.current_task.update_status("Загрузка бизнес-логики...")
            if not self.reload_business_logic():
                self.current_task.finish(success=False, error="Ошибка перезагрузки модуля")
                return
            
            # Импортируем обновленный модуль
            business_logic = sys.modules[self.BUSINESS_LOGIC_MODULE]
            
            # Загружаем соответствия
            with open(correspondences_file, 'r', encoding='utf-8') as f:
                correspondences = json.load(f)
            
            # Запускаем обработку
            self.current_task.update_status("Обработка реестра...")
            result_files = business_logic.process_mortgage_registry(
                task_number,
                self.uploaded_file_path,
                correspondences,
                register_type,
                progress_callback=self.current_task.update_progress,
                status_callback=self.current_task.update_status,
                check_cancelled=lambda: self.current_task.cancelled
            )
            
            if self.current_task.cancelled:
                print("Обработка отменена пользователем")
                return
            
            self.current_task.result_files = result_files
            self.current_task.finish(success=True)
            
            print(f"Обработка завершена успешно. Созданы файлы: {result_files}")
            
        except Exception as e:
            error_msg = str(e)
            self.current_task.finish(success=False, error=error_msg)
            print(f"Ошибка при обработке: {error_msg}")
            print(traceback.format_exc())
        finally:
            # Очищаем временные файлы
            self._cleanup_temp_files()
    
    def _cleanup_temp_files(self):
        """Очистка временных файлов"""
        try:
            if self.uploaded_file_path and Path(self.uploaded_file_path).exists():
                Path(self.uploaded_file_path).unlink()
                print(f"Удален временный файл: {self.uploaded_file_path}")
                self.uploaded_file_path = None
        except Exception as e:
            print(f"Ошибка при удалении временных файлов: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Получение текущего статуса обработки"""
        return {
            'is_running': self.current_task.is_running,
            'progress': self.current_task.progress,
            'status': self.current_task.status,
            'error': self.current_task.error,
            'has_result': len(self.current_task.result_files) > 0,
            'files_count': len(self.current_task.result_files),
            'task_id': self.current_task.task_id,
            'task_number': self.current_task.task_number,
            'start_time': self.current_task.start_time.isoformat() if self.current_task.start_time else None,
            'duration': self.current_task.get_duration(),
            'cancelled': self.current_task.cancelled
        }
    
    def cancel_processing(self) -> Dict[str, str]:
        """Отмена текущей обработки"""
        if not self.current_task.is_running:
            return {'message': 'Нет активной обработки для отмены', 'status': 'warning'}
        
        self.current_task.cancel()
        return {'message': 'Обработка отменена', 'status': 'success'}
    
    def get_result_files(self) -> List[str]:
        """Получение списка файлов результата"""
        return self.current_task.result_files
    
    def reset_task(self):
        """Сброс текущей задачи"""
        if not self.current_task.is_running:
            self.current_task.reset()
            self.uploaded_file_path = None
            self.file_headers = []
            return True
        return False
    
    def get_uploaded_headers(self) -> List[str]:
        """Получение заголовков загруженного файла"""
        return self.file_headers
    
    def has_uploaded_file(self) -> bool:
        """Проверка наличия загруженного файла"""
        return self.uploaded_file_path is not None and Path(self.uploaded_file_path).exists()
    
    def get_default_template_headers(self, register_type: str = "Ипотека") -> List[str]:
        """Получение заголовков шаблона по умолчанию"""
        templates = {
            "Ипотека": [
                "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент",
                "Номер агентского договора", "Дата окончания страхования", "Прошлый период Страховая премия",
                "Прошлый период Страховая сумма", "Канал", "ID_внешней системы", "Кампания",
                "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "Приоритет",
                "Филиал ВСК", "Регион", "Объект страхования",
                "Плановая дата звонка CTI", "Вид полиса", "Скидка по спецпредложению",
                "Скидка к ПК", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации"
            ]
        }
        
        return templates.get(register_type, templates["Ипотека"])


# Создаем глобальный экземпляр сервиса
mortgage_service = MortgageService()
