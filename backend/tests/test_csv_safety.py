"""Text formula neutralization, escaping, and unchanged numeric error signs."""

import csv
import io

from backend.app.services.csv_export import safe_cell


def test_csv_formula_prefixes_and_escaped_text_preserve_numeric_types():
    original = [
        '=HYPERLINK("https://example.test")',
        " +SUM(1,2)",
        "-SUM(1,2)",
        "@SUM(1,2)",
        "\ttext",
        'text,"quoted"\nline',
        -3553,
        0,
        None,
    ]
    stream = io.StringIO(newline="")
    csv.writer(stream).writerow([safe_cell(value) for value in original])
    parsed = next(csv.reader(io.StringIO(stream.getvalue())))
    assert parsed[:5] == ["'" + value for value in original[:5]]
    assert parsed[5] == original[5]
    assert parsed[6:] == ["-3553", "0", ""]
