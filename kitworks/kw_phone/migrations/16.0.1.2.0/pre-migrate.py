import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):

    cr.execute("""
        DELETE FROM ir_ui_view WHERE id IN (
            SELECT res_id
            FROM ir_model_data
            WHERE model = 'ir.ui.view'
              AND module LIKE '%kw_phone%'
        );""")
