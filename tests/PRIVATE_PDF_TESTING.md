# Private PDF regression testing

Real financial statements are useful for exercising PDF geometry, embedded text,
and OCR behavior that synthetic tests cannot reproduce. They also contain highly
sensitive information. Keep every private fixture under
`tests/private-fixtures/`; that entire directory is intentionally ignored by Git.

Do not put an original statement in this repository, even in the ignored
directory. Create a permanently redacted copy outside the repository first, then
copy only that sanitized file into `tests/private-fixtures/`.

## Initial fixture set

Five diverse statements provide more value than a large collection of similar
files:

1. `cibc-credit-digital.pdf`: a multi-page, text-based credit-card statement with
   a payment, purchase, refund, and wrapped merchant description.
2. `cibc-debit-digital.pdf`: a text-based chequing statement with separate debit
   and credit columns, deposits/transfers, and repeated transaction dates.
3. `atb-chequing-scan.pdf`: an image-only statement that requires OCR and includes
   page headers, footers, and continuation markers.
4. `generic-bank-digital.pdf`: one text-based RBC, TD, BMO, or Scotiabank statement
   that exercises the generic parser.
5. `edge-cross-year.pdf`: a December-to-January statement containing at least one
   repeated same-day amount, a continued page, or another previously troublesome
   layout feature.

Use fabricated replacements such as `TEST PERSON`, `0000`, and
`REDACTED MERCHANT A`. Preserve the document's layout, fonts, columns, pagination,
amount signs, and representative transaction types.

## Redaction requirements

A black rectangle drawn over text is not sufficient; the covered text can remain
selectable or recoverable. Use a PDF redaction tool that removes the underlying
content, apply/flatten the redactions, and save a new file. Remove or replace:

- names, addresses, email addresses, and telephone numbers;
- account, card, statement, customer, and reference numbers;
- barcodes, QR codes, signatures, and institution-specific login information;
- identifying merchant notes, payroll sources, or transfer recipients; and
- author/title metadata, attachments, comments, and other embedded content.

After redaction, reopen the saved copy, select/copy all text, inspect the document
properties, and render every page to confirm that no original value survives.
For scanned documents, run OCR against the redacted copy and inspect that output
too. Never paste a fixture or extracted statement text into chat, an issue, or CI
logs.

The extractor logs only method/page/count metadata. Keep it that way: fixture
contents, names, transaction descriptions, dates, and amounts must never be added
to test output or retained in uploaded console logs.

## Expected-result sidecar

Give each PDF an adjacent file with the same stem and `.expected.json` suffix:

```text
tests/private-fixtures/cibc-credit-digital.pdf
tests/private-fixtures/cibc-credit-digital.expected.json
```

Use this versioned shape:

```json
{
  "schema_version": 1,
  "pdf": "cibc-credit-digital.pdf",
  "document": {
    "institution": "CIBC",
    "account_type": "credit_card",
    "requires_ocr": false,
    "statement_start": "2026-07-16",
    "statement_end": "2026-08-15"
  },
  "transactions": [
    {
      "date": "2026-07-20",
      "description_contains": "REDACTED MERCHANT A",
      "amount": 34.21,
      "account_type": "credit_card",
      "category": "Retail and Grocery",
      "is_internal_transfer": false
    }
  ],
  "allowed_extra_transactions": 0
}
```

Required transaction fields are `date`, `description_contains`, `amount`, and
`account_type`. Record `amount` with the exact sign emitted by the parser. The
`category` and `is_internal_transfer` fields are optional; include them only when
the fixture is intended to lock those deterministic rules. Sidecars must contain
only sanitized values and remain local with their PDFs.

## Running without an LLM

PDF extraction and the layout/text parsers are deterministic. The existing
parser suite can be run with Claude explicitly disabled:

```powershell
$env:ANTHROPIC_API_KEY = ""
python -m unittest tests.test_pdf_layout_parser -v
Remove-Item Env:ANTHROPIC_API_KEY -ErrorAction SilentlyContinue
```

A private-fixture harness should call `extract_pdf_document()` followed by
`parse_transactions_from_pdf_document()` and compare the result with the sidecar.
It must not call an HTTP import endpoint, MongoDB, or Plaid. In tests that import
`backend.server`, set inert Mongo/Plaid environment values before the import and
patch both the Anthropic client factory and categorization coroutine to raise an
assertion if invoked. This makes an accidental model request fail the test rather
than send statement data externally.

No opt-in fixture test is committed yet because no redacted fixtures exist. Add
one after the first PDF/sidecar pair is prepared; it should skip cleanly unless a
separate opt-in environment variable is set.

## Before every commit

Confirm that Git ignores the fixture directory and that nothing from it is
tracked:

```powershell
git check-ignore -v tests/private-fixtures/example.pdf
git ls-files tests/private-fixtures
git status --short --ignored
```

The `git ls-files` command must produce no fixture paths. Git ignore rules do not
protect a file that was already committed, so always perform this check before
pushing.
