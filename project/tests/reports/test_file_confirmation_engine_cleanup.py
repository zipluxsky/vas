"""Ensure file_confirmation cleanup does not remove the ExcelExtract template filename."""

import os


def test_fc_runtime_sql_basename_not_collide_with_template_sql():
    from app.reports.file_confirmation.engine import FC_RUNTIME_SQL_BASENAME

    assert FC_RUNTIME_SQL_BASENAME == "ExcelExtract_generated.sql"
    assert FC_RUNTIME_SQL_BASENAME != "ExcelExtract.sql"


def test_runtime_sql_full_path_distinct_from_template_in_runpath():
    """Cleanup removes only the generated file, not ``ExcelExtract.sql`` (template)."""
    from app.reports.file_confirmation.engine import FC_RUNTIME_SQL_BASENAME

    runpath = "/app/data/sql/file_confirmation"
    runtime_cleanup_target = os.path.join(runpath, FC_RUNTIME_SQL_BASENAME)
    template_file = os.path.join(runpath, "ExcelExtract.sql")
    assert runtime_cleanup_target != template_file


def test_cleanup_removes_only_generated_sql_leaves_template(tmp_path):
    """Regression: same as engine cleanup — template must survive for a second run."""
    from app.reports.file_confirmation.engine import FC_RUNTIME_SQL_BASENAME

    template = tmp_path / "ExcelExtract.sql"
    template.write_text("-- template", encoding="utf-8")
    generated = tmp_path / FC_RUNTIME_SQL_BASENAME
    generated.write_text("-- runtime", encoding="utf-8")

    isqlfile = os.path.join(str(tmp_path), FC_RUNTIME_SQL_BASENAME)
    if os.path.isfile(isqlfile):
        os.remove(isqlfile)

    assert template.is_file()
    assert not generated.is_file()
