# web/services/excel_service.py
"""
Сервис для работы с Excel файлами
"""

import os
import io
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple

import pandas as pd
from werkzeug.utils import secure_filename

from web.utils.logging_helper import logging_helper
from web.utils.validators import validate_file_extension


class ExcelService:
    """Сервис для работы с Excel файлами"""
    
    def __init__(self):
        self.allowed_extensions = ['.xlsx', '.xls', '.xlsb']
        self.temp_dir = "temp_uploads"
        self._ensure_temp_directory()
    
    def _ensure_temp_directory(self):
        """Создает временную директорию если её нет"""
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
    
    def is_allowed_file(self, filename: str) -> bool:
        """Проверка разрешённого расширения файла"""
        return validate_file_extension(filename, self.allowed_extensions)
    
    def read_excel_headers(self, file_path: str, sheet_name: Union[str, int] = 0) -> List[str]:
        """
        Читает заголовки из Excel файла
        
        Args:
            file_path: Путь к файлу
            sheet_name: Название или номер листа
            
        Returns:
            list: Список заголовков
        """
        try:
            # Определяем движок по расширению файла
            engine = self._get_engine_for_file(file_path)
            
            df = pd.read_excel(file_path, sheet_name=sheet_name, nrows=0, engine=engine)
            return df.columns.tolist()
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка чтения заголовков из {file_path}: {str(e)}")
            raise Exception(f"Ошибка при чтении заголовков: {str(e)}")
    
    def read_excel_file(
        self, 
        file_path: str, 
        sheet_name: Union[str, int] = 0, 
        dtype: Any = str,
        nrows: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Читает Excel файл
        
        Args:
            file_path: Путь к файлу
            sheet_name: Название или номер листа
            dtype: Тип данных для чтения
            nrows: Количество строк для чтения
            
        Returns:
            pandas.DataFrame: DataFrame с данными файла
        """
        try:
            engine = self._get_engine_for_file(file_path)
            
            df = pd.read_excel(
                file_path, 
                sheet_name=sheet_name, 
                dtype=dtype,
                engine=engine,
                nrows=nrows
            )
            
            logging_helper.log_file_operation(
                operation="read_excel",
                filepath=file_path,
                success=True,
                file_size=os.path.getsize(file_path) if os.path.exists(file_path) else None
            )
            
            return df
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка чтения Excel файла {file_path}: {str(e)}")
            raise Exception(f"Ошибка при чтении Excel файла: {str(e)}")
    
    def save_to_excel(
        self, 
        data: Union[pd.DataFrame, List[List], Dict[str, pd.DataFrame]], 
        filename: str = "results.xlsx",
        save_to_file: bool = False
    ) -> io.BytesIO:
        """
        Сохраняет данные в Excel файл
        
        Args:
            data: Данные для сохранения
            filename: Имя файла
            save_to_file: Сохранить в файл или в память
            
        Returns:
            io.BytesIO: Объект BytesIO с Excel файлом
        """
        try:
            mem = io.BytesIO()
            
            with pd.ExcelWriter(mem, engine='xlsxwriter') as writer:
                if isinstance(data, pd.DataFrame):
                    # Одна таблица
                    data.fillna("", inplace=True)
                    data.to_excel(writer, sheet_name='Sheet1', index=False)
                    
                elif isinstance(data, dict):
                    # Несколько листов
                    for sheet_name, df in data.items():
                        if isinstance(df, pd.DataFrame):
                            df.fillna("", inplace=True)
                            df.to_excel(writer, sheet_name=sheet_name, index=False)
                            
                elif isinstance(data, list) and len(data) > 1:
                    # Список списков
                    headers = data[0]
                    data_rows = data[1:]
                    df = pd.DataFrame(data_rows, columns=headers)
                    df.fillna("", inplace=True)
                    df.to_excel(writer, sheet_name='Sheet1', index=False)
                    
                else:
                    raise ValueError("Неподдерживаемый формат данных")
            
            if save_to_file:
                file_path = os.path.join(self.temp_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(mem.getvalue())
                
                logging_helper.log_file_operation(
                    operation="save_excel",
                    filepath=file_path,
                    success=True,
                    file_size=len(mem.getvalue())
                )
            
            mem.seek(0)
            return mem
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка сохранения Excel файла: {str(e)}")
            raise Exception(f"Ошибка при сохранении Excel файла: {str(e)}")
    
    def upload_and_process_file(self, file) -> Dict[str, Any]:
        """
        Загружает файл и извлекает основную информацию
        
        Args:
            file: Файл из request.files
            
        Returns:
            dict: Информация о файле и его заголовках
        """
        if not file or file.filename == '':
            return {'success': False, 'error': 'Файл не выбран'}
        
        if not self.is_allowed_file(file.filename):
            return {'success': False, 'error': 'Недопустимый тип файла'}
        
        try:
            # Сохраняем файл во временную папку
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_filename = f"{timestamp}_{filename}"
            filepath = os.path.join(self.temp_dir, safe_filename)
            
            file.save(filepath)
            
            # Читаем информацию о файле
            headers = self.read_excel_headers(filepath)
            
            # Получаем размер файла
            file_size = os.path.getsize(filepath)
            
            # Считаем количество строк (читаем небольшой образец)
            try:
                sample_df = self.read_excel_file(filepath, nrows=1000)
                estimated_rows = len(sample_df)
                has_more_data = len(sample_df) == 1000
            except:
                estimated_rows = 0
                has_more_data = False
            
            logging_helper.log_file_operation(
                operation="upload_excel",
                filepath=filename,
                success=True,
                file_size=file_size
            )
            
            return {
                'success': True,
                'filepath': filepath,
                'filename': filename,
                'headers': headers,
                'file_size': file_size,
                'estimated_rows': estimated_rows,
                'has_more_data': has_more_data,
                'session_id': timestamp
            }
            
        except Exception as e:
            # Удаляем файл в случае ошибки
            if 'filepath' in locals() and os.path.exists(filepath):
                os.remove(filepath)
            
            logging_helper.log_error(f"Ошибка обработки загруженного файла: {str(e)}")
            return {'success': False, 'error': f'Ошибка при обработке файла: {str(e)}'}
    
    def generate_kasko_report(
        self, 
        quarter: str, 
        year: str, 
        branches: List[str], 
        base_path: str = r"\\vskportal3\SiteDirectory\cpp\DocLib1"
    ) -> io.BytesIO:
        """
        Генерирует отчёт КАСКО из нескольких Excel файлов
        
        Args:
            quarter: Квартал
            year: Год
            branches: Список номеров филиалов
            base_path: Базовый путь к файлам
            
        Returns:
            io.BytesIO: Объект BytesIO с объединённым Excel файлом
        """
        try:
            all_data = []
            processed_branches = []
            
            for branch in branches:
                try:
                    branch_num = int(branch)
                    df = self._read_kasko_file(branch_num, quarter, year, base_path)
                    
                    if df is not None and not df.empty:
                        # Добавляем информацию о филиале
                        df['Филиал'] = f"{branch_num:02d}"
                        all_data.append(df)
                        processed_branches.append(branch_num)
                        
                except ValueError:
                    logging_helper.log_error(f"Некорректный номер филиала: {branch}")
                    continue
                except Exception as e:
                    logging_helper.log_error(f"Ошибка обработки филиала {branch}: {str(e)}")
                    continue
            
            if not all_data:
                raise Exception("Не удалось найти данные ни для одного филиала")
            
            # Объединяем данные
            final_df = self._merge_dataframes(all_data)
            
            logging_helper.log_user_access(
                page="KASKO Report Generation",
                message=f"Сгенерирован отчет КАСКО: {quarter}кв {year}, филиалы: {processed_branches}"
            )
            
            return self.save_to_excel(final_df)
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка генерации отчета КАСКО: {str(e)}")
            raise Exception(f"Ошибка генерации отчёта: {str(e)}")
    
    def combine_excel_files(self, file_paths: List[str], add_source_column: bool = True) -> pd.DataFrame:
        """
        Объединяет несколько Excel файлов в один DataFrame
        
        Args:
            file_paths: Список путей к файлам
            add_source_column: Добавить колонку с источником файла
            
        Returns:
            pandas.DataFrame: Объединенные данные
        """
        try:
            combined_data = []
            
            for file_path in file_paths:
                if not os.path.exists(file_path):
                    logging_helper.log_error(f"Файл не найден: {file_path}")
                    continue
                
                try:
                    df = self.read_excel_file(file_path)
                    
                    if add_source_column:
                        df['Источник'] = os.path.basename(file_path)
                    
                    combined_data.append(df)
                    
                except Exception as e:
                    logging_helper.log_error(f"Ошибка чтения файла {file_path}: {str(e)}")
                    continue
            
            if not combined_data:
                raise Exception("Не удалось прочитать ни одного файла")
            
            return self._merge_dataframes(combined_data)
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка объединения файлов: {str(e)}")
            raise Exception(f"Ошибка объединения файлов: {str(e)}")
    
    def validate_excel_structure(self, file_path: str, required_columns: List[str]) -> Dict[str, Any]:
        """
        Валидирует структуру Excel файла
        
        Args:
            file_path: Путь к файлу
            required_columns: Обязательные колонки
            
        Returns:
            dict: Результат валидации
        """
        try:
            headers = self.read_excel_headers(file_path)
            
            missing_columns = []
            for col in required_columns:
                if col not in headers:
                    missing_columns.append(col)
            
            extra_columns = []
            for col in headers:
                if col not in required_columns:
                    extra_columns.append(col)
            
            is_valid = len(missing_columns) == 0
            
            return {
                'valid': is_valid,
                'headers': headers,
                'missing_columns': missing_columns,
                'extra_columns': extra_columns,
                'total_columns': len(headers)
            }
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка валидации файла {file_path}: {str(e)}")
            return {
                'valid': False,
                'error': str(e),
                'headers': [],
                'missing_columns': required_columns,
                'extra_columns': [],
                'total_columns': 0
            }
    
    def cleanup_temp_files(self, older_than_hours: int = 24) -> Dict[str, Any]:
        """
        Очищает старые временные файлы
        
        Args:
            older_than_hours: Файлы старше указанного количества часов
            
        Returns:
            dict: Статистика очистки
        """
        try:
            import time
            
            cutoff_time = time.time() - (older_than_hours * 3600)
            cleaned_count = 0
            cleaned_size = 0
            
            if os.path.exists(self.temp_dir):
                for file_path in Path(self.temp_dir).iterdir():
                    if file_path.is_file():
                        try:
                            file_stat = file_path.stat()
                            if file_stat.st_ctime < cutoff_time:
                                file_size = file_stat.st_size
                                file_path.unlink()
                                cleaned_count += 1
                                cleaned_size += file_size
                        except Exception as e:
                            logging_helper.log_error(f"Ошибка удаления файла {file_path}: {str(e)}")
            
            return {
                'success': True,
                'cleaned_files': cleaned_count,
                'cleaned_size_bytes': cleaned_size,
                'cleaned_size_mb': round(cleaned_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка очистки временных файлов: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_files': 0,
                'cleaned_size_bytes': 0,
                'cleaned_size_mb': 0
            }
    
    def _get_engine_for_file(self, file_path: str) -> Optional[str]:
        """Определяет движок для чтения файла по расширению"""
        ext = Path(file_path).suffix.lower()
        
        if ext == '.xlsb':
            return 'pyxlsb'
        elif ext in ['.xlsx', '.xls']:
            return None  # Используем движок по умолчанию
        else:
            return None
    
    def _read_kasko_file(self, branch_num: int, quarter: str, year: str, base_path: str) -> Optional[pd.DataFrame]:
        """Читает файл КАСКО для конкретного филиала"""
        folder_num = f"{branch_num:02d}"
        file_num_xlsx = f"{branch_num:04d}.xlsx"
        file_num_xlsb = f"{branch_num:04d}.xlsb"
        
        folder_path = os.path.join(
            base_path, folder_num, "Автодилеры", "Пролонгация",
            f"{quarter} квартал {year}"
        )
        
        file_path_xlsx = os.path.join(folder_path, file_num_xlsx)
        file_path_xlsb = os.path.join(folder_path, file_num_xlsb)
        
        # Пробуем сначала xlsx
        if os.path.exists(file_path_xlsx):
            try:
                return self.read_excel_file(file_path_xlsx, dtype=str)
            except Exception as e:
                logging_helper.log_error(f"Ошибка чтения {file_path_xlsx}: {str(e)}")
        
        # Затем xlsb
        if os.path.exists(file_path_xlsb):
            try:
                return self.read_excel_file(file_path_xlsb, dtype=str)
            except Exception as e:
                logging_helper.log_error(f"Ошибка чтения {file_path_xlsb}: {str(e)}")
        
        return None
    
    def _merge_dataframes(self, dataframes: List[pd.DataFrame]) -> pd.DataFrame:
        """Объединяет список DataFrame с обработкой различий в колонках"""
        if not dataframes:
            return pd.DataFrame()
        
        if len(dataframes) == 1:
            return dataframes[0]
        
        # Получаем все уникальные колонки
        all_columns = set()
        for df in dataframes:
            all_columns.update(df.columns)
        
        # Добавляем недостающие колонки в каждый DataFrame
        normalized_dfs = []
        for df in dataframes:
            missing_cols = all_columns - set(df.columns)
            if missing_cols:
                missing_df = pd.DataFrame({col: pd.NA for col in missing_cols}, index=df.index)
                df = pd.concat([df, missing_df], axis=1)
            normalized_dfs.append(df)
        
        # Объединяем все DataFrame
        final_df = pd.concat(normalized_dfs, ignore_index=True)
        final_df.fillna("", inplace=True)
        
        return final_df


# Глобальный экземпляр сервиса
excel_service = ExcelService()
