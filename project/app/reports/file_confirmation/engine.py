"""
File-confirmation report engine.

Ported from the legacy file_confirmation.py main flow (lines 390-620).
The business logic is preserved as-is; external dependencies (subprocess isql,
hard-coded dbconnstr, file_send, excel_extract_path) are replaced by
the project's existing services (ISQLDatabase, EmailService, settings paths).
"""

import datetime
import json
import os
import logging
from typing import Any, Dict, List, Optional

import yaml

from app.core.config import settings
from app.core.logging import LogManager
from app.reports.file_confirmation.formatter import (
    format_cpty_file,
    format_fund_file,
    format_summary_excel,
)
from app.reports.file_confirmation.utils import build_region_filter, get_rpt_date
from app.schemas.report_models import FileConfirmationInput
from app.services.sql_template_service import sql_templates

logger = logging.getLogger(__name__)

# Path mappings (legacy excel_extract_path / base_dir)
_CONFIG_DIR = settings.BASE_DIR.parent / "configs" / "python_config" / "file_confirmation"
_RUNPATH = str(settings.BASE_DIR.parent / "data" / "sql" / "file_confirmation")
_BASE_DIR = str(settings.BASE_DIR.parent)


class FileConfirmationEngine:
    """Engine that reproduces the full legacy file_confirmation() logic."""

    def __init__(self, db_service, config_dir: str = None, runpath: str = None):
        self.db_service = db_service
        self.config_dir = config_dir or str(_CONFIG_DIR)
        self.runpath = runpath or _RUNPATH

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate(self, cmd: FileConfirmationInput, log_manager: LogManager) -> Dict[str, Any]:
        """Run the full file-confirmation pipeline.

        Returns a dict with keys: success, output_paths, html_body,
        record_count, error, log_html.
        """
        try:
            return self._run(cmd, log_manager)
        except Exception as e:
            logger.error("FileConfirmationEngine error: %s", e, exc_info=True)
            log_manager.fastapi_log("Error - %s" % e)
            return {
                "success": False,
                "error": str(e),
                "output_paths": [],
                "html_body": "",
                "record_count": 0,
                "log_html": log_manager.gen_fastapi_log(),
            }

    # ------------------------------------------------------------------
    # Internal – mirrors legacy main flow
    # ------------------------------------------------------------------
    def _run(self, cmd: FileConfirmationInput, log_manager: LogManager) -> Dict[str, Any]:
        runpath = self.runpath

        # --- (a) Date handling (legacy lines 390-411) ---
        sDate = datetime.date.today()
        t = datetime.datetime.now()

        if cmd.trade_date != "19000101":
            td = cmd.trade_date
            sDate = datetime.date(int(td[0:4]), int(td[4:6]), int(td[6:8]))
            log_manager.fastapi_log("Override Report date = " + str(sDate))

        sDateStart = get_rpt_date(True, 0, sDate)
        sDate_str = sDate.strftime("%Y%m%d")

        # --- (b) Region filter ---
        strRegion, mkt = build_region_filter(t.hour, cmd.trade_date)

        log_manager.fastapi_log(
            "Start date:%s; Report/Today date for %s region:%s" % (sDateStart, mkt, sDate_str)
        )
        log_manager.fastapi_log("Current time:%s" % t)

        sDate_str = sDateStart  # legacy: sDate = sDateStart

        # --- (c) Config paths ---
        conffile = os.path.join(self.config_dir, "config.json")
        conffilegrp = os.path.join(self.config_dir, "configGrp.json")

        isqlout = os.path.join(runpath, "ExcelExtract_" + sDate_str + ".csv")
        exclfile = os.path.join(runpath, "ExcelExtract_excl_" + sDate_str + ".csv")
        exclflg = 1
        cptyCol = "COUNTERPARTY_CODE"
        cptyColIdx = 20
        allocCol = "CL_TRADE_SET_ID"
        allocColIdx = 33

        cpty: List[str] = []
        grpFlg = 0
        allCpty: dict = {}
        allGrpCpty: dict = {}

        # --- (d) Load YAML configs ---
        if not os.path.isfile(conffilegrp):
            log_manager.fastapi_log("Error - No Group Configuration: " + conffilegrp)
            grpFlg = 1
        else:
            with open(conffilegrp, "r") as f:
                allGrpCpty = yaml.safe_load(f) or {}

        if not os.path.isfile(conffile):
            log_manager.fastapi_log("Error - No Client Configuration: " + conffile)
            if grpFlg == 1:
                return self._result_from_log(log_manager)
        else:
            with open(conffile, "r") as f:
                allCpty = yaml.safe_load(f) or {}

        # --- (e) Filter by cpty ---
        if cmd.cpty != "all":
            log_manager.fastapi_log(
                "Override client list; Ignore excl file. Run for client with Fid Code %s" % cmd.cpty
            )
            del_cpty = []
            del_grpcpty = []
            for k, i in allCpty.items():
                if cmd.cpty in i["cptyCode"]:
                    for j in i["cptyCode"]:
                        cpty.append(j)
                else:
                    del_cpty.append(k)
            for k in del_cpty:
                del allCpty[k]

            for k, i in allGrpCpty.items():
                if cmd.cpty in i["cptyCode"]:
                    for j in i["cptyCode"]:
                        if j not in cpty:
                            cpty.append(j)
                else:
                    del_grpcpty.append(k)
            for k in del_grpcpty:
                del allGrpCpty[k]
            exclflg = 0
        else:
            for i in allCpty.values():
                for j in i["cptyCode"]:
                    cpty.append(j)
            for i in allGrpCpty.values():
                for j in i["cptyCode"]:
                    if j not in cpty:
                        cpty.append(j)

        strCpty = "'" + "','".join(cpty) + "'"
        log_manager.fastapi_log("Report for: " + strCpty + "\n")

        if len(allCpty) == 0 and len(allGrpCpty) == 0:
            log_manager.fastapi_log("Error - Cannot Find this CounterParty Code!")
            return self._result_from_log(log_manager)

        # --- (f) SQL execution via db_service ---
        try:
            # Start with all raw input fields so any {param} in the template
            # can be replaced (e.g. {trade_date}, {env}, {versioning}, …).
            sql_params = {k: str(v) for k, v in cmd.model_dump().items()}
            # Override / add computed values used by the legacy template.
            sql_params.update({
                "date": sDate_str,
                "startdate": sDateStart,
                "cpty": strCpty,
                "region": strRegion,
                "ver": cmd.versioning,
            })
            query = sql_templates.get_query(
                "file_confirmation/ExcelExtract",
                params=sql_params,
            )
            log_manager.fastapi_log(query, show_in_web=1)

            raw_output = self.db_service.sybase.execute_raw_query(query)
            log_manager.fastapi_log("Completed SQL.")
        except Exception as e:
            log_manager.fastapi_log("Error - SQL execution failed: %s" % e)
            return self._result_from_log(log_manager)

        # --- (g) Parse raw isql output (legacy lines 504-519) ---
        if not raw_output or not raw_output.strip():
            log_manager.fastapi_log("Error - No SQL result")
            return self._result_from_log(log_manager)

        raw_lines = raw_output.split("\n")
        lines_raw = [l for l in raw_lines if l.strip()]
        # Remove informational lines produced by isql
        lines_raw = [
            l
            for l in lines_raw
            if not l.strip().lower().startswith("return status")
            and not l.strip().lower().endswith("rows affected)")
        ]

        logger.debug("isql output: %d non-empty lines, first 5: %s",
                      len(lines_raw), [l[:120] for l in lines_raw[:5]])

        # Detect the separator row: after removing commas and whitespace, the
        # remaining characters should all be dashes (e.g. " ,----,----,").
        sep_idx = None
        for idx, l in enumerate(lines_raw):
            stripped = l.replace(",", "").replace(" ", "").replace("\t", "")
            if stripped and all(c == "-" for c in stripped):
                sep_idx = idx
                break

        if sep_idx is not None and sep_idx >= 1:
            # Header is the line right before the separator; data starts after.
            lines_raw = [lines_raw[sep_idx - 1]] + lines_raw[sep_idx + 1:]
        else:
            # No separator found — fall back to legacy behaviour where
            # lines_raw[0]=header, lines_raw[1]=separator (maybe), rest=data.
            logger.warning("No isql separator detected; falling back to positional parsing")
            if len(lines_raw) > 1:
                del lines_raw[1]

        if len(lines_raw) < 2:
            log_manager.fastapi_log("Error - No data rows in SQL result")
            return self._result_from_log(log_manager)

        # Split by comma, strip leading/trailing empty fields (-o file format)
        lines = [(i.split(","))[1:-1] for i in lines_raw]
        for i in lines:
            i[:] = [x.strip() for x in i]

        # Determine expected column count from header and drop short rows
        expected_cols = len(lines[0])
        lines = [lines[0]] + [i for i in lines[1:] if len(i) == expected_cols]

        if len(lines) < 1:
            log_manager.fastapi_log("Error - No valid rows after parsing")
            return self._result_from_log(log_manager)

        cptyColIdx = lines[0].index(cptyCol) if cptyCol in lines[0] else cptyColIdx
        allocColIdx = lines[0].index(allocCol) if allocCol in lines[0] else allocColIdx

        # --- (h) Remove alloc already sent ---
        allocid: list = []
        if os.path.isfile(exclfile) and exclflg == 1:
            with open(exclfile, "rt") as f:
                for i in f:
                    allocid = i.split(",")
        lines = [lines[0]] + [
            i for i in lines[1:] if len(i) > allocColIdx and i[allocColIdx] not in allocid
        ]
        log_manager.fastapi_log("Excl. Alloc: " + str(len(allocid)))

        # --- (i) Per-counterparty formatting ---
        output: list = []

        for i in allCpty.values():
            if i["outPath"] == "":
                i["outPath"] = runpath
            list_trade = list(
                filter(lambda x: x[cptyColIdx] in i["cptyCode"] or x[cptyColIdx] == cptyCol, lines)
            )

            if "fileSplit" not in i.keys() or i["fileSplit"]["fileSplitFlg"] is False:
                a_filepath, b = format_cpty_file(list_trade, i, sDate_str, runpath, log_manager)
                if len(a_filepath) > 0:
                    a_filepath = [a_filepath]
            else:
                a_filepath, b = format_fund_file(
                    list_trade, i, cptyColIdx, False, sDate_str, runpath, log_manager
                )

            output.append([i["cptyName"], len(list_trade) - 1, a_filepath, b])

        # --- (j) Group processing ---
        if grpFlg == 0:
            for k, i in allGrpCpty.items():
                if i["outPath"] == "":
                    i["outPath"] = runpath
                list_trade = list(
                    filter(
                        lambda x: x[cptyColIdx] in i["cptyCode"] or x[cptyColIdx] == cptyCol, lines
                    )
                )
                a_filepath, b = format_fund_file(
                    list_trade, i, cptyColIdx, True, sDate_str, runpath, log_manager
                )
                if k in allCpty.keys():
                    log_manager.fastapi_log(k)
                    cIdx = list(zip(*output))[0].index(allCpty[k]["cptyName"])
                    cpty_result = output[cIdx]
                    if isinstance(a_filepath, list) and len(a_filepath) > 0:
                        cpty_result[2] += a_filepath
                    if isinstance(b, set) and len(b) > 0:
                        for x in b:
                            if x not in cpty_result[3]:
                                cpty_result[3].add(x)
                else:
                    output.append([i["cptyName"], len(list_trade) - 1, a_filepath, b])

        output.sort(key=lambda x: x[0])

        # --- (k) HTML summary table ---
        strBody = ""
        strMsg = ""

        strFiles: List[str] = []
        for x in filter(lambda x: isinstance(x[2], list) and x[2] != "", output):
            strFiles = strFiles + x[2]

        for x in filter(lambda x: isinstance(x[3], set) and len(x[3]) > 0, output):
            strMsg = "%s<b>%s:</b> %s <br>\n" % (strMsg, x[0], ", ".join(x[3]))
        for i in output:
            strBody += '<tr><td style="border:1px solid black;"> %s </td>' % i[0]
            strBody += (
                '<td style="border:1px solid black; padding-left: 5px; padding-right: 5px;"> %d  </td>'
                % i[1]
            )
            strBody += '<td style="border:1px solid black;"> %s </td>' % (
                i[2].split("\\")[-1]
                if isinstance(i[2], str)
                else ", ".join([x.split("\\")[-1] for x in i[2]])
                if isinstance(i[2], list)
                else ""
            )
            strBody += "</tr>\n"

        strBody = (
            strMsg
            + "<br>"
            + '<table style="border:1px solid black;border-collapse:collapse;">\n'
            + strBody
            + "</table>"
        )

        # --- Cleanup temp files ---
        isqlfile = os.path.join(runpath, "ExcelExtract.sql")
        if os.path.isfile(isqlfile):
            os.remove(isqlfile)
        if os.path.isfile(isqlout):
            os.remove(isqlout)

        # --- Update exclusion file ---
        data_lines = lines[1:]  # remove header
        if data_lines:
            with open(exclfile, "a") as f:
                f.write("," + ",".join([i[allocColIdx] for i in data_lines]))
        if os.path.isfile(exclfile) and t.hour >= 18:
            os.remove(exclfile)

        return {
            "success": True,
            "output_paths": strFiles,
            "html_body": strBody,
            "record_count": len(lines) - 1,
            "log_html": log_manager.gen_fastapi_log(),
            "error": None,
        }

    # ------------------------------------------------------------------
    @staticmethod
    def _result_from_log(log_manager: LogManager) -> Dict[str, Any]:
        return {
            "success": False,
            "output_paths": [],
            "html_body": "",
            "record_count": 0,
            "log_html": log_manager.gen_fastapi_log(),
            "error": "See log for details",
        }
