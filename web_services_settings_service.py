# web/services/settings_service.py
"""
Сервис для работы с настройками системы
"""

import configparser
from typing import Dict, Any, Optional

from web.utils.logging_helper import log_error


class SettingsService:
    """Сервис для работы с настройками"""
    
    def __init__(self):
        self.settings_file = 'settings_nexus.ini'
    
    def get_settings(self, section_name: str) -> Dict[str, str]:
        """
        Получает настройки для указанной секции
        
        Args:
            section_name: Название секции настроек
            
        Returns:
            dict: Словарь с настройками
        """
        config = configparser.ConfigParser()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except FileNotFoundError:
            log_error(f"Файл настроек {self.settings_file} не найден")
            return {}
        except Exception as e:
            log_error(f"Ошибка чтения файла настроек: {str(e)}")
            return {}

        if section_name in config:
            return dict(config[section_name])
        else:
            return {}
    
    def save_settings(self, section_name: str, settings: Dict[str, str]) -> bool:
        """
        Сохраняет настройки для указанной секции
        
        Args:
            section_name: Название секции
            settings: Словарь с настройками
            
        Returns:
            bool: True если сохранение успешно
        """
        config = configparser.ConfigParser()
        
        try:
            # Читаем существующий файл
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    config.read_file(f)
            except FileNotFoundError:
                log_error(f"Файл настроек {self.settings_file} не найден")
                return False
            
            # Создаем секцию если её нет
            if not config.has_section(section_name):
                config.add_section(section_name)
                
            # Записываем настройки
            for key, value in settings.items():
                config[section_name][key] = str(value)
                
            # Сохраняем файл
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                config.write(f)
                
            return True
            
        except Exception as e:
            log_error(f"Ошибка сохранения настроек: {str(e)}")
            return False
    
    def get_all_sections(self) -> Dict[str, Dict[str, str]]:
        """
        Получает все секции настроек
        
        Returns:
            dict: Словарь всех секций и их настроек
        """
        config = configparser.ConfigParser()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                config.read_file(f)
        except FileNotFoundError:
            return {}
        except Exception as e:
            log_error(f"Ошибка чтения файла настроек: {str(e)}")
            return {}
        
        result = {}
        for section_name in config.sections():
            result[section_name] = dict(config[section_name])
        
        return result
    
    def delete_section(self, section_name: str) -> bool:
        """
        Удаляет секцию настроек
        
        Args:
            section_name: Название секции для удаления
            
        Returns:
            bool: True если удаление успешно
        """
        config = configparser.ConfigParser()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                config.read_file(f)
                
            if config.has_section(section_name):
                config.remove_section(section_name)
                
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    config.write(f)
                    
                return True
            else:
                return False
                
        except Exception as e:
            log_error(f"Ошибка удаления секции настроек: {str(e)}")
            return False
    
    def update_setting(self, section_name: str, key: str, value: str) -> bool:
        """
        Обновляет отдельную настройку
        
        Args:
            section_name: Название секции
            key: Ключ настройки
            value: Значение настройки
            
        Returns:
            bool: True если обновление успешно
        """
        config = configparser.ConfigParser()
        
        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                config.read_file(f)
                
            if not config.has_section(section_name):
                config.add_section(section_name)
                
            config[section_name][key] = str(value)
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                config.write(f)
                
            return True
            
        except Exception as e:
            log_error(f"Ошибка обновления настройки: {str(e)}")
            return False
    
    def get_setting(self, section_name: str, key: str, default_value: str = "") -> str:
        """
        Получает значение отдельной настройки
        
        Args:
            section_name: Название секции
            key: Ключ настройки
            default_value: Значение по умолчанию
            
        Returns:
            str: Значение настройки или значение по умолчанию
        """
        settings = self.get_settings(section_name)
        return settings.get(key, default_value)


# Глобальный экземпляр сервиса
settings_service = SettingsService()
