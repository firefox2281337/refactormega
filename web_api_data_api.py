# web/api/data_api.py
"""
API для работы с данными
"""

from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from web.services.data_service import data_service
from web.utils.logging_helper import log_user_access
from web.utils.validators import validate_date_format, validate_required_fields

data_api_bp = Blueprint('data_api', __name__)


@data_api_bp.route('/kasko-prolongation')
def get_kasko_prolongation():
    """
    Получение данных о пролонгации КАСКО
    
    Query параметры:
    - start_date: Начальная дата (YYYY-MM-DD)
    - end_date: Конечная дата (YYYY-MM-DD)
    - insurance_type: Типы страхования (разделенные запятой)
    - channel: Канал продаж
    - branch_code: Коды филиалов (разделенные запятой)
    """
    try:
        # Получаем параметры запроса
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        insurance_type = request.args.get('insurance_type')
        channel = request.args.get('channel')
        branch_code = request.args.get('branch_code')
        
        # Валидируем даты если они переданы
        if start_date and not validate_date_format(start_date):
            return jsonify({'error': 'Неверный формат start_date. Используйте YYYY-MM-DD'}), 400
            
        if end_date and not validate_date_format(end_date):
            return jsonify({'error': 'Неверный формат end_date. Используйте YYYY-MM-DD'}), 400

        # Логируем запрос
        log_user_access(
            page="КАСКО Пролонгация API",
            client_ip=request.remote_addr,
            current_time=datetime.now().strftime("%Y.%m.%d %H:%M:%S"),
            message=f"Запрос данных: {start_date} - {end_date}, тип: {insurance_type}"
        )

        # Преобразуем параметры
        insurance_type_list = insurance_type.split(',') if insurance_type else None
        branch_code_list = branch_code.split(',') if branch_code else None

        # Получаем данные
        results = data_service.get_kasko_prolongation_data(
            start_date=start_date,
            end_date=end_date,
            insurance_type=insurance_type_list,
            channel=channel,
            branch_code=branch_code_list
        )

        if results:
            return jsonify({
                'success': True,
                'data': results,
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Данные не найдены или произошла ошибка во время запроса',
                'data': {'columns': [], 'rows': []}
            }), 404

    except Exception as e:
        current_app.logger.error(f"Ошибка в get_kasko_prolongation: {str(e)}")
        return jsonify({'error': f'Ошибка получения данных: {str(e)}'}), 500


@data_api_bp.route('/contracts/contacts', methods=['POST'])
def get_contracts_contacts():
    """
    Получение контактных данных по номерам договоров
    
    Body:
    {
        "contracts": ["contract1", "contract2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'contracts' not in data:
            return jsonify({'error': 'Поле contracts обязательно'}), 400
        
        contracts = data['contracts']
        
        if not isinstance(contracts, list) or not contracts:
            return jsonify({'error': 'contracts должен быть непустым списком'}), 400
        
        # Формируем строку для SQL запроса
        contracts_string = "(" + ",".join(f"'{contract}'" for contract in contracts) + ")"
        
        # Выполняем запрос
        result = data_service.execute_sql_query(contracts_string, "contacts")
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Контактные данные не найдены',
                'data': []
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Ошибка в get_contracts_contacts: {str(e)}")
        return jsonify({'error': f'Ошибка получения контактных данных: {str(e)}'}), 500


@data_api_bp.route('/contracts/registration', methods=['POST'])
def get_contracts_registration():
    """
    Получение данных регистрации по ID записей в DWH
    
    Body:
    {
        "subject_ids": ["id1", "id2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'subject_ids' not in data:
            return jsonify({'error': 'Поле subject_ids обязательно'}), 400
        
        subject_ids = data['subject_ids']
        
        if not isinstance(subject_ids, list) or not subject_ids:
            return jsonify({'error': 'subject_ids должен быть непустым списком'}), 400
        
        # Формируем строку для SQL запроса
        ids_string = "(" + ",".join(f"'{subject_id}'" for subject_id in subject_ids) + ")"
        
        # Выполняем запрос
        result = data_service.execute_sql_query(ids_string, "registration")
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Данные регистрации не найдены',
                'data': []
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Ошибка в get_contracts_registration: {str(e)}")
        return jsonify({'error': f'Ошибка получения данных регистрации: {str(e)}'}), 500


@data_api_bp.route('/contracts/passport', methods=['POST'])
def get_contracts_passport():
    """
    Получение паспортных данных по ID записей в DWH
    
    Body:
    {
        "subject_ids": ["id1", "id2", ...]
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'subject_ids' not in data:
            return jsonify({'error': 'Поле subject_ids обязательно'}), 400
        
        subject_ids = data['subject_ids']
        
        if not isinstance(subject_ids, list) or not subject_ids:
            return jsonify({'error': 'subject_ids должен быть непустым списком'}), 400
        
        # Формируем строку для SQL запроса
        ids_string = "(" + ",".join(f"'{subject_id}'" for subject_id in subject_ids) + ")"
        
        # Выполняем запрос
        result = data_service.execute_sql_query(ids_string, "passport")
        
        if result:
            return jsonify({
                'success': True,
                'data': result,
                'count': len(result),
                'timestamp': datetime.now().isoformat()
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Паспортные данные не найдены',
                'data': []
            }), 404
            
    except Exception as e:
        current_app.logger.error(f"Ошибка в get_contracts_passport: {str(e)}")
        return jsonify({'error': f'Ошибка получения паспортных данных: {str(e)}'}), 500


@data_api_bp.route('/gender/by-patronymic')
def get_gender_by_patronymic():
    """
    Определение пола по отчеству
    
    Query параметры:
    - patronymic: Отчество
    """
    try:
        patronymic = request.args.get('patronymic')
        
        if not patronymic:
            return jsonify({'error': 'Параметр patronymic обязателен'}), 400
        
        gender = data_service.get_gender_from_patronymic(patronymic)
        
        return jsonify({
            'success': True,
            'patronymic': patronymic,
            'gender': gender,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Ошибка в get_gender_by_patronymic: {str(e)}")
        return jsonify({'error': f'Ошибка определения пола: {str(e)}'}), 500
