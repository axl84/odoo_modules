import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    # cr.execute("""
    #    ALTER TABLE kw_message_notification_line
    #    ADD COLUMN model_notification_id INTEGER
    #    """)
    # cr.execute("""
    #       ALTER TABLE kw_message_notification_line
    #       ADD COLUMN model_notification_name VARCHAR
    #       """)
    # cr.execute("""
    #    UPDATE kw_message_notification_line
    #             SET model_notification_name = model_name;
    #    """)
    # cr.execute("""
    #       UPDATE kw_message_notification_line
    #               SET model_notification_id = model_id;
    #       """)

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
