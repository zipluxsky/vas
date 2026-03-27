"""Ensure file_confirmation cleanup does not remove the ExcelExtract template filename."""

def test_fc_runtime_sql_basename_not_collide_with_template_sql():
    from app.reports.file_confirmation.engine import FC_RUNTIME_SQL_BASENAME

    assert FC_RUNTIME_SQL_BASENAME == "ExcelExtract_generated.sql"
    assert FC_RUNTIME_SQL_BASENAME != "ExcelExtract.sql"
