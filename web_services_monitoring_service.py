# web/services/monitoring_service.py
"""
Сервис мониторинга системы для админской панели.
Обеспечивает сбор и анализ метрик производительности системы.
"""

import os
import json
import time
import threading
import subprocess
import platform
import socket
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
from dataclasses import dataclass, asdict
from enum import Enum

from web.utils.logging_helper import log_user_access

try:
    import psutil
except ImportError:
    psutil = None


class AlertSeverity(Enum):
    """Уровни серьезности алертов"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class MetricType(Enum):
    """Типы метрик"""
    CPU = "CPU"
    MEMORY = "MEMORY"
    DISK = "DISK"
    NETWORK = "NETWORK"
    PROCESS = "PROCESS"


@dataclass
class SystemAlert:
    """Системный алерт"""
    id: int
    severity: AlertSeverity
    category: MetricType
    message: str
    timestamp: datetime
    acknowledged: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь для JSON"""
        return {
            'id': self.id,
            'severity': self.severity.value,
            'category': self.category.value,
            'message': self.message,
            'timestamp': self.timestamp.isoformat(),
            'acknowledged': self.acknowledged
        }


@dataclass
class MetricPoint:
    """Точка метрики"""
    timestamp: datetime
    value: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        result = {
            'timestamp': self.timestamp.isoformat(),
            'value': self.value
        }
        if self.metadata:
            result.update(self.metadata)
        return result


@dataclass
class SystemMetrics:
    """Системные метрики"""
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    cpu_frequency: float
    memory_total: int
    memory_available: int
    memory_percent: float
    memory_used: int
    memory_free: int
    swap_total: int
    swap_used: int
    swap_percent: float
    disk_total: int
    disk_used: int
    disk_free: int
    disk_percent: float
    disk_read_bytes: int
    disk_write_bytes: int
    network_bytes_sent: int
    network_bytes_recv: int
    network_packets_sent: int
    network_packets_recv: int
    process_count: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Преобразование в словарь"""
        return asdict(self)


class SystemThresholds:
    """Пороговые значения для системных метрик"""
    
    def __init__(self):
        self.cpu_warning = 70.0
        self.cpu_critical = 90.0
        self.memory_warning = 80.0
        self.memory_critical = 95.0
        self.disk_warning = 85.0
        self.disk_critical = 95.0
        self.network_warning = 100.0  # МБ/сек
        self.network_critical = 500.0  # МБ/сек
    
    def update_thresholds(self, thresholds: Dict[str, float]):
        """Обновление пороговых значений"""
        for key, value in thresholds.items():
            if hasattr(self, key) and isinstance(value, (int, float)):
                setattr(self, key, float(value))


class MonitoringService:
    """Сервис мониторинга системы в реальном времени"""
    
    MAX_HISTORY_POINTS = 1440  # 24 часа по минутам
    MAX_ALERTS = 1000
    MONITORING_INTERVAL = 60  # секунд
    
    def __init__(self):
        self.metrics_history: Dict[str, deque] = {
            'cpu': deque(maxlen=self.MAX_HISTORY_POINTS),
            'memory': deque(maxlen=self.MAX_HISTORY_POINTS),
            'disk': deque(maxlen=self.MAX_HISTORY_POINTS),
            'network': deque(maxlen=self.MAX_HISTORY_POINTS)
        }
        
        self.alerts: List[SystemAlert] = []
        self.monitoring_active = False
        self.monitoring_thread: Optional[threading.Thread] = None
        self.thresholds = SystemThresholds()
        
        # Thread-safe лок для доступа к данным
        self._lock = threading.Lock()
        self._alert_counter = 0
        
        # Проверяем доступность psutil
        self._psutil_available = psutil is not None
        
        if not self._psutil_available:
            print("WARNING: psutil не установлен. Мониторинг будет работать в ограниченном режиме.")
    
    def start_monitoring(self):
        """Запуск фонового мониторинга"""
        with self._lock:
            if not self.monitoring_active:
                self.monitoring_active = True
                self.monitoring_thread = threading.Thread(
                    target=self._monitoring_loop, 
                    daemon=True,
                    name="SystemMonitoring"
                )
                self.monitoring_thread.start()
                print("Мониторинг системы запущен")
                return True
        return False
    
    def stop_monitoring(self):
        """Остановка мониторинга"""
        with self._lock:
            if self.monitoring_active:
                self.monitoring_active = False
        
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            self.monitoring_thread.join(timeout=5)
            print("Мониторинг системы остановлен")
            return True
        return False
    
    def is_monitoring_active(self) -> bool:
        """Проверка активности мониторинга"""
        with self._lock:
            return self.monitoring_active
    
    def _monitoring_loop(self):
        """Основной цикл мониторинга"""
        while self.monitoring_active:
            try:
                # Собираем метрики
                metrics = self._collect_system_metrics()
                
                if metrics:
                    # Сохраняем в историю (thread-safe)
                    with self._lock:
                        self._save_metrics_to_history(metrics)
                    
                    # Проверяем пороги
                    self._check_thresholds(metrics)
                
                time.sleep(self.MONITORING_INTERVAL)
                
            except Exception as e:
                print(f"Ошибка в мониторинге: {e}")
                time.sleep(10)
                
                # Проверяем нужно ли продолжать
                if not self.monitoring_active:
                    break
    
    def _collect_system_metrics(self) -> Optional[SystemMetrics]:
        """Сбор текущих метрик системы"""
        if not self._psutil_available:
            return self._generate_mock_metrics()
        
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            cpu_freq = psutil.cpu_freq()
            
            # Память
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            # Диск
            disk = psutil.disk_usage('/')
            
            try:
                disk_io = psutil.disk_io_counters()
            except:
                disk_io = None
            
            # Сеть
            try:
                network = psutil.net_io_counters()
            except:
                network = None
            
            # Процессы
            try:
                process_count = len(psutil.pids())
            except:
                process_count = 0
            
            return SystemMetrics(
                timestamp=datetime.now(),
                cpu_percent=cpu_percent,
                cpu_count=cpu_count,
                cpu_frequency=cpu_freq.current if cpu_freq else 0,
                memory_total=memory.total,
                memory_available=memory.available,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_free=memory.free,
                swap_total=swap.total,
                swap_used=swap.used,
                swap_percent=swap.percent,
                disk_total=disk.total,
                disk_used=disk.used,
                disk_free=disk.free,
                disk_percent=disk.percent,
                disk_read_bytes=disk_io.read_bytes if disk_io else 0,
                disk_write_bytes=disk_io.write_bytes if disk_io else 0,
                network_bytes_sent=network.bytes_sent if network else 0,
                network_bytes_recv=network.bytes_recv if network else 0,
                network_packets_sent=network.packets_sent if network else 0,
                network_packets_recv=network.packets_recv if network else 0,
                process_count=process_count
            )
            
        except Exception as e:
            print(f"Ошибка сбора метрик: {e}")
            return None
    
    def _generate_mock_metrics(self) -> SystemMetrics:
        """Генерация заглушки метрик при отсутствии psutil"""
        import random
        
        return SystemMetrics(
            timestamp=datetime.now(),
            cpu_percent=random.uniform(10, 60),
            cpu_count=4,
            cpu_frequency=2400,
            memory_total=8589934592,  # 8GB
            memory_available=4294967296,  # 4GB
            memory_percent=random.uniform(40, 80),
            memory_used=4294967296,
            memory_free=4294967296,
            swap_total=2147483648,  # 2GB
            swap_used=random.randint(0, 1073741824),
            swap_percent=random.uniform(0, 50),
            disk_total=107374182400,  # 100GB
            disk_used=random.randint(53687091200, 75161927680),  # 50-70GB
            disk_free=53687091200,
            disk_percent=random.uniform(50, 70),
            disk_read_bytes=random.randint(0, 1000000),
            disk_write_bytes=random.randint(0, 1000000),
            network_bytes_sent=random.randint(0, 10000000),
            network_bytes_recv=random.randint(0, 10000000),
            network_packets_sent=random.randint(0, 10000),
            network_packets_recv=random.randint(0, 10000),
            process_count=random.randint(80, 120)
        )
    
    def _save_metrics_to_history(self, metrics: SystemMetrics):
        """Сохранение метрик в историю (должно вызываться с _lock)"""
        timestamp = metrics.timestamp
        
        self.metrics_history['cpu'].append(MetricPoint(
            timestamp=timestamp,
            value=metrics.cpu_percent,
            metadata={'count': metrics.cpu_count, 'frequency': metrics.cpu_frequency}
        ))
        
        self.metrics_history['memory'].append(MetricPoint(
            timestamp=timestamp,
            value=metrics.memory_percent,
            metadata={
                'total': metrics.memory_total,
                'used': metrics.memory_used,
                'swap_percent': metrics.swap_percent
            }
        ))
        
        self.metrics_history['disk'].append(MetricPoint(
            timestamp=timestamp,
            value=metrics.disk_percent,
            metadata={
                'total': metrics.disk_total,
                'used': metrics.disk_used,
                'read_bytes': metrics.disk_read_bytes,
                'write_bytes': metrics.disk_write_bytes
            }
        ))
        
        # Вычисляем скорость сети (байт/сек)
        network_usage = 0
        if len(self.metrics_history['network']) > 0:
            prev_net = self.metrics_history['network'][-1]
            time_diff = (timestamp - prev_net.timestamp).total_seconds()
            if time_diff > 0:
                bytes_sent_rate = (metrics.network_bytes_sent - prev_net.metadata.get('bytes_sent', 0)) / time_diff
                bytes_recv_rate = (metrics.network_bytes_recv - prev_net.metadata.get('bytes_recv', 0)) / time_diff
                network_usage = (bytes_sent_rate + bytes_recv_rate) / (1024 * 1024)  # МБ/сек
        
        self.metrics_history['network'].append(MetricPoint(
            timestamp=timestamp,
            value=network_usage,
            metadata={
                'bytes_sent': metrics.network_bytes_sent,
                'bytes_recv': metrics.network_bytes_recv,
                'packets_sent': metrics.network_packets_sent,
                'packets_recv': metrics.network_packets_recv
            }
        ))
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """Проверка превышения пороговых значений"""
        timestamp = metrics.timestamp
        
        # Проверка CPU
        if metrics.cpu_percent >= self.thresholds.cpu_critical:
            self._create_alert(
                AlertSeverity.CRITICAL, 
                MetricType.CPU, 
                f'Критическая загрузка CPU: {metrics.cpu_percent:.1f}%',
                timestamp
            )
        elif metrics.cpu_percent >= self.thresholds.cpu_warning:
            self._create_alert(
                AlertSeverity.WARNING, 
                MetricType.CPU, 
                f'Высокая загрузка CPU: {metrics.cpu_percent:.1f}%',
                timestamp
            )
        
        # Проверка памяти
        if metrics.memory_percent >= self.thresholds.memory_critical:
            self._create_alert(
                AlertSeverity.CRITICAL, 
                MetricType.MEMORY, 
                f'Критическое использование памяти: {metrics.memory_percent:.1f}%',
                timestamp
            )
        elif metrics.memory_percent >= self.thresholds.memory_warning:
            self._create_alert(
                AlertSeverity.WARNING, 
                MetricType.MEMORY, 
                f'Высокое использование памяти: {metrics.memory_percent:.1f}%',
                timestamp
            )
        
        # Проверка диска
        if metrics.disk_percent >= self.thresholds.disk_critical:
            self._create_alert(
                AlertSeverity.CRITICAL, 
                MetricType.DISK, 
                f'Критическое заполнение диска: {metrics.disk_percent:.1f}%',
                timestamp
            )
        elif metrics.disk_percent >= self.thresholds.disk_warning:
            self._create_alert(
                AlertSeverity.WARNING, 
                MetricType.DISK, 
                f'Высокое заполнение диска: {metrics.disk_percent:.1f}%',
                timestamp
            )
    
    def _create_alert(self, severity: AlertSeverity, category: MetricType, message: str, timestamp: datetime):
        """Создание алерта (thread-safe)"""
        with self._lock:
            self._alert_counter += 1
            alert = SystemAlert(
                id=self._alert_counter,
                severity=severity,
                category=category,
                message=message,
                timestamp=timestamp
            )
            
            self.alerts.append(alert)
            
            # Ограничиваем количество алертов
            if len(self.alerts) > self.MAX_ALERTS:
                self.alerts = self.alerts[-500:]
        
        print(f"[{severity.value}] {category.value}: {message}")
    
    def get_real_time_metrics(self) -> Dict[str, Any]:
        """Получение метрик в реальном времени"""
        if not self._psutil_available:
            return self._get_mock_real_time_metrics()
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            try:
                processes = len(psutil.pids())
            except:
                processes = 0
            
            return {
                'cpu': round(cpu_percent, 1),
                'memory': round(memory.percent, 1),
                'disk': round(disk.percent, 1),
                'processes': processes,
                'timestamp': datetime.now().isoformat(),
                'psutil_available': True
            }
        except Exception as e:
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'psutil_available': False
            }
    
    def _get_mock_real_time_metrics(self) -> Dict[str, Any]:
        """Заглушка для реального времени без psutil"""
        import random
        
        return {
            'cpu': round(random.uniform(10, 60), 1),
            'memory': round(random.uniform(40, 80), 1),
            'disk': round(random.uniform(50, 70), 1),
            'processes': random.randint(80, 120),
            'timestamp': datetime.now().isoformat(),
            'psutil_available': False
        }
    
    def get_performance_data(self, timeframe: str = '1h') -> Dict[str, Any]:
        """Получение данных производительности за период (thread-safe)"""
        try:
            with self._lock:
                now = datetime.now()
                
                # Определяем временной интервал
                if timeframe == '1h':
                    start_time = now - timedelta(hours=1)
                elif timeframe == '6h':
                    start_time = now - timedelta(hours=6)
                elif timeframe == '24h':
                    start_time = now - timedelta(hours=24)
                elif timeframe == '7d':
                    start_time = now - timedelta(days=7)
                else:
                    start_time = now - timedelta(hours=1)
                
                # Фильтруем данные по времени
                filtered_data = {}
                for metric_type in ['cpu', 'memory', 'disk', 'network']:
                    filtered_data[metric_type] = [
                        point for point in self.metrics_history[metric_type] 
                        if point.timestamp >= start_time
                    ]
                
                # Если данных мало, генерируем тестовые
                if len(filtered_data['cpu']) < 10:
                    return self._generate_sample_performance_data(timeframe)
                
                # Группируем данные
                labels = []
                cpu_data = []
                memory_data = []
                disk_data = []
                network_data = []
                
                step = max(1, len(filtered_data['cpu']) // 50)  # Максимум 50 точек
                
                for i in range(0, len(filtered_data['cpu']), step):
                    if i < len(filtered_data['cpu']):
                        point = filtered_data['cpu'][i]
                        labels.append(point.timestamp.isoformat())
                        cpu_data.append(round(point.value, 1))
                        
                        # Добавляем данные других метрик
                        memory_data.append(
                            round(filtered_data['memory'][i].value, 1) 
                            if i < len(filtered_data['memory']) else 0
                        )
                        disk_data.append(
                            round(filtered_data['disk'][i].value, 1) 
                            if i < len(filtered_data['disk']) else 0
                        )
                        network_data.append(
                            round(filtered_data['network'][i].value, 2) 
                            if i < len(filtered_data['network']) else 0
                        )
                
                return {
                    'labels': labels,
                    'cpu_data': cpu_data,
                    'memory_data': memory_data,
                    'disk_data': disk_data,
                    'network_data': network_data,
                    'data_points': len(labels),
                    'timeframe': timeframe
                }
                
        except Exception as e:
            print(f"Ошибка получения данных производительности: {e}")
            return self._generate_sample_performance_data(timeframe)
    
    def _generate_sample_performance_data(self, timeframe: str) -> Dict[str, Any]:
        """Генерация тестовых данных производительности"""
        import random
        import math
        
        now = datetime.now()
        
        # Определяем количество точек и интервал
        timeframe_config = {
            '1h': (60, timedelta(minutes=1)),
            '6h': (36, timedelta(minutes=10)),
            '24h': (48, timedelta(minutes=30)),
            '7d': (84, timedelta(hours=2))
        }
        
        points, interval = timeframe_config.get(timeframe, (60, timedelta(minutes=1)))
        
        labels = []
        cpu_data = []
        memory_data = []
        disk_data = []
        network_data = []
        
        for i in range(points):
            timestamp = now - interval * (points - i)
            labels.append(timestamp.isoformat())
            
            # Генерируем реалистичные данные с циклическими паттернами
            base_time = i / points
            
            # CPU с некоторой периодичностью
            cpu_base = 20 + 30 * (0.5 + 0.3 * math.sin(base_time * 6))
            cpu_noise = random.uniform(-5, 5)
            cpu_value = max(5, min(95, cpu_base + cpu_noise))
            cpu_data.append(round(cpu_value, 1))
            
            # Память с ростом во времени
            memory_base = 45 + 15 * base_time + 10 * math.sin(base_time * 4)
            memory_noise = random.uniform(-3, 3)
            memory_value = max(30, min(90, memory_base + memory_noise))
            memory_data.append(round(memory_value, 1))
            
            # Диск относительно стабильный
            disk_base = 60 + 5 * math.sin(base_time * 2)
            disk_noise = random.uniform(-2, 2)
            disk_value = max(40, min(95, disk_base + disk_noise))
            disk_data.append(round(disk_value, 1))
            
            # Сеть с пиками активности
            network_base = 5 + 10 * math.sin(base_time * 8) ** 2
            network_noise = random.uniform(0, 3)
            network_value = max(0, network_base + network_noise)
            network_data.append(round(network_value, 2))
        
        return {
            'labels': labels,
            'cpu_data': cpu_data,
            'memory_data': memory_data,
            'disk_data': disk_data,
            'network_data': network_data,
            'data_points': len(labels),
            'timeframe': timeframe,
            'sample_data': True
        }
    
    def get_alerts(self, limit: Optional[int] = None, severity: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Получение списка алертов"""
        with self._lock:
            alerts = self.alerts.copy()
        
        # Фильтрация по серьезности
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
        
        # Сортировка по времени (новые первыми)
        alerts.sort(key=lambda x: x.timestamp, reverse=True)
        
        # Ограничение количества
        if limit:
            alerts = alerts[:limit]
        
        return [alert.to_dict() for alert in alerts]
    
    def acknowledge_alert(self, alert_id: int) -> bool:
        """Подтверждение алерта"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.acknowledged = True
                    return True
        return False
    
    def clear_alerts(self, severity: Optional[AlertSeverity] = None) -> int:
        """Очистка алертов"""
        with self._lock:
            if severity:
                initial_count = len(self.alerts)
                self.alerts = [alert for alert in self.alerts if alert.severity != severity]
                return initial_count - len(self.alerts)
            else:
                count = len(self.alerts)
                self.alerts.clear()
                return count
    
    def update_thresholds(self, thresholds: Dict[str, float]) -> bool:
        """Обновление пороговых значений"""
        try:
            self.thresholds.update_thresholds(thresholds)
            return True
        except Exception as e:
            print(f"Ошибка обновления порогов: {e}")
            return False
    
    def get_thresholds(self) -> Dict[str, float]:
        """Получение текущих пороговых значений"""
        return {
            'cpu_warning': self.thresholds.cpu_warning,
            'cpu_critical': self.thresholds.cpu_critical,
            'memory_warning': self.thresholds.memory_warning,
            'memory_critical': self.thresholds.memory_critical,
            'disk_warning': self.thresholds.disk_warning,
            'disk_critical': self.thresholds.disk_critical,
            'network_warning': self.thresholds.network_warning,
            'network_critical': self.thresholds.network_critical
        }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Получение информации о системе"""
        info = {
            'platform': platform.system(),
            'platform_release': platform.release(),
            'platform_version': platform.version(),
            'architecture': platform.machine(),
            'hostname': socket.gethostname(),
            'python_version': platform.python_version(),
            'psutil_available': self._psutil_available
        }
        
        if self._psutil_available:
            try:
                info.update({
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat()
                })
            except:
                pass
        
        return info


# Создаем глобальный экземпляр сервиса
monitoring_service = MonitoringService()
