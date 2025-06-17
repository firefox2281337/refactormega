# web/services/sql_service.py
"""
Сервис для выполнения SQL операций
"""

import os
import json
import hashlib
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager

import pyodbc
import psycopg2
import oracledb

from core.config.db_config import DATABASES
from web.utils.logging_helper import logging_helper


class SQLConnectionError(Exception):
    """Ошибка подключения к базе данных"""
    pass


class SQLExecutionError(Exception):
    """Ошибка выполнения SQL запроса"""
    pass


class SQLService:
    """Сервис для работы с SQL базами данных"""
    
    def __init__(self):
        self.databases = DATABASES
        self.query_history_file = "sql_query_history.json"
        self.saved_queries_file = "sql_saved_queries.json"
        self.max_history_size = 1000
        self.default_limit = 1000
    
    def test_connection(self, database: str) -> bool:
        """
        Тестирует подключение к базе данных
        
        Args:
            database: Название базы данных
            
        Returns:
            bool: True если подключение успешно
        """
        try:
            with self._get_connection(database) as conn:
                if database == "PostgreSQL":
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                elif database in ["ACTUAR2", "adinsure_prod"]:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                elif database == "Oracle":
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1 FROM dual")
                        cursor.fetchone()
                
                return True
                
        except Exception as e:
            logging_helper.log_error(f"Ошибка тестирования подключения к {database}: {str(e)}")
            return False
    
    def execute_query(self, sql_query: str, database: str, limit: int = None) -> Dict[str, Any]:
        """
        Выполняет SQL запрос к указанной базе данных
        
        Args:
            sql_query: SQL запрос
            database: Название базы данных
            limit: Ограничение количества строк
            
        Returns:
            dict: Результат выполнения запроса
        """
        try:
            if database not in self.databases:
                return {
                    "success": False,
                    "error": f"Неизвестная база данных: {database}"
                }
            
            limit = limit or self.default_limit
            
            # Добавляем LIMIT к запросу если его нет
            limited_query = self._add_limit_to_query(sql_query, limit, database)
            
            # Выполняем запрос
            if database == "PostgreSQL":
                result = self._execute_postgresql(limited_query)
            elif database in ["ACTUAR2", "adinsure_prod"]:
                result = self._execute_mssql(limited_query, database)
            elif database == "Oracle":
                result = self._execute_oracle(limited_query)
            else:
                return {
                    "success": False,
                    "error": f"База данных {database} не поддерживается"
                }
            
            # Сохраняем в историю
            self._save_to_history(sql_query, database, result)
            
            return {
                "success": True,
                **result
            }
            
        except SQLConnectionError as e:
            error_msg = f"Ошибка подключения к {database}: {str(e)}"
            logging_helper.log_error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
            
        except SQLExecutionError as e:
            error_msg = f"Ошибка выполнения запроса: {str(e)}"
            logging_helper.log_error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"Неожиданная ошибка: {str(e)}"
            logging_helper.log_error(error_msg, traceback_info=traceback.format_exc())
            return {
                "success": False,
                "error": error_msg
            }
    
    def execute_query_for_api(self, sql_query: str, database: str) -> Dict[str, Any]:
        """
        Выполнение запроса через API (для внешних вызовов)
        
        Args:
            sql_query: SQL запрос
            database: База данных
            
        Returns:
            dict: Результат запроса в формате API
        """
        try:
            result = self.execute_query(sql_query, database)
            
            if result.get("success"):
                # Адаптируем формат для API совместимости
                if database in ["ACTUAR2", "adinsure_prod"]:
                    # Для MS SQL возвращаем в старом формате с results
                    return {
                        "results": [{
                            "columns": result.get("columns", []),
                            "rows": [dict(zip(result.get("columns", []), row)) for row in result.get("rows", [])]
                        }]
                    }
                else:
                    # Для PostgreSQL и Oracle
                    columns = result.get("columns", [])
                    rows = result.get("rows", [])
                    return {
                        "columns": columns,
                        "rows": [dict(zip(columns, row)) for row in rows] if rows else []
                    }
            else:
                return {"error": result.get("error", "Неизвестная ошибка")}
                
        except Exception as e:
            error_message = f"Ошибка API выполнения запроса: {str(e)}"
            logging_helper.log_error(error_message, traceback_info=traceback.format_exc())
            return {"error": error_message}
    
    def get_query_history(self, limit: int = 50, database: str = None) -> List[Dict[str, Any]]:
        """
        Получает историю выполненных запросов
        
        Args:
            limit: Ограничение количества записей
            database: Фильтр по базе данных
            
        Returns:
            list: История запросов
        """
        try:
            if not os.path.exists(self.query_history_file):
                return []
            
            with open(self.query_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # Фильтруем по базе данных если указана
            if database:
                history = [entry for entry in history if entry.get('database') == database]
            
            # Сортируем по времени (новые сначала) и ограничиваем
            history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
            return history[:limit]
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка получения истории запросов: {str(e)}")
            return []
    
    def get_saved_queries(self) -> List[Dict[str, Any]]:
        """
        Получает сохраненные запросы
        
        Returns:
            list: Сохраненные запросы
        """
        try:
            if not os.path.exists(self.saved_queries_file):
                return []
            
            with open(self.saved_queries_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logging_helper.log_error(f"Ошибка получения сохраненных запросов: {str(e)}")
            return []
    
    def save_query(self, name: str, query: str, description: str = "", database: str = "") -> bool:
        """
        Сохраняет запрос
        
        Args:
            name: Название запроса
            query: SQL запрос
            description: Описание
            database: База данных
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            saved_queries = self.get_saved_queries()
            
            # Проверяем, не существует ли уже запрос с таким именем
            for i, saved_query in enumerate(saved_queries):
                if saved_query.get('name') == name:
                    # Обновляем существующий
                    saved_queries[i] = {
                        'name': name,
                        'query': query,
                        'description': description,
                        'database': database,
                        'created': saved_query.get('created', datetime.now().isoformat()),
                        'updated': datetime.now().isoformat()
                    }
                    break
            else:
                # Добавляем новый
                saved_queries.append({
                    'name': name,
                    'query': query,
                    'description': description,
                    'database': database,
                    'created': datetime.now().isoformat(),
                    'updated': datetime.now().isoformat()
                })
            
            with open(self.saved_queries_file, 'w', encoding='utf-8') as f:
                json.dump(saved_queries, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка сохранения запроса: {str(e)}")
            return False
    
    def get_query_hash(self, sql_query: str) -> str:
        """Получение хеша SQL запроса для логирования"""
        return hashlib.md5(sql_query.encode('utf-8')).hexdigest()
    
    @contextmanager
    def _get_connection(self, database: str):
        """
        Контекстный менеджер для получения подключения к базе данных
        
        Args:
            database: Название базы данных
            
        Yields:
            connection: Объект подключения
        """
        conn = None
        try:
            if database == "PostgreSQL":
                conn = psycopg2.connect(**self.databases[database])
            elif database in ["ACTUAR2", "adinsure_prod"]:
                config = self.databases[database]
                conn = pyodbc.connect(
                    f"DRIVER={config['driver']};"
                    f"SERVER={config['server']};"
                    f"DATABASE={config['database']};"
                    f"Trusted_Connection={config['trusted_connection']};"
                )
            elif database == "Oracle":
                conn = oracledb.connect(
                    user=self.databases[database]["user"],
                    password=self.databases[database]["password"],
                    dsn=self.databases[database]["dsn"]
                )
            else:
                raise SQLConnectionError(f"Неподдерживаемая база данных: {database}")
            
            yield conn
            
        except Exception as e:
            raise SQLConnectionError(f"Не удалось подключиться к {database}: {str(e)}")
        finally:
            if conn:
                conn.close()
    
    def _execute_postgresql(self, sql_query: str) -> Dict[str, Any]:
        """Выполнение запроса к PostgreSQL"""
        with self._get_connection("PostgreSQL") as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql_query)
                    
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        return {
                            "columns": columns,
                            "rows": [list(row) for row in rows]
                        }
                    else:
                        return {"message": "Запрос выполнен успешно"}
                        
                except Exception as e:
                    raise SQLExecutionError(f"PostgreSQL ошибка: {str(e)}")
    
    def _execute_mssql(self, sql_query: str, database: str) -> Dict[str, Any]:
        """Выполнение запроса к MS SQL Server"""
        with self._get_connection(database) as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql_query)
                    
                    results = []
                    while True:
                        if cursor.description:
                            columns = [desc[0] for desc in cursor.description]
                            rows = cursor.fetchall()
                            results.append({
                                "columns": columns,
                                "rows": [list(row) for row in rows]
                            })
                        if not cursor.nextset():
                            break
                    
                    # Для совместимости возвращаем первый результат
                    if results:
                        return results[0]
                    else:
                        return {"message": "Запрос выполнен успешно"}
                        
                except Exception as e:
                    raise SQLExecutionError(f"MS SQL ошибка: {str(e)}")
    
    def _execute_oracle(self, sql_query: str) -> Dict[str, Any]:
        """Выполнение запроса к Oracle"""
        with self._get_connection("Oracle") as conn:
            with conn.cursor() as cursor:
                try:
                    cursor.execute(sql_query)
                    
                    if cursor.description:
                        columns = [desc[0] for desc in cursor.description]
                        rows = cursor.fetchall()
                        return {
                            "columns": columns,
                            "rows": [list(row) for row in rows]
                        }
                    else:
                        return {"message": "Запрос выполнен успешно"}
                        
                except Exception as e:
                    raise SQLExecutionError(f"Oracle ошибка: {str(e)}")
    
    def _add_limit_to_query(self, sql_query: str, limit: int, database: str) -> str:
        """
        Добавляет LIMIT к запросу если его нет
        
        Args:
            sql_query: Исходный запрос
            limit: Ограничение
            database: База данных
            
        Returns:
            str: Запрос с LIMIT
        """
        query_upper = sql_query.upper().strip()
        
        # Проверяем, есть ли уже LIMIT/TOP
        if any(keyword in query_upper for keyword in ['LIMIT', 'TOP', 'ROWNUM']):
            return sql_query
        
        # Добавляем ограничение в зависимости от типа БД
        if database == "PostgreSQL":
            return f"{sql_query.rstrip(';')} LIMIT {limit}"
        elif database in ["ACTUAR2", "adinsure_prod"]:
            # Для MS SQL добавляем TOP после SELECT
            if query_upper.startswith('SELECT'):
                return sql_query.replace('SELECT', f'SELECT TOP {limit}', 1)
        elif database == "Oracle":
            return f"SELECT * FROM ({sql_query}) WHERE ROWNUM <= {limit}"
        
        return sql_query
    
    def _save_to_history(self, sql_query: str, database: str, result: Dict[str, Any]):
        """
        Сохраняет запрос в историю
        
        Args:
            sql_query: SQL запрос
            database: База данных
            result: Результат выполнения
        """
        try:
            history = self.get_query_history(self.max_history_size)
            
            # Добавляем новую запись
            history_entry = {
                'query': sql_query[:1000],  # Ограничиваем длину запроса
                'query_hash': self.get_query_hash(sql_query),
                'database': database,
                'timestamp': datetime.now().isoformat(),
                'success': result.get('success', True),
                'rows_count': len(result.get('rows', [])) if result.get('rows') else 0,
                'error': result.get('error') if not result.get('success', True) else None
            }
            
            # Добавляем в начало списка
            history.insert(0, history_entry)
            
            # Ограничиваем размер истории
            history = history[:self.max_history_size]
            
            with open(self.query_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logging_helper.log_error(f"Ошибка сохранения в историю: {str(e)}")
    
    def cleanup_old_history(self, days_to_keep: int = 30):
        """
        Очищает старую историю запросов
        
        Args:
            days_to_keep: Количество дней для хранения истории
        """
        try:
            if not os.path.exists(self.query_history_file):
                return
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            with open(self.query_history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # Фильтруем историю
            filtered_history = []
            for entry in history:
                try:
                    entry_date = datetime.fromisoformat(entry.get('timestamp', ''))
                    if entry_date > cutoff_date:
                        filtered_history.append(entry)
                except:
                    # Если не удается парсить дату, оставляем запись
                    filtered_history.append(entry)
            
            with open(self.query_history_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_history, f, ensure_ascii=False, indent=2)
                
            logging_helper.log_user_access(
                page="SQL History Cleanup",
                message=f"Очищена история SQL запросов: удалено {len(history) - len(filtered_history)} записей"
            )
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка очистки истории: {str(e)}")


# Глобальный экземпляр сервиса
sql_service = SQLService()
