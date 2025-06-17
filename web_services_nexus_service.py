# web/services/nexus_service.py
"""
Сервис для работы с системой Nexus
"""

from typing import Dict, List, Any, Optional
from datetime import datetime

from web.utils.logging_helper import logging_helper


class NexusService:
    """Сервис для работы с системой автоматизации Nexus"""
    
    def __init__(self):
        self.page_configs = self._init_page_configs()
        self.autoreg_configs = self._init_autoreg_configs()
        self.autodailyes_configs = self._init_autodailyes_configs()
    
    def _init_page_configs(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация конфигураций страниц"""
        return {
            'main': {
                'title': 'Nexus - Главная',
                'description': 'Система автоматизации процессов',
                'sections': ['autoreg', 'autodailyes', 'monitoring']
            },
            'autoreg': {
                'title': 'Автореестры',
                'description': 'Автоматическая обработка реестров',
                'sections': ['prolong', 'olds', 'pilots']
            },
            'prolong': {
                'title': 'Пролонгация',
                'description': 'Обработка реестров пролонгации',
                'types': ['ipoteka', 'kasko', 'osago', 'mbg']
            },
            'olds': {
                'title': 'Потеряшки',
                'description': 'Обработка потерянных клиентов',
                'types': ['ipoteka_wa', 'osago_wa', 'osago_4_1']
            },
            'pilots': {
                'title': 'Пилотные проекты',
                'description': 'Экспериментальные автореестры',
                'types': ['ipoteka_kom_bank', 'ipoteka_sos', 'f1', 'osago_kz', 'dvr']
            },
            'autodailyes': {
                'title': 'Автоежедневки',
                'description': 'Автоматизация ежедневных задач',
                'periods': ['dailyes', 'weeks']
            },
            'dailyes': {
                'title': 'Ежедневные задачи',
                'description': 'Задачи, выполняемые каждый день',
                'tasks': ['autoverint', 'autoolds', 'autojarvis', 'autodeals']
            },
            'weeks': {
                'title': 'Еженедельные задачи',
                'description': 'Задачи, выполняемые еженедельно',
                'tasks': ['autochekcompany']
            }
        }
    
    def _init_autoreg_configs(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация конфигураций автореестров"""
        return {
            'ipoteka': {
                'title': 'Ипотека',
                'description': 'Обработка ипотечных реестров пролонгации',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                    "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                    "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент",
                    "Номер агентского договора", "Дата окончания страхования", "Прошлый период Страховая премия",
                    "Прошлый период Страховая сумма", "Канал", "ID_внешней системы", "Кампания",
                    "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "Приоритет",
                    "Филиал ВСК", "Регион", "Объект страхования",
                    "Плановая дата звонка CTI", "Вид полиса", "Скидка по спецпредложению",
                    "Скидка к ПК", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации"
                ],
                'register_type': 'Ипотека',
                'category': 'prolong'
            },
            'ipoteka_msk': {
                'title': 'Ипотека Москва',
                'description': 'Обработка московских ипотечных реестров (Профит)',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                    "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                    "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент",
                    "Номер агентского договора", "Дата окончания страхования", "Прошлый период Страховая премия",
                    "Прошлый период Страховая сумма", "Канал", "ID_внешней системы", "Кампания",
                    "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "Приоритет",
                    "Филиал ВСК", "Регион", "Объект страхования",
                    "Плановая дата звонка CTI", "Вид полиса", "Скидка по спецпредложению",
                    "Скидка к ПК", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации"
                ],
                'register_type': 'Ипотека_мск',
                'category': 'prolong'
            },
            'kasko': {
                'title': 'КАСКО',
                'description': 'Обработка реестров пролонгации КАСКО',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон",
                    "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования", "Марка", "Модель", "Год выпуска",
                    "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал",
                    "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент", "Дилер", "Логин дилера", "Точка продаж", "Категория партнера", 
                    "Номер агентского договора", "Вид полиса", "ID_внешней системы", "Кампания", "Плановая дата звонка CTI", "Приоритет", "Вид страхования", 
                    "Группа продукта", "Продукт", "Тип лида", "Передан в АКЦ", "Парный договор", "Вероятность, шт.", "Вероятность, руб."
                ],
                'register_type': 'КАСКО',
                'category': 'prolong'
            },
            'kasko_iz_osago': {
                'title': 'КАСКО из ОСАГО',
                'description': 'Обработка реестров КАСКО по ОСАГО',
                'template_headers': [
                    "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                    "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                    "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                    "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
                ],
                'register_type': 'КАСКО_ИЗ_ОСАГО_4_1',
                'category': 'prolong'
            },
            'osago': {
                'title': 'ОСАГО',
                'description': 'Обработка реестров пролонгации ОСАГО',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения",
                    "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования",
                    "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект", "Дата окончания страхования",
                    "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
                    "Промокод", "Канал", "ID_внешней системы", "Тип лида", "Продукт", "Группа продукта", "Вид страхования",
                    "Приоритет", "Плановая дата звонка CTI", "Номер проекта", "Программа страхования"
                ],
                'register_type': 'ОСАГО',
                'category': 'prolong'
            },
            'mbg': {
                'title': 'МБГ',
                'description': 'Обработка реестров МБГ (Малый бизнес и граждане)',
                'template_headers': [
                    "ID_внешней системы", "Приоритет", "Тип лида", "Кампания", "id физ лица", 
                    "ФИО", "Фамилия", "Имя", "Отчество", "Регион", "Филиал ВСК", "Дата рождения", 
                    "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Вид страхования", "Группа продукта", 
                    "Продукт", "№ Договора К Пролонгации", "Дата окончания страхования", "Прошлый период Страховая премия", 
                    "Прошлый период Страховая сумма", "Канал", "Объект страхования"
                ],
                'register_type': 'МБГ',
                'category': 'prolong'
            },
            'ipoteka_wa': {
                'title': 'Ипотека WA',
                'description': 'Ипотечные потеряшки через WhatsApp',
                'template_headers': [
                    "ID_внешней системы", "Примечания", "Дополнительные сведения", "Кампания", "Тип лида", "Группа продукта",
                    "Продукт", "Вид страхования", "Ответственное подразделение", "Ответственный отдел", "Приоритет", "id физ лица",
                    "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail",
                    "Регион", "Филиал ВСК", "Другой полис", "Кредитный договор Дата", "Банк", "Объект страхования", "Дата окончания страхования",
                    "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Канал", "Тип базы"
                ],
                'register_type': 'Ипотека_WA',
                'category': 'olds'
            },
            'osago_wa': {
                'title': 'ОСАГО WA',
                'description': 'ОСАГО потеряшки через WhatsApp',
                'template_headers': [
                    "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                    "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                    "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                    "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
                ],
                'register_type': 'ОСАГО_WA',
                'category': 'olds'
            },
            'osago_4_1_up': {
                'title': 'ОСАГО 4.1',
                'description': 'ОСАГО потеряшки версии 4.1',
                'template_headers': [
                    "id физлицо", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Филиал ВСК", 
                    "Регион", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Объект страхования", "Марка", "Модель", 
                    "Год выпуска", "VIN", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                    "Новый период страховая премия", "Канал", "Ссылка на проект", "Дополнительные сведения"
                ],
                'register_type': 'ОСАГО_4_1',
                'category': 'olds'
            },
            'ipoteka_kom_bank': {
                'title': 'Ипотека Ком.Банки',
                'description': 'Ипотека коммерческих банков',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество",
                    "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Банк",
                    "Ответственный за лид id", "Ответственный сотрудник ЦО Филиала", "Ответственный сотрудник Агент",
                    "Номер агентского договора", "Дата окончания страхования", "Прошлый период Страховая премия",
                    "Прошлый период Страховая сумма", "Канал", "ID_внешней системы", "Кампания",
                    "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "Приоритет",
                    "Филиал ВСК", "Регион", "Объект страхования",
                    "Плановая дата звонка CTI", "Вид полиса", "Скидка по спецпредложению",
                    "Скидка к ПК", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации"
                ],
                'register_type': 'Ипотека_ком_банки',
                'category': 'pilots'
            },
            'ipoteka_sos': {
                'title': 'Ипотека SOS',
                'description': 'Ипотека в рамках проекта SOS',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ID_внешней системы", "Статус рассылки 3", "Кампания", "Тип лида", "Продукт", "Группа продукта", 
                    "Вид страхования", "Приоритет", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
                    "Филиал ВСК", "Регион", "Банк", "Плановая дата звонка CTI", "Дата окончания страхования", "Прошлый период Страховая премия", "Прошлый период Страховая сумма", 
                    "Канал", "Вид полиса", "Шт., вероятность пролонгации", "Руб., вероятность пролонгации", "Дополнительные сведения", "Ссылка на проект в CTI"
                ],
                'register_type': 'Ипотека_SOS',
                'category': 'pilots'
            },
            'f1': {
                'title': 'OneFactor',
                'description': 'Обработка реестров OneFactor',
                'template_headers': [
                    "id физ лица", "Тип лида", "Продукт", "Группа продукта", "Вид страхования", "ФИО", "Фамилия", 
                    "Имя", "Отчество", "Дата рождения", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", 
                    "Филиал ВСК", "Регион", "Другой полис", "Дополнительные сведения", "Тип базы"
                ],
                'register_type': 'f1',
                'category': 'pilots'
            },
            'osago_kz': {
                'title': 'ОСАГО КЗ',
                'description': 'ОСАГО в рамках проекта КЗ',
                'template_headers': [
                    "id физ лица", "№ Договора К Пролонгации", "ФИО", "Фамилия", "Имя", "Отчество", "Дата рождения",
                    "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail", "Филиал ВСК", "Регион", "Объект страхования",
                    "Марка", "Модель", "Год выпуска", "VIN", "Ссылка на проект", "Дата окончания страхования",
                    "Прошлый период Страховая премия", "Прошлый период Страховая сумма", "Новый период Страховая премия",
                    "Промокод", "Канал", "ID_внешней системы", "Тип лида", "Продукт", "Группа продукта", "Вид страхования",
                    "Приоритет", "Плановая дата звонка CTI", "Номер проекта", "Программа страхования"
                ],
                'register_type': 'ОСАГО_КЗ',
                'category': 'pilots'
            },
            'dvr': {
                'title': 'ДВР',
                'description': 'Обработка реестров проекта ДВР',
                'template_headers': [
                    "Примечания", "Продукт", "Филиал ВСК", "ФИО", "Фамилия", "Имя", "Отчество", "Основной телефон", "Телефон 2", "Телефон 3", "Основной e-mail",
                    "Другой полис", "Дата начала страхования/дата заключения", "Кредитный договор Дата", 
                    "Прошлый период Страховая сумма", "Марка", "Модель", "Год выпуска", "СтраховаяСумма", "Риск", "ТипСобытия", "Стадия"
                ],
                'register_type': 'ДВР',
                'category': 'pilots'
            }
        }
    
    def _init_autodailyes_configs(self) -> Dict[str, Dict[str, Any]]:
        """Инициализация конфигураций автоежедневок"""
        return {
            'autoverint': {
                'title': 'Автоматизация Verint',
                'description': 'Автоматическая обработка файлов Verint',
                'period': 'daily',
                'schedule': '08:00',
                'enabled': True
            },
            'autoolds': {
                'title': 'Автоматизация потеряшек',
                'description': 'Автоматическая обработка старых записей',
                'period': 'daily',
                'schedule': '09:00',
                'enabled': True
            },
            'autojarvis': {
                'title': 'Автоматизация Jarvis',
                'description': 'Автоматическая обработка задач Jarvis',
                'period': 'daily',
                'schedule': '10:00',
                'enabled': True
            },
            'autodeals': {
                'title': 'Автоматизация сделок',
                'description': 'Автоматическая обработка сделок',
                'period': 'daily',
                'schedule': '11:00',
                'enabled': True
            },
            'autochekcompany': {
                'title': 'Автопроверка компаний',
                'description': 'Автоматическая проверка компаний',
                'period': 'weekly',
                'schedule': 'monday 08:00',
                'enabled': True
            }
        }
    
    def get_page_config(self, page_key: str) -> Dict[str, Any]:
        """Получение конфигурации страницы"""
        return self.page_configs.get(page_key, self.page_configs['main'])
    
    def get_autoreg_config(self, autoreg_key: str) -> Dict[str, Any]:
        """Получение конфигурации автореестра"""
        config = self.autoreg_configs.get(autoreg_key, {})
        if config:
            config['timestamp'] = datetime.now().isoformat()
        return config
    
    def get_autodailyes_config(self, autodailyes_key: str) -> Dict[str, Any]:
        """Получение конфигурации автоежедневки"""
        config = self.autodailyes_configs.get(autodailyes_key, {})
        if config:
            config['timestamp'] = datetime.now().isoformat()
        return config
    
    def get_available_register_types(self) -> List[str]:
        """Получение списка доступных типов реестров"""
        return list(self.autoreg_configs.keys())
    
    def get_prolong_types(self) -> List[Dict[str, Any]]:
        """Получение типов пролонгации"""
        return [
            config for config in self.autoreg_configs.values()
            if config.get('category') == 'prolong'
        ]
    
    def get_olds_types(self) -> List[Dict[str, Any]]:
        """Получение типов потеряшек"""
        return [
            config for config in self.autoreg_configs.values()
            if config.get('category') == 'olds'
        ]
    
    def get_pilot_types(self) -> List[Dict[str, Any]]:
        """Получение типов пилотных проектов"""
        return [
            config for config in self.autoreg_configs.values()
            if config.get('category') == 'pilots'
        ]
    
    def get_autodailyes_periods(self) -> List[str]:
        """Получение периодов автоежедневок"""
        return ['dailyes', 'weeks']
    
    def get_daily_tasks(self) -> List[Dict[str, Any]]:
        """Получение ежедневных задач"""
        return [
            config for config in self.autodailyes_configs.values()
            if config.get('period') == 'daily'
        ]
    
    def get_weekly_tasks(self) -> List[Dict[str, Any]]:
        """Получение еженедельных задач"""
        return [
            config for config in self.autodailyes_configs.values()
            if config.get('period') == 'weekly'
        ]
    
    def get_main_page_stats(self) -> Dict[str, Any]:
        """Получение статистики для главной страницы"""
        total_autoreg = len(self.autoreg_configs)
        total_autodailyes = len(self.autodailyes_configs)
        
        enabled_autodailyes = len([
            config for config in self.autodailyes_configs.values()
            if config.get('enabled', False)
        ])
        
        return {
            'total_autoreg_types': total_autoreg,
            'total_autodailyes': total_autodailyes,
            'enabled_autodailyes': enabled_autodailyes,
            'categories': {
                'prolong': len(self.get_prolong_types()),
                'olds': len(self.get_olds_types()),
                'pilots': len(self.get_pilot_types())
            },
            'periods': {
                'daily': len(self.get_daily_tasks()),
                'weekly': len(self.get_weekly_tasks())
            },
            'last_update': datetime.now().isoformat()
        }
    
    def get_detailed_stats(self) -> Dict[str, Any]:
        """Получение детальной статистики"""
        try:
            stats = self.get_main_page_stats()
            
            # Добавляем дополнительную статистику
            stats.update({
                'autoreg_by_category': {
                    'prolong': [config['title'] for config in self.get_prolong_types()],
                    'olds': [config['title'] for config in self.get_olds_types()],
                    'pilots': [config['title'] for config in self.get_pilot_types()]
                },
                'autodailyes_by_period': {
                    'daily': [config['title'] for config in self.get_daily_tasks()],
                    'weekly': [config['title'] for config in self.get_weekly_tasks()]
                },
                'system_info': {
                    'version': '2.0.0',
                    'modules': ['autoreg', 'autodailyes'],
                    'active_since': datetime.now().replace(hour=0, minute=0, second=0).isoformat()
                }
            })
            
            return stats
            
        except Exception as e:
            logging_helper.log_error(f"Ошибка получения детальной статистики Nexus: {str(e)}")
            return {'error': 'Ошибка получения статистики'}
    
    def get_page_configs(self) -> Dict[str, Dict[str, Any]]:
        """Получение всех конфигураций страниц"""
        return self.page_configs
    
    def get_autoreg_configs(self) -> Dict[str, Dict[str, Any]]:
        """Получение всех конфигураций автореестров"""
        return self.autoreg_configs
    
    def get_autodailyes_configs(self) -> Dict[str, Dict[str, Any]]:
        """Получение всех конфигураций автоежедневок"""
        return self.autodailyes_configs
    
    def get_template_headers(self, register_type: str) -> List[str]:
        """Получение шаблонных заголовков для типа реестра"""
        for config in self.autoreg_configs.values():
            if config.get('register_type') == register_type:
                return config.get('template_headers', [])
        return []
    
    def validate_register_type(self, register_type: str) -> bool:
        """Проверка валидности типа реестра"""
        return any(
            config.get('register_type') == register_type 
            for config in self.autoreg_configs.values()
        )
    
    def get_register_config_by_type(self, register_type: str) -> Optional[Dict[str, Any]]:
        """Получение конфигурации по типу реестра"""
        for config in self.autoreg_configs.values():
            if config.get('register_type') == register_type:
                return config
        return None


# Глобальный экземпляр сервиса
nexus_service = NexusService()
