import logging

from datetime import datetime, timedelta
from unittest.mock import patch
import random

from odoo.tests import common

# import class Privat24AutoclientApi from the file
from odoo.addons.kw_bank_autoclient_privat24_base.models.api import (
    Privat24AutoclientApi,
)

_logger = logging.getLogger(__name__)


class TestAutoclientPrivat(common.TransactionCase):

    def setUp(self):
        super(TestAutoclientPrivat, self).setUp()

        self.partner = self.env.ref(
            'kw_bank_autoclient_privat24_base.demo_privat24_base_partner'
        )
        self.company = self.env.ref(
            'kw_bank_autoclient_privat24_base.demo_privat24_base_company'
        )
        self.bank_account = self.env.ref(
            'kw_bank_autoclient_privat24_base.demo_privat24_base_bank_account'
        )
        self.account_journal = self.env.ref(
            'kw_bank_autoclient_privat24_base.demo_privat24_base_journal'
        )
        # Link the partner to the company
        self.partner.write({"company_id": self.company.id})

        self.mock_requests_get = patch("requests.get").start()
        self.addCleanup(patch.stopall)

    def create_mock_transactions(self, start_date, end_date):
        mock_value_privat24 = []
        for _ in range(10):
            transaction_date = start_date + timedelta(
                days=random.randint(0, (end_date - start_date).days)
            )

            statement_id = f"HS41O030{random.randint(1000, 9999)}"
            statement = {
                "HS43O0311L01YW": {
                    "AUT_MY_CRF": "3266712365",
                    "AUT_MY_MFO": "305299",
                    "AUT_MY_ACC": (
                        f"UA{random.randint(100, 999)}"
                    ),
                    "AUT_MY_NAM": "Іванов Ю.М. ФОП",
                    "AUT_MY_MFO_NAME": 'АТ КБ "ПРИВАТБАНК"',
                    "AUT_CNTR_CRF": (
                        random.randint(100000, 999999)
                    ),
                    "AUT_CNTR_MFO": "322001",
                    "AUT_CNTR_ACC": (
                        f"UA{random.randint(100, 999)}"
                    ),
                    "AUT_CNTR_NAM": "ФОП Іванов Іван Іванович",
                    "AUT_CNTR_MFO_NAME": 'АТ "УНІВЕРСАЛ БАНК"',
                    "BPL_CCY": "UAH",
                    "BPL_FL_REAL": "r",
                    "BPL_FL_DC": "C",
                    "BPL_PR_PR": "r",
                    "BPL_DOC_TYP": "p",
                    "BPL_NUM_DOC": f"{random.randint(100000, 999999)}.",
                    "BPL_DAT_KL": transaction_date.strftime("%d.%m.%Y"),
                    "BPL_DAT_OD": transaction_date.strftime("%d.%m.%Y"),
                    "BPL_OSND": "інші інформаційні послуги",
                    "BPL_SUM": f"{random.uniform(1000, 50000):.2f}",
                    "BPL_SUM_E": f"{random.uniform(1000, 50000):.2f}",
                    "BPL_REF": statement_id,
                    "BPL_REFN": "P",
                    "BPL_TIM_P": (
                        f"{random.randint(0, 23):02d}"
                        f":{random.randint(0, 59):02d}"
                    ),
                    "DATE_TIME_DAT_OD_TIM_P": transaction_date.strftime(
                        "%d.%m.%Y %H:%M:%S"
                    ),
                    "ID": f"{random.randint(100, 999)}",
                    "TRANTYPE": "C",
                    "TECHNICAL_TRANSACTION_ID": (
                        f"{random.randint(100, 999)}_online"
                    ),
                }
            }
            mock_value_privat24.append(statement)

        return mock_value_privat24

    def check_get_statement(self, start_date, end_date):
        self.mock_requests_get.return_value.status_code = 200

        mock_value_privat24 = self.create_mock_transactions(
            start_date, end_date
        )
        self.mock_requests_get.return_value.json.return_value = {
            "StatementsResponse": {"statements": mock_value_privat24}
        }

        api = Privat24AutoclientApi(
            self.bank_account.acc_number,
            self.account_journal.privat24_id,
            self.account_journal.privat24_token,
        )
        api.get_statement(start_date, end_date)

        self.mock_requests_get.assert_called_once_with(
            "https://acp.privatbank.ua/api/proxy/transactions",
            params={
                "period": "date",
                "acc": self.bank_account.acc_number,
                "startDate": start_date.strftime("%d-%m-%Y"),
                "endDate": end_date.strftime("%d-%m-%Y"),
            },
            headers={
                "User-Agent": "python",
                "id": self.account_journal.privat24_id,
                "Token": self.account_journal.privat24_token,
                "Content-Type": "application/json;charset=utf8",
                "Accept": "application/json",
            },
            timeout=30,
        )

        data = api.get_statement(start_date, end_date)
        for entry in data:
            for _, value in entry.items():
                transaction_date = datetime.strptime(
                    value["DATE_TIME_DAT_OD_TIM_P"], "%d.%m.%Y %H:%M:%S"
                ).date()
                self.assertTrue(start_date <= transaction_date <= end_date)

    def test_get_statement(self):
        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()
        self.check_get_statement(start_date, end_date)

    def test_get_statement_yesterday(self):
        start_date = datetime.now().date() - timedelta(days=1)
        end_date = datetime.now().date()
        self.check_get_statement(start_date, end_date)

    def test_get_statement_today(self):
        start_date = datetime.now().date()
        end_date = datetime.now().date()
        self.check_get_statement(start_date, end_date)

    def test_create_payment_with_all_fields(self):
        bank_acc_number = "1234 5678 9012 3456"
        client_id = "your_client_id"
        token = "your_token"
        payment_data = {
            "document_number": "12345",
            "recipient_nceo": "recipient_nceo_value",
            "payment_naming": "payment_naming_value",
            "recipient_ifi": "recipient_ifi_value",
            "payment_amount": 100.00,
            "payment_destination": "payment_destination_value",
            "recipient_account": "recipient_account_value",
            "recipient_card": "recipient_card_value",
            "document_type": "document_type_value",
            "payment_date": "payment_date_value",
            "payment_accept_date": "payment_accept_date_value",
            "payment_cb_ref": "payment_cb_ref_value",
            "copy_from_ref": "copy_from_ref_value",
            "attach": "attach_value",
        }

        # Create an instance of Privat24AutoclientApi
        privat24_api = Privat24AutoclientApi(bank_acc_number, client_id, token)
        with patch.object(privat24_api, "request_url") as mock_request_url:
            mock_request_url.return_value = {
                "status": "success",
                "message": "Payment created successfully",
            }
            result = privat24_api.create_payment(**payment_data)
            self.assertTrue(isinstance(result, dict))
            self.assertIn("status", result)
            self.assertEqual(result["status"], "success")

    def test_create_payment_with_required_fields(self):
        bank_acc_number = "1234 5678 9012 3456"
        client_id = "your_client_id"
        token = "your_token"

        payment_data = {
            "document_number": "12345",
            "recipient_nceo": "recipient_nceo_value",
            "payment_naming": "payment_naming_value",
            "recipient_ifi": "recipient_ifi_value",
            "payment_amount": 100.00,
            "payment_destination": "payment_destination_value",
        }

        privat24_api = Privat24AutoclientApi(bank_acc_number, client_id, token)

        PAYMENT_REQUIDED_FIELDS = [
            "document_number",
            "recipient_nceo",
            "payment_naming",
            "recipient_ifi",
            "payment_amount",
            "payment_destination",
        ]
        for req_field in PAYMENT_REQUIDED_FIELDS:
            temp_payment_data = payment_data.copy()
            temp_payment_data.pop(req_field)

            with self.assertRaises(Exception) as context:
                privat24_api.create_payment(**temp_payment_data)

        self.assertEqual(
            str(context.exception),
            '"{}" parameter is required!'.format(req_field)
        )

    def test_get_rest(self):
        start_date = datetime.now().date() - timedelta(days=7)
        end_date = datetime.now().date()
        self.check_get_rest(start_date, end_date)

    def test_get_rest_yesterday(self):
        start_date = datetime.now().date() - timedelta(days=1)
        end_date = datetime.now().date()
        self.check_get_rest(start_date, end_date)

    def test_get_rest_today(self):
        start_date = datetime.now().date()
        end_date = datetime.now().date()
        self.check_get_rest(start_date, end_date)

    def check_get_rest(self, start_date, end_date):
        self.mock_requests_get.return_value.status_code = 200

        mock_value_rest = {"balanceResponse": {"balance": 1000}}

        self.mock_requests_get.return_value.json.return_value = mock_value_rest

        api = Privat24AutoclientApi(
            self.bank_account.acc_number,
            self.account_journal.privat24_id,
            self.account_journal.privat24_token,
        )

        # Call the tested function
        api.get_rest(start_date, end_date)

        # Verify that the request was executed with the correct parameters
        self.mock_requests_get.assert_called_once_with(
            "https://acp.privatbank.ua/api/proxy/rest",
            params={
                "period": "date",
                "acc": self.bank_account.acc_number,
                "startDate": start_date.strftime("%d-%m-%Y"),
                "endDate": end_date.strftime("%d-%m-%Y"),
            },
            headers={
                "User-Agent": "python",
                "id": self.account_journal.privat24_id,
                "Token": self.account_journal.privat24_token,
                "Content-Type": "application/json;charset=utf8",
                "Accept": "application/json",
            },
            timeout=30,
        )

        # Verify that the data was received and processed correctly
        data = api.get_rest(start_date, end_date)
        self.assertEqual(data, mock_value_rest["balanceResponse"])
