import ast
import pathlib
import re
import unittest
from collections import Counter, defaultdict
from datetime import date, datetime
from typing import Dict, List, Optional


def load_parser_namespace():
    server_path = pathlib.Path("backend/server.py")
    source = server_path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source, filename=str(server_path))

    wanted_assignments = {
        "MONTH_ABBREVIATIONS",
        "AMOUNT_TOKEN_PATTERN",
        "GENERIC_AMOUNT_PATTERN",
        "OCR_AMOUNT_PATTERN",
        "DATE_TOKEN_PATTERN",
        "GENERIC_CATEGORY_VALUES",
        "MERCHANT_SIGNATURE_NOISE_WORDS",
        "CATEGORY_MATCH_RULES",
        "DEFAULT_CATEGORIES",
    }
    wanted_functions = {
        "group_pdf_words_into_rows",
        "parse_date_string",
        "generate_source_name",
        "normalize_row_text",
        "is_amount_text",
        "parse_amount_text",
        "parse_ocr_amount_text",
        "extract_ocr_amounts_from_line",
        "extract_generic_amounts_from_line",
        "infer_atb_transaction_amount",
        "infer_generic_transaction_amount",
        "infer_account_type_from_text",
        "parse_atb_transactions_from_text",
        "parse_generic_transactions_from_text",
        "extract_compact_date",
        "extract_two_leading_dates",
        "append_text_value",
        "build_header_positions",
        "get_words_in_x_range",
        "select_rightmost_amount_candidate",
        "detect_credit_layout_columns",
        "detect_debit_layout_columns",
        "normalize_text",
        "resolve_category_name",
        "build_merchant_signature",
        "score_categories_from_text",
        "infer_category_from_context",
        "clean_category",
        "finalize_credit_layout_transaction",
        "finalize_debit_layout_transaction",
        "parse_cibc_credit_transactions_from_layout",
        "assign_debit_amounts",
        "parse_cibc_debit_transactions_from_layout",
    }

    selected_nodes = []
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id in wanted_assignments
            for target in node.targets
        ):
            selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in wanted_functions:
            selected_nodes.append(node)

    module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace = {
        "Counter": Counter,
        "defaultdict": defaultdict,
        "date": date,
        "datetime": datetime,
        "Dict": Dict,
        "List": List,
        "Optional": Optional,
        "re": re,
    }
    exec(compile(module, str(server_path), "exec"), namespace)
    return namespace


PARSER = load_parser_namespace()


def make_word(text, x0, top=0.0):
    return {"text": text, "x0": float(x0), "top": float(top)}


def make_row(*words, top=0.0):
    return {
        "top": float(top),
        "words": list(words),
        "text": " ".join(word["text"] for word in words),
    }


class PdfLayoutParserTests(unittest.TestCase):
    def test_group_pdf_words_into_rows_groups_nearby_words(self):
        rows = PARSER["group_pdf_words_into_rows"](
            [
                make_word("Trans", 50, top=10.0),
                make_word("Post", 90, top=10.8),
                make_word("Description", 150, top=25.0),
            ]
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["text"], "Trans Post")
        self.assertEqual(rows[1]["text"], "Description")

    def test_credit_layout_parser_extracts_description_category_and_amount(self):
        rows = [
            make_row(make_word("Trans", 50), make_word("Post", 95), top=10),
            make_row(
                make_word("date", 50),
                make_word("date", 95),
                make_word("Description", 140),
                make_word("Spend", 360),
                make_word("Categories", 405),
                make_word("Amount($)", 520),
                top=22,
            ),
            make_row(
                make_word("Oct", 50),
                make_word("13", 78),
                make_word("Oct", 105),
                make_word("15", 133),
                make_word("Lovisa", 150),
                make_word("Alberta", 205),
                make_word("AB", 275),
                make_word("Retail", 360),
                make_word("and", 405),
                make_word("Grocery", 435),
                make_word("29.39", 525),
                top=40,
            ),
        ]

        transactions = PARSER["parse_cibc_credit_transactions_from_layout"](
            [{"page_number": 1, "rows": rows}],
            "user-1",
            "credit.pdf",
            2024,
            "JANE DOE",
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["description"], "Lovisa Alberta AB")
        self.assertEqual(transactions[0]["category"], "Retail and Grocery")
        self.assertEqual(transactions[0]["amount"], 29.39)
        self.assertEqual(transactions[0]["date"], "2024-10-13")

    def test_debit_layout_parser_keeps_multiline_description_and_sign(self):
        rows = [
            make_row(make_word("Transaction", 100), make_word("details", 185), top=10),
            make_row(
                make_word("Date", 50),
                make_word("Description", 140),
                make_word("Withdrawals", 360),
                make_word("Deposits", 455),
                make_word("Balance", 545),
                top=24,
            ),
            make_row(
                make_word("Oct", 50),
                make_word("05", 78),
                make_word("VISA", 145),
                make_word("DEBIT", 180),
                make_word("RETAIL", 230),
                make_word("PURCHASE", 285),
                make_word("25.99", 370),
                make_word("974.01", 550),
                top=42,
            ),
            make_row(
                make_word("TIM", 145),
                make_word("HORTONS", 180),
                make_word("#1234", 255),
                top=54,
            ),
        ]

        transactions = PARSER["parse_cibc_debit_transactions_from_layout"](
            [{"page_number": 1, "rows": rows}],
            "user-1",
            "debit.pdf",
            2024,
            "SARAH JOHNSON",
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["amount"], 25.99)
        self.assertIn("TIM HORTONS #1234", transactions[0]["description"])
        self.assertEqual(transactions[0]["category"], "Restaurants")
        self.assertEqual(transactions[0]["date"], "2024-10-05")

    def test_debit_layout_parser_splits_same_day_rows_without_repeated_date(self):
        rows = [
            make_row(make_word("Transaction", 100), make_word("details", 185), top=10),
            make_row(
                make_word("Date", 50),
                make_word("Description", 140),
                make_word("Withdrawals", 360),
                make_word("Deposits", 455),
                make_word("Balance", 545),
                top=24,
            ),
            make_row(
                make_word("Dec", 50),
                make_word("1", 78),
                make_word("Opening", 145),
                make_word("balance", 205),
                make_word("$15,897.31", 545),
                top=42,
            ),
            make_row(
                make_word("Dec", 50),
                make_word("1", 78),
                make_word("E-TRANSFER", 145),
                make_word("011498144817", 225),
                make_word("4,000.00", 455),
                make_word("19,897.31", 545),
                top=56,
            ),
            make_row(
                make_word("samirkumarpatel2005", 145),
                top=68,
            ),
            make_row(
                make_word("E-TRANSFER", 145),
                make_word("011498204227", 225),
                make_word("1,000.00", 455),
                make_word("20,897.31", 545),
                top=82,
            ),
            make_row(
                make_word("RAJVI", 145),
                make_word("PATEL", 190),
                top=94,
            ),
        ]

        transactions = PARSER["parse_cibc_debit_transactions_from_layout"](
            [{"page_number": 1, "rows": rows}],
            "user-1",
            "debit.pdf",
            2025,
            "DANIEL OLAIFA",
        )

        self.assertEqual(len(transactions), 2)
        self.assertEqual(transactions[0]["date"], "2025-12-01")
        self.assertEqual(transactions[0]["amount"], -4000.0)
        self.assertIn("samirkumarpatel2005", transactions[0]["description"])
        self.assertEqual(transactions[1]["date"], "2025-12-01")
        self.assertEqual(transactions[1]["amount"], -1000.0)
        self.assertIn("RAJVI PATEL", transactions[1]["description"])

    def test_atb_ocr_text_parser_extracts_transactions(self):
        atb_text = """
        Deposit Account Statement
        Statement date March 15, 2026
        Details of your account transactions
        Date Description Money out of your account ($) Money into your account ($) Balance ($)
        Feb 26 $1,461.13 Direct Deposit Payroll Deposit ATB 1,480.13
        Feb 26 $510.00 INTERAC e-Transfer Sent-Autodep 970.13
        Feb 28 $11.30 Loan Payment 988.83
        Mar 12 $200.00 INTERAC e-Transfer Sent-Autodep 1,273.96
        Mar 12 $1,200.00 ATBMOBILE Principal Payment 73.96
        Mar 15 Closing balance $73.96
        Find an error? Give us a call.
        """

        transactions = PARSER["parse_atb_transactions_from_text"](
            atb_text,
            "user-1",
            "march-atb.pdf",
            2026,
            "JANE AGBAOHWO",
        )

        self.assertEqual(len(transactions), 5)
        self.assertEqual(transactions[0]["date"], "2026-02-26")
        self.assertEqual(transactions[0]["amount"], -1461.13)
        self.assertIn("Payroll Deposit", transactions[0]["description"])
        self.assertEqual(transactions[1]["amount"], 510.0)
        self.assertEqual(transactions[-1]["date"], "2026-03-12")
        self.assertEqual(transactions[-1]["amount"], 1200.0)

    def test_atb_ocr_text_parser_skips_footer_and_continued_markers(self):
        atb_text = """
        Deposit Account Statement
        Statement date March 15, 2026
        Details of your account transactions
        Date Description Money out of your account ($) Money into your account ($) Balance ($)
        Mar 12 Direct Deposit Payroll Deposit ATB $1,461.13 1,473.96
        Keep your credentials private. Never share your banking login details.
        these.
        Details of your account transactions (continued)
        Date Description Money out of your account ($) Money into your account ($) Balance ($)
        Mar 12 INTERAC e-Transfer Sent-Autodep $200.00 1,273.96
        Find an error? Give us a call.
        """

        transactions = PARSER["parse_atb_transactions_from_text"](
            atb_text,
            "user-1",
            "march-atb.pdf",
            2026,
            "JANE AGBAOHWO",
        )

        self.assertEqual(len(transactions), 2)
        self.assertNotIn("these", transactions[0]["description"].lower())
        self.assertNotIn("continued", transactions[0]["description"].lower())
        self.assertEqual(transactions[0]["category"], "Professional and Financial Services")

    def test_normalize_text_splits_ocr_merged_tokens(self):
        normalized = PARSER["normalize_text"]("INTERAC e-TransferReceived -Autodeposit")
        self.assertIn("e transfer received", normalized)
        self.assertIn("autodeposit", normalized)

    def test_parse_date_string_handles_cross_year_statement_period(self):
        parsed_date = PARSER["parse_date_string"]("Dec 31", 2026, "Dec 15", "Jan 15")
        self.assertEqual(parsed_date.isoformat(), "2025-12-31")

    def test_generic_parser_extracts_transactions_for_unknown_bank_format(self):
        statement_text = """
        Deposit Account Statement
        For Dec 15 to Jan 15, 2026
        Daily account activity
        Dec 17 INTERAC e-Transfer Received - Autodeposit 200.00 230.21
        Dec 17 ATBMOBILE Principal Payment 200.00 30.21
        Jan 4 INTERAC e-Transfer Sent-Autodep 20.00 8.23
        """

        transactions = PARSER["parse_generic_transactions_from_text"](
            statement_text,
            "user-1",
            "generic.pdf",
            2026,
            "JANE AGBAOHWO",
            statement_start="Dec 15",
            statement_end="Jan 15",
        )

        self.assertEqual(len(transactions), 3)
        self.assertEqual(transactions[0]["date"], "2025-12-17")
        self.assertEqual(transactions[0]["amount"], -200.0)
        self.assertEqual(transactions[1]["amount"], 200.0)
        self.assertEqual(transactions[2]["date"], "2026-01-04")


if __name__ == "__main__":
    unittest.main()
