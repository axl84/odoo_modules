import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    # from table kw_chatbot_notification delete column is_notification_for_sale
    # cr.execute("""
    #     ALTER TABLE kw_chatbot_notification
    #     DROP COLUMN is_notification_for_sale;
    # """)

    cr.execute("""
             DELETE FROM ir_ui_view
            WHERE id IN (
                SELECT res_id
                FROM ir_model_data
                WHERE module LIKE '%kw_chatbot%'
                  AND model = 'ir.ui.view'
                    );
           """)
    cr.commit()
