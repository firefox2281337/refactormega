# web/services/system_service.py
"""
Сервис для работы с системной информацией и мониторингом
"""

import os
import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from core.config.db_config import DATABASES
from core.database.db_utils import check_database_status
from core.utils.helpers import get_server_uptime, get_cpu_usage, get_memory_usage, get_disk_usage


class SystemService:
    """Сервис для работы с системой и мониторингом"""
    
    def __init__(self):
        self.cached_data = {
            "system_info": {},
            "db_statuses": {},
            "last_update": None
        }
        self.cache_lock = threading.Lock()
        self.cache_duration = 30  # секунд
        self._start_background_cache_update()
    
    def _start_background_cache_update(self):
        """Запускает фоновое обновление кэша"""
        cache_thread = threading.Thread(target=self._update_cache_background, daemon=True)
        cache_thread.start()
    
    def _update_cache_background(self):
        """Фоновое обновление кэша"""
        while True:
            try:
                system_info = {
                    "uptime": get_server_uptime(),
                    "cpu": get_cpu_usage(),
                    "memory": get_memory_usage(),
                    "disk": get_disk_usage()
                }
                
                db_statuses = {}
                for db_name, config in DATABASES.items():
                    db_statuses[db_name] = check_database_status(config)
                
                with self.cache_lock:
                    self.cached_data["system_info"] = system_info
                    self.cached_data["db_statuses"] = db_statuses
                    self.cached_data["last_update"] = datetime.now()
                    
            except Exception as e:
                print(f"Ошибка обновления кэша: {e}")
            
            time.sleep(self.cache_duration)
    
    def get_cached_system_info(self) -> Dict[str, Any]:
        """Получение кэшированной системной информации"""
        with self.cache_lock:
            system_info = self.cached_data["system_info"].copy()
            last_update = self.cached_data["last_update"]
        
        if last_update:
            last_check = last_update.strftime("%d.%m.%Y %H:%M:%S")
        else:
            last_check = "Загрузка..."
        
        return {
            "system_info": system_info,
            "last_check": last_check
        }
    
    def get_cached_db_statuses(self) -> Dict[str, bool]:
        """Получение кэшированных статусов БД"""
        with self.cache_lock:
            return self.cached_data["db_statuses"].copy()
    
    def get_database_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Получение актуальных статусов баз данных"""
        statuses = {}
        
        for db_name, db_config in DATABASES.items():
            try:
                status = check_database_status(db_config)
                statuses[db_name] = {"status": "connected" if status else "disconnected"}
            except Exception as e:
                statuses[db_name] = {"status": "disconnected", "error": str(e)}
        
        return statuses
    
    def get_detailed_system_stats(self) -> Dict[str, Any]:
        """Получение детальной системной статистики для админки"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            process_count = len(psutil.pids())
            
            boot_time = psutil.boot_time()
            uptime = datetime.now() - datetime.fromtimestamp(boot_time)
            uptime_str = str(uptime).split('.')[0]
            
            project_size = self._get_directory_size('.')
            logs_size = self._get_directory_size('logs') if os.path.exists('logs') else 0
            backups_size = self._get_directory_size('backups') if os.path.exists('backups') else 0
            
            return {
                'system': {
                    'cpu_usage': round(cpu_percent, 1),
                    'memory_usage': round(memory.percent, 1),
                    'disk_usage': round(disk.percent, 1),
                    'process_count': process_count,
                    'uptime': uptime_str
                },
                'storage': {
                    'project_size': project_size,
                    'logs_size': logs_size,
                    'backups_size': backups_size,
                    'total_size': project_size + logs_size + backups_size
                }
            }
        except Exception as e:
            print(f"Ошибка получения системной статистики: {e}")
            return {}
    
    def get_performance_data(self, timeframe: str = '1h') -> Dict[str, Any]:
        """Получение данных производительности для графиков"""
        import random
        
        now = datetime.now()
        if timeframe == '1h':
            delta = timedelta(hours=1)
            intervals = 60
        elif timeframe == '6h':
            delta = timedelta(hours=6)
            intervals = 72
        elif timeframe == '24h':
            delta = timedelta(hours=24)
            intervals = 288
        else:  # 7d
            delta = timedelta(days=7)
            intervals = 168
        
        start_time = now - delta
        step = delta / intervals
        
        data = {
            'labels': [],
            'cpu': [],
            'memory': [],
            'disk': []
        }
        
        for i in range(intervals):
            timestamp = start_time + (step * i)
            data['labels'].append(timestamp.isoformat())
            data['cpu'].append(random.randint(10, 80))
            data['memory'].append(random.randint(30, 70))
            data['disk'].append(random.randint(20, 60))
        
        return data
    
    def calculate_system_health(self) -> int:
        """Расчет общего здоровья системы"""
        try:
            cpu_usage = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            health_score = 100
            
            if cpu_usage > 80:
                health_score -= 20
            elif cpu_usage > 60:
                health_score -= 10
            
            if memory.percent > 85:
                health_score -= 15
            elif memory.percent > 70:
                health_score -= 8
            
            return max(health_score, 0)
        except:
            return 50
    
    def _get_directory_size(self, path: str) -> int:
        """Получение размера директории"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    if os.path.exists(filepath):
                        total_size += os.path.getsize(filepath)
        except:
            pass
        return total_size


# Глобальный экземпляр сервиса
system_service = SystemService()
