# web/blueprints/api_routes.py
"""
Главный blueprint для регистрации всех API маршрутов.
Объединяет различные API модули в единую структуру.
"""

from flask import Blueprint

# Импортируем все API blueprints
from web.api.core_api import core_api_bp
from web.api.data_api import data_api_bp  
from web.api.settings_api import settings_api_bp
from web.api.correspondences_api import correspondences_api_bp
from web.api.admin_api import admin_api_bp

# Создаем главный API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')


def register_api_routes(app):
    """
    Регистрирует все API blueprints в приложении
    
    Args:
        app: Flask приложение
    """
    
    # Регистрируем основные API
    app.register_blueprint(core_api_bp, url_prefix='/api')
    app.register_blueprint(data_api_bp, url_prefix='/api')
    app.register_blueprint(settings_api_bp, url_prefix='/api')
    app.register_blueprint(correspondences_api_bp, url_prefix='/api')
    app.register_blueprint(admin_api_bp, url_prefix='/api')
    
    # Регистрируем главный API blueprint
    app.register_blueprint(api_bp)


# Совместимость со старым API
# Дублируем некоторые маршруты для обратной совместимости
@api_bp.route('/status')
def get_status():
    """Обратная совместимость для /api/status"""
    from web.api.core_api import get_system_status
    return get_system_status()


@api_bp.route('/get_data', methods=['POST'])
def get_data_api():
    """Обратная совместимость для /api/get_data"""
    from web.api.data_api import get_kasko_prolongation_data
    return get_kasko_prolongation_data()


@api_bp.route('/get-settings', methods=['GET'])  
def get_settings():
    """Обратная совместимость для /api/get-settings"""
    from web.api.settings_api import get_settings as settings_get
    return settings_get()


@api_bp.route('/save-settings', methods=['POST'])
def save_settings():
    """Обратная совместимость для /api/save-settings"""
    from web.api.settings_api import update_settings
    return update_settings()


@api_bp.route('/auto-map-headers', methods=['POST'])
def auto_map_headers():
    """Обратная совместимость для /api/auto-map-headers"""
    from web.api.correspondences_api import auto_map_headers as auto_map
    return auto_map()


@api_bp.route('/save-correspondences', methods=['POST'])
def save_correspondences():
    """Обратная совместимость для /api/save-correspondences"""
    from web.api.correspondences_api import update_correspondences
    return update_correspondences()


@api_bp.route('/cancel-processing', methods=['POST'])
def cancel_processing_nexus():
    """Обратная совместимость для /api/cancel-processing"""
    from web.api.core_api import cancel_processing
    return cancel_processing()
