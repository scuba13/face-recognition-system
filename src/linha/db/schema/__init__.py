"""
Pacote de modelagem do banco de dados MongoDB para o sistema de monitoramento de presença.
"""

# Importar modelos já implementados
from src.linha.db.schema.allocations import allocation_schema, allocation_indexes
from src.linha.db.schema.batch_detections import batch_detection_schema, batch_detection_indexes, ttl_index as batch_detection_ttl
from src.linha.db.schema.attendance import attendance_schema, attendance_indexes, ttl_index as attendance_ttl

# Importar novos modelos
from src.linha.db.schema.factories import factory_schema, factory_indexes
from src.linha.db.schema.production_lines import production_line_schema, production_line_indexes
from src.linha.db.schema.workstations import workstation_schema, workstation_indexes
from src.linha.db.schema.cameras import camera_schema, camera_indexes
from src.linha.db.schema.shifts import shift_schema, shift_indexes
from src.linha.db.schema.employees import employee_schema, employee_indexes
from src.linha.db.schema.batch_control import batch_control_schema, batch_control_indexes, ttl_index as batch_control_ttl
from src.linha.db.schema.daily_detections import daily_detection_schema, daily_detection_indexes, ttl_index as daily_detection_ttl
from src.linha.db.schema.historical_summaries import historical_summary_schema, historical_summary_indexes

__all__ = [
    # Modelos já implementados
    'allocation_schema', 'allocation_indexes',
    'batch_detection_schema', 'batch_detection_indexes', 'batch_detection_ttl',
    'attendance_schema', 'attendance_indexes', 'attendance_ttl',
    
    # Novos modelos
    'factory_schema', 'factory_indexes',
    'production_line_schema', 'production_line_indexes',
    'workstation_schema', 'workstation_indexes',
    'camera_schema', 'camera_indexes',
    'shift_schema', 'shift_indexes',
    'employee_schema', 'employee_indexes',
    'batch_control_schema', 'batch_control_indexes', 'batch_control_ttl',
    'daily_detection_schema', 'daily_detection_indexes', 'daily_detection_ttl',
    'historical_summary_schema', 'historical_summary_indexes'
] 