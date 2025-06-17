# web/services/correspondences_service.py
"""
Сервис для работы с соответствиями заголовков файлов
"""

import json
import os
from typing import Dict, List, Optional
from difflib import SequenceMatcher

from web.utils.logging_helper import log_error


class CorrespondencesService:
    """Сервис для работы с соответствиями заголовков"""
    
    def __init__(self):
        self.correspondences_dir = "correspondences"
        self._ensure_correspondences_dir()
    
    def _ensure_correspondences_dir(self):
        """Создает директорию для соответствий если её нет"""
        if not os.path.exists(self.correspondences_dir):
            os.makedirs(self.correspondences_dir)
    
    def auto_map_headers(
        self, 
        register_type: str, 
        template_headers: List[str], 
        file_headers: List[str]
    ) -> Dict[str, str]:
        """
        Автоматически сопоставляет заголовки файла с шаблонными заголовками
        
        Args:
            register_type: Тип регистра
            template_headers: Заголовки шаблона
            file_headers: Заголовки из файла
            
        Returns:
            dict: Словарь соответствий {template_header: file_header}
        """
        mappings = {}
        
        # Загружаем существующие соответствия
        existing_correspondences = self.load_correspondences(register_type)
        
        for template_header in template_headers:
            best_match = None
            best_score = 0.0
            
            # Сначала проверяем существующие соответствия
            if template_header in existing_correspondences:
                reverse_mapping = {v: k for k, v in existing_correspondences.items()}
                if existing_correspondences[template_header] in file_headers:
                    mappings[template_header] = existing_correspondences[template_header]
                    continue
            
            # Ищем лучшее совпадение среди заголовков файла
            for file_header in file_headers:
                score = self._calculate_similarity(template_header, file_header)
                if score > best_score and score > 0.6:  # Минимальный порог схожести
                    best_score = score
                    best_match = file_header
            
            if best_match:
                mappings[template_header] = best_match
        
        return mappings
    
    def save_correspondences(self, register_type: str, mappings: Dict[str, str]) -> bool:
        """
        Сохраняет соответствия заголовков
        
        Args:
            register_type: Тип регистра
            mappings: Словарь соответствий
            
        Returns:
            bool: True если сохранение успешно
        """
        try:
            filename = os.path.join(self.correspondences_dir, f"{register_type}.json")
            
            # Загружаем существующие соответствия
            existing_mappings = self.load_correspondences(register_type)
            
            # Обновляем существующие соответствия
            existing_mappings.update(mappings)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(existing_mappings, f, ensure_ascii=False, indent=2)
            
            return True
            
        except Exception as e:
            log_error(f"Ошибка сохранения соответствий для {register_type}: {str(e)}")
            return False
    
    def load_correspondences(self, register_type: str) -> Dict[str, str]:
        """
        Загружает соответствия для типа регистра
        
        Args:
            register_type: Тип регистра
            
        Returns:
            dict: Словарь соответствий
        """
        try:
            filename = os.path.join(self.correspondences_dir, f"{register_type}.json")
            
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                return {}
                
        except Exception as e:
            log_error(f"Ошибка загрузки соответствий для {register_type}: {str(e)}")
            return {}
    
    def get_all_correspondences(self) -> Dict[str, Dict[str, str]]:
        """
        Получает все соответствия для всех типов регистров
        
        Returns:
            dict: Словарь всех соответствий
        """
        result = {}
        
        try:
            if not os.path.exists(self.correspondences_dir):
                return result
            
            for filename in os.listdir(self.correspondences_dir):
                if filename.endswith('.json'):
                    register_type = filename[:-5]  # убираем .json
                    result[register_type] = self.load_correspondences(register_type)
            
            return result
            
        except Exception as e:
            log_error(f"Ошибка получения всех соответствий: {str(e)}")
            return {}
    
    def delete_correspondences(self, register_type: str) -> bool:
        """
        Удаляет соответствия для типа регистра
        
        Args:
            register_type: Тип регистра
            
        Returns:
            bool: True если удаление успешно
        """
        try:
            filename = os.path.join(self.correspondences_dir, f"{register_type}.json")
            
            if os.path.exists(filename):
                os.remove(filename)
                return True
            else:
                return False
                
        except Exception as e:
            log_error(f"Ошибка удаления соответствий для {register_type}: {str(e)}")
            return False
    
    def update_correspondence(self, register_type: str, template_header: str, file_header: str) -> bool:
        """
        Обновляет отдельное соответствие
        
        Args:
            register_type: Тип регистра
            template_header: Заголовок шаблона
            file_header: Заголовок файла
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            mappings = self.load_correspondences(register_type)
            mappings[template_header] = file_header
            return self.save_correspondences(register_type, mappings)
            
        except Exception as e:
            log_error(f"Ошибка обновления соответствия: {str(e)}")
            return False
    
    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """
        Вычисляет схожесть между двумя строками
        
        Args:
            str1: Первая строка
            str2: Вторая строка
            
        Returns:
            float: Коэффициент схожести от 0 до 1
        """
        # Приводим к нижнему регистру и удаляем лишние пробелы
        str1_clean = str1.lower().strip()
        str2_clean = str2.lower().strip()
        
        # Базовая схожесть через SequenceMatcher
        base_similarity = SequenceMatcher(None, str1_clean, str2_clean).ratio()
        
        # Дополнительные проверки для повышения точности
        bonus = 0.0
        
        # Бонус за точное совпадение слов
        words1 = set(str1_clean.split())
        words2 = set(str2_clean.split())
        if words1 & words2:  # если есть общие слова
            bonus += 0.2
        
        # Бонус за совпадение ключевых слов
        key_words = ['номер', 'договор', 'фио', 'фамилия', 'имя', 'отчество', 
                    'телефон', 'адрес', 'дата', 'сумма', 'процент', 'тип']
        
        for key_word in key_words:
            if key_word in str1_clean and key_word in str2_clean:
                bonus += 0.1
                break
        
        return min(base_similarity + bonus, 1.0)
    
    def get_template_headers(self, register_type: str) -> List[str]:
        """
        Получает шаблонные заголовки для типа регистра
        
        Args:
            register_type: Тип регистра
            
        Returns:
            list: Список шаблонных заголовков
        """
        # Здесь можно определить шаблонные заголовки для разных типов регистров
        templates = {
            'ипотека': [
                'Номер договора', 'ФИО', 'Фамилия', 'Имя', 'Отчество',
                'Дата рождения', 'Телефон', 'Email', 'Адрес регистрации',
                'Сумма кредита', 'Процентная ставка', 'Срок кредита'
            ],
            'каско': [
                'Номер полиса', 'ФИО страхователя', 'Марка автомобиля',
                'Модель автомобиля', 'VIN номер', 'Государственный номер',
                'Год выпуска', 'Страховая сумма', 'Дата начала страхования',
                'Дата окончания страхования'
            ],
            'осаго': [
                'Номер полиса', 'ФИО собственника', 'Марка ТС', 'Модель ТС',
                'VIN номер', 'Регистрационный знак', 'Год выпуска',
                'Мощность двигателя', 'Дата начала страхования'
            ]
        }
        
        return templates.get(register_type.lower(), [])


# Глобальный экземпляр сервиса
correspondences_service = CorrespondencesService()
