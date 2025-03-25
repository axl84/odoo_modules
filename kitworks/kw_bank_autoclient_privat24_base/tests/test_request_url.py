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


class TestAutoclientPrivatRequestUrl(common.TransactionCase):

    @patch("requests.get")
    def test_request_url_success(self, mock_requests_get):
        mock_requests_get.return_value.status_code = 200
        statement_exempl = []
        for i in range(10):
            date_today = datetime.now().date() - timedelta(days=i)
            for _ in range(2):
                random_days_ago = random.randint(0, 1)
                trans_date = date_today - timedelta(days=random_days_ago)

                statement_id = "HS43O0311L01YW"
                statement = {
                    "StatementsResponse": {
                        "ResponceRef": "",
                        "statements": [
                            {
                                statement_id: {
                                    "AUT_MY_CRF": "3266712365",
                                    "AUT_MY_MFO": "305299",
                                    "AUT_MY_ACC": (
                                        f"{'UA' + str(random.randint(10, 99))}"
                                    ),
                                    "AUT_MY_NAM": "Іванов Ю.М. ФОП",
                                    "AUT_MY_MFO_NAME": 'АТ КБ "ПРИВАТБАНК"',
                                    "AUT_CNTR_CRF": random.randint(10, 99),
                                    "AUT_CNTR_MFO": "351005",
                                    "AUT_CNTR_ACC": (
                                        f"{'UA' + str(random.randint(10, 99))}"
                                    ),
                                    "AUT_CNTR_NAM": 'ТОВ ФК "ВЕЙ ФОР ПЕЙ"',
                                    "AUT_CNTR_MFO_NAME": 'АТ "УкрСиббанк"',
                                    "BPL_CCY": "UAH",
                                    "BPL_FL_REAL": "r",
                                    "BPL_FL_DC": "C",
                                    "BPL_PR_PR": "r",
                                    "BPL_DOC_TYP": "p",
                                    "BPL_NUM_DOC": "3B3377",
                                    "BPL_DAT_KL": (
                                        trans_date.strftime("%d.%m.%Y")
                                    ),
                                    "BPL_DAT_OD": (
                                        trans_date.strftime("%d.%m.%Y")
                                    ),
                                    "BPL_OSND": (
                                        f"Переказ коштів за "
                                        f"{date_today.strftime('%d.%m.%Y')} - "
                                        f"{trans_date.strftime('%d.%m.%Y')}"
                                    ),
                                    "BPL_SUM": (
                                        f"{random.uniform(1000, 50000):.2f}"
                                    ),
                                    "BPL_SUM_E": (
                                        f"{random.uniform(1000, 50000):.2f}"
                                    ),
                                    "BPL_REF": statement_id,
                                    "BPL_REFN": "P",
                                    "BPL_TIM_P": (
                                        f"{random.randint(0, 23):02d}"
                                        f":"
                                        f"{random.randint(0, 59):02d}"
                                    ),
                                    "DATE_TIME_DAT_OD_TIM_P": (
                                        trans_date.strftime(
                                            "%d.%m.%Y %H:%M:%S"
                                        ),
                                    ),
                                    "ID": f"{random.randint(100, 999)}",
                                    "TRANTYPE": "C",
                                    "TECHNICAL_TRANSACTION_ID": (
                                        f"{random.randint(100, 999)}_online"
                                    ),
                                }
                            }
                        ],
                    }
                }
                statement_exempl.append(statement)
        mock_requests_get.return_value.json.return_value = statement_exempl

        api = Privat24AutoclientApi(
            "example_acc",
            "example_id",
            "example_token"
            )
        result = api.request_url(
            type_request="data",
            example_param="example_value"
            )

        self.assertEqual(result, statement_exempl)

    @patch("requests.get")
    def test_request_url_failure(self, mock_requests_get):
        test_cases = [
            (
                400,
                "Invalid request format or missing one or more"
                " required headers! Error 400",
            ),
            (
                403,
                "If the account is disabled through the management interface "
                "of the Privat24 for Businesses! Error 403",
            ),
            (
                401,
                "Incorrect credentials for access (id and / or token)!"
                " Error 401",
            ),
            (500, "Internal server error! Status code 500"),
            (502, "Internal server error! Status code 502"),
            (503, "Server temporary is unavailable! Status code 503"),
        ]

        for status_code, expected_error_msg in test_cases:
            with self.subTest(status_code=status_code):
                mock_requests_get.return_value.status_code = status_code

                api = Privat24AutoclientApi(
                    "example_acc", "example_id", "example_token"
                )

                with self.assertRaises(Exception) as context:
                    api.request_url(
                        type_request="data",
                        example_param="example_value"
                    )
                self.assertEqual(str(context.exception), expected_error_msg)
