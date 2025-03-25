import logging

_logger = logging.getLogger(__name__)


def migrate(cr, installed_version):
    cr.execute("""
        ALTER TABLE kw_chatbot_messenger
        DROP COLUMN echat_developer_url,
        DROP COLUMN is_developer_mode;
    """)
