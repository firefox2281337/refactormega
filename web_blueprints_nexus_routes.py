# web/blueprints/nexus_routes.py
"""
Blueprint для маршрутов Nexus - системы автоматизации
"""

from datetime import datetime
from flask import Blueprint, render_template, request, jsonify

from web.services.nexus_service import nexus_service
from web.utils.logging_helper import logging_helper
from web.utils.access_control import require_ip_access

nexus_bp = Blueprint('nexus', __name__)


def log_nexus_access(page_name: str, additional_info: str = ""):
    """Логирование доступа к страницам Nexus"""
    message = f"Пользователь зашёл на {page_name}"
    if additional_info:
        message += f" ({additional_info})"
    
    logging_helper.log_user_access(
        page=page_name,
        message=message
    )


@nexus_bp.route('/')
@require_ip_access
def nexus_main():
    """Главная страница Nexus"""
    try:
        log_nexus_access('nexus/main.html', 'главная страница Nexus')
        
        # Получаем общую статистику через сервис
        stats = nexus_service.get_main_page_stats()
        
        page_data = nexus_service.get_page_config('main')
        
        return render_template(
            'nexus/main.html', 
            page_data=page_data,
            stats=stats,
            current_time=datetime.now().strftime("%d.%m.%Y %H:%M:%S")
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка главной страницы Nexus: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки Nexus"), 500


# ============================================================================
# АВТОРЕЕСТРЫ
# ============================================================================

@nexus_bp.route('/autoreg')
@require_ip_access
def nexus_autoreg():
    """Страница выбора типа автореестра"""
    try:
        log_nexus_access('nexus/autoreg_type_leads.html', 'выбор типа автореестра')
        
        page_data = nexus_service.get_page_config('autoreg')
        available_types = nexus_service.get_available_register_types()
        
        return render_template(
            'nexus/autoreg_type_leads.html',
            page_data=page_data,
            available_types=available_types
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автореестров: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автореестров"), 500


@nexus_bp.route('/autoreg/prolong')
@require_ip_access
def nexus_autoreg_prolong():
    """Страница пролонгации"""
    try:
        log_nexus_access('nexus/autoreg_prolong_type_register.html', 'пролонгация')
        
        page_data = nexus_service.get_page_config('prolong')
        prolong_types = nexus_service.get_prolong_types()
        
        return render_template(
            'nexus/autoreg_prolong_type_register.html',
            page_data=page_data,
            prolong_types=prolong_types
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы пролонгации: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки пролонгации"), 500


@nexus_bp.route('/autoreg/olds')
@require_ip_access
def nexus_autoreg_olds():
    """Страница потеряшек"""
    try:
        log_nexus_access('nexus/autoreg_olds_type_register.html', 'потеряшки')
        
        page_data = nexus_service.get_page_config('olds')
        olds_types = nexus_service.get_olds_types()
        
        return render_template(
            'nexus/autoreg_olds_type_register.html',
            page_data=page_data,
            olds_types=olds_types
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы потеряшек: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки потеряшек"), 500


@nexus_bp.route('/autoreg/pilots')
@require_ip_access
def nexus_autoreg_pilots():
    """Страница пилотных проектов"""
    try:
        log_nexus_access('nexus/autoreg_pilots_type_register.html', 'пилоты')
        
        page_data = nexus_service.get_page_config('pilots')
        pilot_types = nexus_service.get_pilot_types()
        
        return render_template(
            'nexus/autoreg_pilots_type_register.html',
            page_data=page_data,
            pilot_types=pilot_types
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы пилотов: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки пилотов"), 500


# ============================================================================
# КОНКРЕТНЫЕ ТИПЫ АВТОРЕЕСТРОВ
# ============================================================================

@nexus_bp.route('/autoreg/prolong/ipoteka')
@require_ip_access
def nexus_autoreg_prolong_ipoteka():
    """Страница ипотечной пролонгации"""
    try:
        log_nexus_access('nexus/ipoteka.html', 'ипотечная пролонгация')
        
        autoreg_data = nexus_service.get_autoreg_config('ipoteka')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='Ипотека'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ипотеки: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ипотеки"), 500


@nexus_bp.route('/autoreg/prolong/ipoteka-msk')
@require_ip_access
def nexus_autoreg_prolong_ipoteka_msk():
    """Страница московской ипотечной пролонгации"""
    try:
        log_nexus_access('nexus/ipoteka_msk.html', 'московская ипотека')
        
        autoreg_data = nexus_service.get_autoreg_config('ipoteka_msk')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='Ипотека_мск'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы московской ипотеки: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки московской ипотеки"), 500


@nexus_bp.route('/autoreg/prolong/kasko')
@require_ip_access
def nexus_autoreg_prolong_kasko():
    """Страница пролонгации КАСКО"""
    try:
        log_nexus_access('nexus/kasko.html', 'пролонгация КАСКО')
        
        autoreg_data = nexus_service.get_autoreg_config('kasko')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='КАСКО'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы КАСКО: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки КАСКО"), 500


@nexus_bp.route('/autoreg/prolong/kasko-iz-osago')
@require_ip_access
def nexus_autoreg_prolong_kasko_iz_osago():
    """Страница пролонгации КАСКО из ОСАГО"""
    try:
        log_nexus_access('nexus/kasko_iz_osago.html', 'КАСКО из ОСАГО')
        
        autoreg_data = nexus_service.get_autoreg_config('kasko_iz_osago')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='КАСКО_ИЗ_ОСАГО_4_1'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы КАСКО из ОСАГО: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки КАСКО из ОСАГО"), 500


@nexus_bp.route('/autoreg/prolong/osago')
@require_ip_access
def nexus_autoreg_prolong_osago():
    """Страница пролонгации ОСАГО"""
    try:
        log_nexus_access('nexus/osago.html', 'пролонгация ОСАГО')
        
        autoreg_data = nexus_service.get_autoreg_config('osago')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='ОСАГО'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ОСАГО: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ОСАГО"), 500


@nexus_bp.route('/autoreg/prolong/mbg')
@require_ip_access
def nexus_autoreg_prolong_mbg():
    """Страница пролонгации MBG"""
    try:
        log_nexus_access('nexus/mbg.html', 'пролонгация МБГ')
        
        autoreg_data = nexus_service.get_autoreg_config('mbg')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='МБГ'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы МБГ: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки МБГ"), 500


# ============================================================================
# ПОТЕРЯШКИ
# ============================================================================

@nexus_bp.route('/autoreg/olds/ipowa')
@require_ip_access
def nexus_autoreg_olds_ipowa():
    """Страница ипотечных потеряшек WA"""
    try:
        log_nexus_access('nexus/ipoteka_wa.html', 'ипотечные потеряшки WA')
        
        autoreg_data = nexus_service.get_autoreg_config('ipoteka_wa')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='Ипотека_WA'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ипотечных потеряшек WA: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ипотечных потеряшек WA"), 500


@nexus_bp.route('/autoreg/olds/osagowa')
@require_ip_access
def nexus_autoreg_olds_osagowa():
    """Страница ОСАГО потеряшек WA"""
    try:
        log_nexus_access('nexus/osago_wa.html', 'ОСАГО потеряшки WA')
        
        autoreg_data = nexus_service.get_autoreg_config('osago_wa')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='ОСАГО_WA'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ОСАГО потеряшек WA: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ОСАГО потеряшек WA"), 500


@nexus_bp.route('/autoreg/olds/osago41')
@require_ip_access
def nexus_autoreg_olds_osago41():
    """Страница ОСАГО потеряшек 4.1"""
    try:
        log_nexus_access('nexus/osago_4_1_up.html', 'ОСАГО потеряшки 4.1')
        
        autoreg_data = nexus_service.get_autoreg_config('osago_4_1_up')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='ОСАГО_4_1'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ОСАГО 4.1: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ОСАГО 4.1"), 500


# ============================================================================
# ПИЛОТЫ
# ============================================================================

@nexus_bp.route('/autoreg/pilots/ipoteka_kom_bank')
@require_ip_access
def nexus_autoreg_pilots_ipoteka_kom_bank():
    """Страница ипотеки коммерческих банков"""
    try:
        log_nexus_access('nexus/ipoteka_kom_bank.html', 'ипотека коммерческих банков')
        
        autoreg_data = nexus_service.get_autoreg_config('ipoteka_kom_bank')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='Ипотека_ком_банки'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ипотеки коммерческих банков: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ипотеки коммерческих банков"), 500


@nexus_bp.route('/autoreg/pilots/ipoteka_sos')
@require_ip_access
def nexus_autoreg_pilots_ipoteka_sos():
    """Страница ипотеки SOS"""
    try:
        log_nexus_access('nexus/ipoteka_sos.html', 'ипотека SOS')
        
        autoreg_data = nexus_service.get_autoreg_config('ipoteka_sos')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='Ипотека_SOS'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ипотеки SOS: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ипотеки SOS"), 500


@nexus_bp.route('/autoreg/pilots/f1')
@require_ip_access
def nexus_autoreg_pilots_f1():
    """Страница OneFactor"""
    try:
        log_nexus_access('nexus/f1.html', 'OneFactor')
        
        autoreg_data = nexus_service.get_autoreg_config('f1')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='f1'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы OneFactor: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки OneFactor"), 500


@nexus_bp.route('/autoreg/pilots/osago_kz')
@require_ip_access
def nexus_autoreg_pilots_osago_kz():
    """Страница ОСАГО КЗ"""
    try:
        log_nexus_access('nexus/osago_kz.html', 'ОСАГО КЗ')
        
        autoreg_data = nexus_service.get_autoreg_config('osago_kz')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='ОСАГО_КЗ'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ОСАГО КЗ: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ОСАГО КЗ"), 500


@nexus_bp.route('/autoreg/pilots/dvr')
@require_ip_access
def nexus_autoreg_pilots_dvr():
    """Страница проекта ДВР"""
    try:
        log_nexus_access('nexus/dvr.html', 'проект ДВР')
        
        autoreg_data = nexus_service.get_autoreg_config('dvr')
        
        return render_template(
            'nexus/autoreg.html',
            autoreg_data=autoreg_data,
            register_type='ДВР'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ДВР: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ДВР"), 500


# ============================================================================
# АВТОЕЖЕДНЕВКИ
# ============================================================================

@nexus_bp.route('/autodailyes')
@require_ip_access
def nexus_autodailyes():
    """Страница выбора периодичности автоежедневок"""
    try:
        log_nexus_access('nexus/autodailyes_select_task_period.html', 'выбор периодичности автоежедневок')
        
        page_data = nexus_service.get_page_config('autodailyes')
        available_periods = nexus_service.get_autodailyes_periods()
        
        return render_template(
            'nexus/autodailyes_select_task_period.html',
            page_data=page_data,
            available_periods=available_periods
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автоежедневок: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автоежедневок"), 500


@nexus_bp.route('/autodailyes/dailyes')
@require_ip_access
def nexus_autodailyes_dailyes():
    """Страница ежедневных задач"""
    try:
        log_nexus_access('nexus/autodailyes_select_task_dailyes.html', 'ежедневные задачи')
        
        page_data = nexus_service.get_page_config('dailyes')
        daily_tasks = nexus_service.get_daily_tasks()
        
        return render_template(
            'nexus/autodailyes_select_task_dailyes.html',
            page_data=page_data,
            daily_tasks=daily_tasks
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы ежедневных задач: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки ежедневных задач"), 500


@nexus_bp.route('/autodailyes/weeks')
@require_ip_access
def nexus_autodailyes_weeks():
    """Страница еженедельных задач"""
    try:
        log_nexus_access('nexus/autodailyes_select_task_weeks.html', 'еженедельные задачи')
        
        page_data = nexus_service.get_page_config('weeks')
        weekly_tasks = nexus_service.get_weekly_tasks()
        
        return render_template(
            'nexus/autodailyes_select_task_weeks.html',
            page_data=page_data,
            weekly_tasks=weekly_tasks
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы еженедельных задач: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки еженедельных задач"), 500


# ============================================================================
# КОНКРЕТНЫЕ АВТОЕЖЕДНЕВКИ
# ============================================================================

@nexus_bp.route('/autodailyes/dailyes/autoverint')
@require_ip_access
def nexus_autodailyes_dailyes_autoverint():
    """Страница автоматизации Verint"""
    try:
        log_nexus_access('nexus/autoverint.html', 'автоматизация Verint')
        
        autodailyes_data = nexus_service.get_autodailyes_config('autoverint')
        
        return render_template(
            'nexus/autodailyes.html',
            autodailyes_data=autodailyes_data,
            task_type='autoverint'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автоматизации Verint: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автоматизации Verint"), 500


@nexus_bp.route('/autodailyes/dailyes/autoolds')
@require_ip_access
def nexus_autodailyes_dailyes_autoolds():
    """Страница автоматизации старых записей"""
    try:
        log_nexus_access('nexus/autoolds.html', 'автоматизация старых записей')
        
        autodailyes_data = nexus_service.get_autodailyes_config('autoolds')
        
        return render_template(
            'nexus/autodailyes.html',
            autodailyes_data=autodailyes_data,
            task_type='autoolds'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автоматизации старых записей: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автоматизации старых записей"), 500


@nexus_bp.route('/autodailyes/dailyes/autojarvis')
@require_ip_access
def nexus_autodailyes_dailyes_autojarvis():
    """Страница автоматизации Jarvis"""
    try:
        log_nexus_access('nexus/autojarvis.html', 'автоматизация Jarvis')
        
        autodailyes_data = nexus_service.get_autodailyes_config('autojarvis')
        
        return render_template(
            'nexus/autodailyes.html',
            autodailyes_data=autodailyes_data,
            task_type='autojarvis'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автоматизации Jarvis: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автоматизации Jarvis"), 500


@nexus_bp.route('/autodailyes/dailyes/autodeals')
@require_ip_access
def nexus_autodailyes_dailyes_autodeals():
    """Страница автоматизации сделок"""
    try:
        log_nexus_access('nexus/autodeals.html', 'автоматизация сделок')
        
        autodailyes_data = nexus_service.get_autodailyes_config('autodeals')
        
        return render_template(
            'nexus/autodailyes.html',
            autodailyes_data=autodailyes_data,
            task_type='autodeals'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автоматизации сделок: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автоматизации сделок"), 500


@nexus_bp.route('/autodailyes/weeks/autochekcompany')
@require_ip_access
def nexus_autodailyes_weeks_autochekcompany():
    """Страница автоматической проверки компаний"""
    try:
        log_nexus_access('nexus/autochekcompany.html', 'автопроверка компаний')
        
        autodailyes_data = nexus_service.get_autodailyes_config('autochekcompany')
        
        return render_template(
            'nexus/autodailyes.html',
            autodailyes_data=autodailyes_data,
            task_type='autochekcompany'
        )
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка страницы автопроверки компаний: {str(e)}")
        return render_template('site/error.html', error_message="Ошибка загрузки автопроверки компаний"), 500


# ============================================================================
# API ENDPOINTS
# ============================================================================

@nexus_bp.route('/api/config/<config_type>')
def get_nexus_config(config_type):
    """API для получения конфигураций Nexus"""
    try:
        if config_type == 'autoreg':
            config = nexus_service.get_autoreg_configs()
        elif config_type == 'autodailyes':
            config = nexus_service.get_autodailyes_configs()
        elif config_type == 'page':
            config = nexus_service.get_page_configs()
        else:
            return jsonify({'error': 'Неизвестный тип конфигурации'}), 400
        
        return jsonify({
            'success': True,
            'data': config
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения конфигурации {config_type}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения конфигурации'
        }), 500


@nexus_bp.route('/api/stats')
def get_nexus_stats():
    """API для получения статистики Nexus"""
    try:
        stats = nexus_service.get_detailed_stats()
        
        return jsonify({
            'success': True,
            'data': stats
        })
        
    except Exception as e:
        logging_helper.log_error(f"Ошибка получения статистики Nexus: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Ошибка получения статистики'
        }), 500


@nexus_bp.errorhandler(404)
def nexus_not_found(error):
    """Обработчик ошибки 404 для Nexus"""
    logging_helper.log_user_access(
        page="nexus/404",
        message=f"Страница Nexus не найдена: {request.url}"
    )
    return render_template('nexus/error.html', error_code=404), 404


@nexus_bp.errorhandler(500)
def nexus_server_error(error):
    """Обработчик ошибки 500 для Nexus"""
    logging_helper.log_error(
        f"Внутренняя ошибка в Nexus: {str(error)}",
        context={'url': request.url, 'method': request.method}
    )
    return render_template('nexus/error.html', error_code=500), 500
