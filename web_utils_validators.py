# web/utils/validators.py
"""
Утилиты для валидации данных
"""

import re
from datetime import datetime
from typing import Dict, Any, List, Optional


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Optional[str]:
    """
    Проверяет наличие обязательных полей в данных
    
    Args:
        data: Словарь с данными
        required_fields: Список обязательных полей
        
    Returns:
        str: Сообщение об ошибке или None если все поля присутствуют
    """
    if not data:
        return "Данные не переданы"
    
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        return f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
    
    return None


def validate_date_format(date_string: str, date_format: str = "%Y-%m-%d") -> bool:
    """
    Проверяет корректность формата даты
    
    Args:
        date_string: Строка с датой
        date_format: Формат даты (по умолчанию YYYY-MM-DD)
        
    Returns:
        bool: True если формат корректный
    """
    try:
        datetime.strptime(date_string, date_format)
        return True
    except ValueError:
        return False


def validate_email(email: str) -> bool:
    """
    Проверяет корректность email адреса
    
    Args:
        email: Email адрес
        
    Returns:
        bool: True если email корректный
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_phone(phone: str) -> bool:
    """
    Проверяет корректность номера телефона
    
    Args:
        phone: Номер телефона
        
    Returns:
        bool: True если номер корректный
    """
    # Удаляем все символы кроме цифр и +
    cleaned_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем российские номера
    patterns = [
        r'^\+7\d{10}$',  # +7XXXXXXXXXX
        r'^8\d{10}$',    # 8XXXXXXXXXX
        r'^7\d{10}$',    # 7XXXXXXXXXX
        r'^\d{10}$'      # XXXXXXXXXX
    ]
    
    return any(re.match(pattern, cleaned_phone) for pattern in patterns)


def validate_inn(inn: str) -> bool:
    """
    Проверяет корректность ИНН
    
    Args:
        inn: ИНН
        
    Returns:
        bool: True если ИНН корректный
    """
    if not inn or not inn.isdigit():
        return False
    
    if len(inn) == 10:
        # ИНН юридического лица
        check_digit = (
            (int(inn[0]) * 2 + int(inn[1]) * 4 + int(inn[2]) * 10 +
             int(inn[3]) * 3 + int(inn[4]) * 5 + int(inn[5]) * 9 +
             int(inn[6]) * 4 + int(inn[7]) * 6 + int(inn[8]) * 8) % 11
        ) % 10
        return check_digit == int(inn[9])
    
    elif len(inn) == 12:
        # ИНН физического лица
        check_digit1 = (
            (int(inn[0]) * 7 + int(inn[1]) * 2 + int(inn[2]) * 4 +
             int(inn[3]) * 10 + int(inn[4]) * 3 + int(inn[5]) * 5 +
             int(inn[6]) * 9 + int(inn[7]) * 4 + int(inn[8]) * 6 +
             int(inn[9]) * 8) % 11
        ) % 10
        
        check_digit2 = (
            (int(inn[0]) * 3 + int(inn[1]) * 7 + int(inn[2]) * 2 +
             int(inn[3]) * 4 + int(inn[4]) * 10 + int(inn[5]) * 3 +
             int(inn[6]) * 5 + int(inn[7]) * 9 + int(inn[8]) * 4 +
             int(inn[9]) * 6 + int(inn[10]) * 8) % 11
        ) % 10
        
        return check_digit1 == int(inn[10]) and check_digit2 == int(inn[11])
    
    return False


def validate_snils(snils: str) -> bool:
    """
    Проверяет корректность СНИЛС
    
    Args:
        snils: СНИЛС
        
    Returns:
        bool: True если СНИЛС корректный
    """
    # Удаляем все символы кроме цифр
    cleaned_snils = re.sub(r'\D', '', snils)
    
    if len(cleaned_snils) != 11:
        return False
    
    # Проверяем контрольную сумму
    digits = [int(d) for d in cleaned_snils[:9]]
    check_sum = sum(digit * (9 - i) for i, digit in enumerate(digits))
    
    if check_sum < 100:
        expected_check = check_sum
    elif check_sum in [100, 101]:
        expected_check = 0
    else:
        expected_check = check_sum % 101
        if expected_check == 100:
            expected_check = 0
    
    actual_check = int(cleaned_snils[9:11])
    return expected_check == actual_check


def validate_passport(passport: str) -> bool:
    """
    Проверяет корректность номера паспорта РФ
    
    Args:
        passport: Номер паспорта
        
    Returns:
        bool: True если номер корректный
    """
    # Удаляем все символы кроме цифр
    cleaned_passport = re.sub(r'\D', '', passport)
    
    # Паспорт РФ: 4 цифры серии + 6 цифр номера
    return len(cleaned_passport) == 10 and cleaned_passport.isdigit()


def validate_contract_number(contract_number: str) -> bool:
    """
    Проверяет корректность номера договора
    
    Args:
        contract_number: Номер договора
        
    Returns:
        bool: True если номер корректный
    """
    if not contract_number:
        return False
    
    # Базовая проверка - не пустая строка и разумная длина
    return 3 <= len(contract_number.strip()) <= 50


def validate_vin(vin: str) -> bool:
    """
    Проверяет корректность VIN номера
    
    Args:
        vin: VIN номер
        
    Returns:
        bool: True если VIN корректный
    """
    if not vin or len(vin) != 17:
        return False
    
    # VIN не содержит символы I, O, Q
    forbidden_chars = ['I', 'O', 'Q']
    if any(char in vin.upper() for char in forbidden_chars):
        return False
    
    # VIN содержит только цифры и буквы
    return re.match(r'^[A-HJ-NPR-Z0-9]{17}$', vin.upper()) is not None


def validate_license_plate(plate: str) -> bool:
    """
    Проверяет корректность российского автомобильного номера
    
    Args:
        plate: Автомобильный номер
        
    Returns:
        bool: True если номер корректный
    """
    if not plate:
        return False
    
    # Российские номера: А123БВ123 или А123БВ12
    patterns = [
        r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]{2}\d{2,3}$',  # Обычные номера
        r'^\d{4}[АВЕКМНОРСТУХ]{2}\d{2,3}$',               # Такси
        r'^[АВЕКМНОРСТУХ]\d{3}[АВЕКМНОРСТУХ]\d{2,3}$'     # Мотоциклы
    ]
    
    cleaned_plate = plate.upper().replace(' ', '')
    return any(re.match(pattern, cleaned_plate) for pattern in patterns)


def validate_amount(amount: str, min_value: float = 0, max_value: float = None) -> bool:
    """
    Проверяет корректность денежной суммы
    
    Args:
        amount: Сумма в виде строки
        min_value: Минимальное значение
        max_value: Максимальное значение
        
    Returns:
        bool: True если сумма корректная
    """
    try:
        # Заменяем запятую на точку для российского формата
        cleaned_amount = amount.replace(',', '.').replace(' ', '')
        value = float(cleaned_amount)
        
        if value < min_value:
            return False
        
        if max_value is not None and value > max_value:
            return False
        
        return True
    except (ValueError, TypeError):
        return False


def validate_percentage(percentage: str) -> bool:
    """
    Проверяет корректность процентного значения (0-100)
    
    Args:
        percentage: Процент в виде строки
        
    Returns:
        bool: True если процент корректный
    """
    try:
        # Заменяем запятую на точку и убираем знак %
        cleaned_percentage = percentage.replace(',', '.').replace('%', '').strip()
        value = float(cleaned_percentage)
        return 0 <= value <= 100
    except (ValueError, TypeError):
        return False


def validate_year(year: str, min_year: int = 1900, max_year: int = None) -> bool:
    """
    Проверяет корректность года
    
    Args:
        year: Год в виде строки
        min_year: Минимальный год
        max_year: Максимальный год (по умолчанию текущий + 10)
        
    Returns:
        bool: True если год корректный
    """
    try:
        year_int = int(year)
        
        if max_year is None:
            max_year = datetime.now().year + 10
        
        return min_year <= year_int <= max_year
    except (ValueError, TypeError):
        return False


def sanitize_string(text: str, max_length: int = None) -> str:
    """
    Очищает строку от опасных символов
    
    Args:
        text: Исходная строка
        max_length: Максимальная длина
        
    Returns:
        str: Очищенная строка
    """
    if not text:
        return ""
    
    # Удаляем потенциально опасные символы
    cleaned = re.sub(r'[<>"\'\x00-\x1f\x7f-\x9f]', '', str(text))
    
    # Ограничиваем длину
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()


def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """
    Проверяет допустимость расширения файла
    
    Args:
        filename: Имя файла
        allowed_extensions: Список допустимых расширений (с точкой)
        
    Returns:
        bool: True если расширение допустимо
    """
    if not filename:
        return False
    
    file_extension = '.' + filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return file_extension in [ext.lower() for ext in allowed_extensions]


def validate_ip_address(ip: str) -> bool:
    """
    Проверяет корректность IP адреса
    
    Args:
        ip: IP адрес
        
    Returns:
        bool: True если IP корректный
    """
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        
        return True
    except (ValueError, AttributeError):
        return False
