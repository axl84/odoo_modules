import logging
from datetime import datetime, timedelta
from unittest.mock import patch
from odoo.tests import common
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Separate function to set up the mock
def mock_requests_response():
    return {
        "StatementsResponse": {
            "statements": [
                {
                    "HS43O0311L01YW": {
                        "AUT_MY_CRF": "3266712365",
                        "AUT_MY_MFO": "305299",
                        "AUT_MY_ACC": "UA123",
                        "AUT_MY_NAM": "Іванов Ю.М. ФОП",
                        "AUT_MY_MFO_NAME": 'АТ КБ "ПРИВАТБАНК"',
                        "AUT_CNTR_CRF": "123456",
                        "AUT_CNTR_MFO": "322001",
                        "AUT_CNTR_ACC": "UA456",
                        "AUT_CNTR_NAM": "ФОП Іванов Іван Іванович",
                        "AUT_CNTR_MFO_NAME": 'АТ "УНІВЕРСАЛ БАНК"',
                        "BPL_CCY": "UAH",
                        "BPL_FL_REAL": "r",
                        "BPL_FL_DC": "C",
                        "BPL_PR_PR": "r",
                        "BPL_DOC_TYP": "p",
                        "BPL_NUM_DOC": "123456.",
                        "BPL_DAT_KL": "23.07.2024",
                        "BPL_DAT_OD": "23.07.2024",
                        "BPL_OSND": "інші інформаційні послуги",
                        "BPL_SUM": "1000.00",
                        "BPL_SUM_E": "1000.00",
                        "BPL_REF": "HS43O0311L01YW",
                        "BPL_REFN": "P",
                        "BPL_TIM_P": "12:34",
                        "DATE_TIME_DAT_OD_TIM_P": "23.07.2024 12:34:56",
                        "ID": "123",
                        "TRANTYPE": "C",
                        "TECHNICAL_TRANSACTION_ID": "123_online"
                    }
                }
            ]
        }
    }


class TestAutoclientPrivat(common.TransactionCase):

    def setUp(self):
        super(TestAutoclientPrivat, self).setUp()

        self.bank = self.env["res.bank"].create(
            {
                "name": "Privat24",
                "active": True,
                "bic": "1234567",
            }
        )

        self.company = self.env["res.company"].search([], limit=1)
        self.partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
                "company_id": self.company.id,
            }
        )
        self.company.write({"partner_id": self.partner.id})

        self.bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "UA573052990000026002005022255",
                "bank_id": self.bank.id,
                "partner_id": self.partner.id,
                "company_id": self.company.id,
                "currency_id": self.env.ref("base.UAH").id,
            }
        )

        debit_account = self.env["account.account"].create(
            {
                "name": "Default Debit Account",
                "code": "DEBIT.ACC3",
                "account_type": "asset_current",
                "company_id": self.company.id,
            }
        )

        credit_account = self.env["account.account"].create(
            {
                "name": "Default Credit Account",
                "code": "CREDIT.ACC3",
                "account_type": "liability_current",
                "company_id": self.company.id,
            }
        )

        suspent_account = self.env["account.account"].create(
            {
                "name": "Suspense Account",
                "code": "SUSPENSE.ACC3",
                "account_type": "asset_current",
                "company_id": self.company.id,
            }
        )

        self.account_journal = self.env["account.journal"].create(
            {
                "name": "Privat24_Test3",
                "type": "bank",
                "code": "PRIVAT24_TEST3",
                "bank_account_id": self.bank_account.id,
                "default_debit_account_id": debit_account.id,
                "default_credit_account_id": credit_account.id,
                "suspense_account_id": suspent_account.id,
                "bank_statements_source": "privat24_autoclient",
                "kw_bank_import_initial_date": (
                    datetime.now().date() - timedelta(days=7)
                ),
                "privat24_id": "9e2a762a-f149-4fed-9024-8fbdf83797f0",
                "privat24_token": "zHLUYit9oUngW6pgcagjxk1y"
                "1QDrISBMz6G+Tds/VNWJxMyGfbKqo9QBwo"
                "+V6X29NByin4VzyL7PbK+7z"
                "MbKJI7n0fnmbzX8J+OcKdngW4O+FaEnjU"
                "R2wxuGrkgri4slSL3GOxl7S"
                "4bjlwaVtq8tbYqfl5Lcd0rVTALPIiq46G8D"
                "OGoeTxD9ZaNNpuPrJ0BlQiPr"
                "SQ8n7S21Viwjxo3d+AU7+BH2f/J0oP/wx"
                "6nOGdJdyhHiTK/Rt1sr5y9Sr8v7H2ZXWMU=",
                "privat24_auto_sync": False,
            }
        )

        self.acc_bank_statement = self.env["account.bank.statement"].create(
            {
                "journal_id": self.account_journal.id,
                "line_ids": [
                    (0, 0, {
                        "name": "Test Line",
                        "amount": 0.0,
                        "date": datetime.now(),
                        "journal_id": self.account_journal.id,
                    })
                ],
            }
        )

    def test_kw_privat24_init_sync(self):
        """Test kw_privat24_init_sync method."""
        self.account_journal.kw_privat24_init_sync()
        self.assertEqual(
            self.account_journal.kw_privat24_downloading_date,
            self.account_journal.kw_bank_import_initial_date,
        )

    @patch("requests.get")
    def test_perform_kw_privat24_self_sync(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_requests_response()

        self.assertLessEqual(
            self.account_journal.kw_privat24_downloading_date,
            datetime.now().date(),
            "Incorrect downloading date.",
        )

        statements = self.env["account.bank.statement"].search(
            [("journal_id", "=", self.account_journal.id)]
        )
        self.assertTrue(statements, "No bank statements were created.")

        if statements:
            last_statement = statements[0]
            expected_balance_end_real = 0
            self.assertEqual(
                last_statement.balance_end_real,
                expected_balance_end_real,
                "Incorrect balance_end_real value.",
            )

        self.env["account.bank.statement"].unlink()
        self.account_journal.kw_privat24_self_sync()
        self.assertEqual(
            self.account_journal.kw_privat24_downloading_date,
            datetime.now().date(),
            "Incorrect downloading date.",
        )

    @patch("requests.get")
    def test_kw_privat24_self_sync(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = mock_requests_response()

        self.account_journal.kw_privat24_self_sync()
        self.assertLessEqual(
            self.account_journal.kw_privat24_downloading_date,
            datetime.now().date(),
        )

    def test_incorrect_kw_privat24_self_sync(self):
        self.account_journal.kw_privat24_downloading_date = False
        self.assertRaises(
            UserError, self.account_journal.kw_privat24_self_sync
        )
        self.account_journal.kw_privat24_downloading_date = (
            datetime.now().date() + timedelta(days=1)
        )
