# web/utils/nexus_utils.py
"""
Утилиты для работы с Nexus.
Дополнительные функции для расширения функциональности интерфейса.
"""

from typing import Dict, List, Any, Optional
from web.utils.nexus_config import (
    PAGE_CONFIGS, 
    BUTTON_CONFIGS, 
    AUTOREG_CONFIGS, 
    AUTODAILYES_CONFIGS,
    nexus_config_manager
)


class NexusPageBuilder:
    """Класс для динамического создания страниц Nexus"""
    
    @staticmethod
    def create_custom_page(
        title: str, 
        subtitle: str, 
        buttons: List[Dict[str, Any]], 
        show_steps: bool = False, 
        current_step: int = 1, 
        random_slogan: bool = False
    ) -> Dict[str, Any]:
        """
        Создание кастомной страницы
        
        Args:
            title: Заголовок страницы
            subtitle: Подзаголовок страницы
            buttons: Список кнопок
            show_steps: Показывать ли индикатор шагов
            current_step: Текущий шаг
            random_slogan: Показывать ли случайный слоган
            
        Returns:
            Dict: Конфигурация страницы
        """
        return {
            'title': title,
            'subtitle': subtitle,
            'config': {
                'randomSlogan': random_slogan,
                'showSteps': show_steps,
                'currentStep': current_step,
                'buttons': buttons
            }
        }
    
    @staticmethod
    def add_back_button(
        buttons: List[Dict[str, Any]], 
        back_url: str, 
        back_message: str = "Назад"
    ) -> List[Dict[str, Any]]:
        """
        Добавление кнопки "Назад" к списку кнопок
        
        Args:
            buttons: Существующий список кнопок
            back_url: URL для возврата
            back_message: Текст кнопки возврата
            
        Returns:
            List: Обновленный список кнопок
        """
        back_button = {
            'icon': 'fas fa-arrow-left',
            'text': back_message,
            'url': back_url,
            'message': f'Возврат к {back_message.lower()}'
        }
        return buttons + [back_button]
    
    @staticmethod
    def create_button(
        icon: str, 
        text: str, 
        url: Optional[str] = None, 
        message: Optional[str] = None, 
        disabled: bool = False, 
        badge: Optional[str] = None, 
        disabled_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создание отдельной кнопки
        
        Args:
            icon: CSS класс иконки
            text: Текст кнопки
            url: URL для перехода
            message: Сообщение при наведении
            disabled: Флаг отключенной кнопки
            badge: Значок на кнопке
            disabled_message: Сообщение для отключенной кнопки
            
        Returns:
            Dict: Конфигурация кнопки
        """
        button = {
            'icon': icon,
            'text': text
        }
        
        if disabled:
            button['disabled'] = True
            button['disabledMessage'] = disabled_message or f'{text} в разработке'
            if badge:
                button['badge'] = badge
        else:
            button['url'] = url
            button['message'] = message or f'Переход к модулю "{text}"'
        
        return button
    
    @staticmethod
    def create_processing_buttons(
        process_url: str,
        status_url: str,
        cancel_url: str,
        download_url: str,
        back_url: str
    ) -> List[Dict[str, Any]]:
        """
        Создание стандартного набора кнопок для страниц обработки
        
        Args:
            process_url: URL для запуска обработки
            status_url: URL для получения статуса
            cancel_url: URL для отмены обработки
            download_url: URL для скачивания результата
            back_url: URL для возврата назад
            
        Returns:
            List: Набор кнопок для обработки
        """
        return [
            {
                'icon': 'fas fa-play',
                'text': 'Запустить обработку',
                'url': process_url,
                'message': 'Начать обработку файлов'
            },
            {
                'icon': 'fas fa-download',
                'text': 'Скачать результат',
                'url': download_url,
                'message': 'Скачать обработанный файл'
            },
            {
                'icon': 'fas fa-times',
                'text': 'Отменить',
                'url': cancel_url,
                'message': 'Отменить текущую обработку'
            },
            {
                'icon': 'fas fa-arrow-left',
                'text': 'Назад',
                'url': back_url,
                'message': 'Вернуться назад'
            }
        ]


class NexusConfigHelper:
    """Вспомогательные функции для работы с конфигурациями"""
    
    @staticmethod
    def get_page_config(page_key: str) -> Dict[str, Any]:
        """
        Получение конфигурации страницы по ключу
        
        Args:
            page_key: Ключ страницы
            
        Returns:
            Dict: Конфигурация страницы
        """
        return nexus_config_manager.get_page_config(page_key) or PAGE_CONFIGS['main']
    
    @staticmethod
    def get_autodailyes_config(autodailyes_key: str) -> Dict[str, Any]:
        """
        Получение конфигурации автоежедневки по ключу
        
        Args:
            autodailyes_key: Ключ автоежедневки
            
        Returns:
            Dict: Конфигурация автоежедневки
        """
        return nexus_config_manager.get_autodailyes_config(autodailyes_key) or AUTODAILYES_CONFIGS['autodeals']
    
    @staticmethod
    def get_autoreg_config(autoreg_key: str) -> Dict[str, Any]:
        """
        Получение конфигурации автореестра по ключу
        
        Args:
            autoreg_key: Ключ автореестра
            
        Returns:
            Dict: Конфигурация автореестра
        """
        return nexus_config_manager.get_autoreg_config(autoreg_key) or AUTOREG_CONFIGS['ipoteka']
    
    @staticmethod
    def get_buttons_config(config_key: str) -> List[Dict[str, Any]]:
        """
        Получение конфигурации кнопок по ключу
        
        Args:
            config_key: Ключ конфигурации кнопок
            
        Returns:
            List: Список конфигураций кнопок
        """
        return nexus_config_manager.get_button_config(config_key) or []
    
    @staticmethod
    def extend_page_config(page_key: str, **kwargs) -> Dict[str, Any]:
        """
        Расширение существующей конфигурации страницы
        
        Args:
            page_key: Ключ страницы
            **kwargs: Дополнительные параметры для изменения
            
        Returns:
            Dict: Расширенная конфигурация
        """
        config = NexusConfigHelper.get_page_config(page_key).copy()
        
        for key, value in kwargs.items():
            if key in config:
                config[key] = value
            elif 'config' in config and key in config['config']:
                config['config'][key] = value
        
        return config
    
    @staticmethod
    def validate_module_access(module_type: str, register_type: str = None) -> bool:
        """
        Проверка доступности модуля
        
        Args:
            module_type: Тип модуля (autoreg, autodailyes)
            register_type: Тип реестра (для автореестров)
            
        Returns:
            bool: Доступен ли модуль
        """
        if module_type == 'autoreg' and register_type:
            return nexus_config_manager.validate_register_type(register_type)
        elif module_type == 'autodailyes' and register_type:
            return nexus_config_manager.validate_autodailyes_type(register_type)
        
        return True
    
    @staticmethod
    def get_module_endpoint_mapping(module_type: str) -> Dict[str, str]:
        """
        Получение маппинга эндпоинтов для модуля
        
        Args:
            module_type: Тип модуля
            
        Returns:
            Dict: Маппинг эндпоинтов
        """
        endpoint_mappings = {
            'autojarvis': {
                'process': '/jarvis/process',
                'status': '/jarvis/status',
                'download': '/jarvis/download',
                'cancel': '/jarvis/cancel'
            },
            'autoolds': {
                'process': '/lost_contracts/process',
                'status': '/lost_contracts/status',
                'download': '/lost_contracts/download',
                'cancel': '/lost_contracts/cancel'
            },
            'autodeals': {
                'process': '/registry/process',
                'status': '/registry/status',
                'download': '/registry/download',
                'cancel': '/registry/cancel'
            },
            'autoverint': {
                'process': '/processing/process',
                'status': '/processing/status',
                'download': '/processing/download',
                'cancel': '/processing/cancel'
            },
            'autochekcompany': {
                'process': '/campaigns/process',
                'status': '/campaigns/status',
                'download': '/campaigns/download',
                'cancel': '/campaigns/cancel'
            }
        }
        
        return endpoint_mappings.get(module_type, {})


# Предустановленные конфигурации для часто используемых типов страниц
PRESET_CONFIGS: Dict[str, Dict[str, Any]] = {
    'processing_page': {
        'showSteps': True,
        'currentStep': 2,
        'randomSlogan': False
    },
    
    'mapping_page': {
        'showSteps': True,
        'currentStep': 3,
        'randomSlogan': False
    },
    
    'result_page': {
        'showSteps': True,
        'currentStep': 4,
        'randomSlogan': False
    },
    
    'upload_page': {
        'showSteps': True,
        'currentStep': 1,
        'randomSlogan': False
    },
    
    'main_menu': {
        'showSteps': False,
        'currentStep': 1,
        'randomSlogan': True
    }
}


class NexusRouteHelper:
    """Вспомогательные функции для работы с маршрутами Nexus"""
    
    @staticmethod
    def build_breadcrumb(current_page: str, parent_pages: List[str] = None) -> List[Dict[str, str]]:
        """
        Построение навигационной цепочки (breadcrumb)
        
        Args:
            current_page: Текущая страница
            parent_pages: Список родительских страниц
            
        Returns:
            List: Навигационная цепочка
        """
        breadcrumb = [{'name': 'Nexus', 'url': '/nexus'}]
        
        if parent_pages:
            for page in parent_pages:
                config = NexusConfigHelper.get_page_config(page)
                breadcrumb.append({
                    'name': config.get('title', page.title()),
                    'url': f'/nexus/{page}'
                })
        
        # Текущая страница без ссылки
        current_config = NexusConfigHelper.get_page_config(current_page)
        breadcrumb.append({
            'name': current_config.get('title', current_page.title()),
            'url': None  # Текущая страница
        })
        
        return breadcrumb
    
    @staticmethod
    def get_step_info(current_step: int, total_steps: int = 4) -> Dict[str, Any]:
        """
        Получение информации о текущем шаге процесса
        
        Args:
            current_step: Текущий шаг
            total_steps: Общее количество шагов
            
        Returns:
            Dict: Информация о шаге
        """
        step_names = {
            1: 'Выбор файлов',
            2: 'Сопоставление',
            3: 'Обработка',
            4: 'Результат'
        }
        
        return {
            'current': current_step,
            'total': total_steps,
            'name': step_names.get(current_step, f'Шаг {current_step}'),
            'percentage': (current_step / total_steps) * 100
        }


# Создаем глобальные экземпляры для удобства использования
page_builder = NexusPageBuilder()
config_helper = NexusConfigHelper()
route_helper = NexusRouteHelper()

# Функции для обратной совместимости
get_page_config = config_helper.get_page_config
get_autodailyes_config = config_helper.get_autodailyes_config
get_autoreg_config = config_helper.get_autoreg_config
get_buttons_config = config_helper.get_buttons_config
extend_page_config = config_helper.extend_page_config
