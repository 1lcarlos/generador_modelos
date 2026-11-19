"""Pruebas unitarias del nucleo (no requieren base de datos ni Java)."""

import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ladm_admin.core.database import SchemaInfo  # noqa: E402
from ladm_admin.core.events import Level  # noqa: E402
from ladm_admin.core.ili import dependency_closure, duplicate_models, parse_ili_file, suggested_models  # noqa: E402
from ladm_admin.core.ili2db import Ili2pg, ToolConfig, default_schema_options  # noqa: E402
from ladm_admin.core.database import ConnectionParams  # noqa: E402
from ladm_admin.core.naming import NamingConvention, StorageMode, code_from_path, validate_identifier  # noqa: E402
from ladm_admin.core.operations import ImportItem, ImportRequest, PlanState, evaluate_item  # noqa: E402
from ladm_admin.core.process import ToolResult, classify_line, mask_command  # noqa: E402
from ladm_admin.core.xtf import SourceFile, expand_sources, read_header, scan_content  # noqa: E402

ILI = """INTERLIS 2.3;
/* comentario con MODEL Falso = */
CONTRACTED TYPE MODEL Tipos (es) AT "http://x" VERSION "1" = END Tipos.
MODEL Base (es) AT "http://x" VERSION "2.0" =
  IMPORTS UNQUALIFIED INTERLIS, Tipos;
  TOPIC T = CLASS A = END A; END T;
END Base.
MODEL App (es) AT "http://x" VERSION "3" =
  IMPORTS Base,Tipos;
END App.
"""

XTF = """<?xml version="1.0" encoding="UTF-8"?><TRANSFER xmlns="http://www.interlis.ch/INTERLIS2.3">
<HEADERSECTION SENDER="ili2pg-5.5.1-abc" VERSION="2.3"><MODELS>
<MODEL NAME="Base" VERSION="2.0" URI="x"></MODEL><MODEL NAME="App" VERSION="3" URI="x"></MODEL>
</MODELS></HEADERSECTION>
<DATASECTION>
<App.T BID="b1"><App.T.A TID="1"><n>x</n></App.T.A><App.T.A TID="2"/><App.T.B TID="3"/></App.T>
</DATASECTION></TRANSFER>
"""


@pytest.fixture
def ili_file(tmp_path):
    p = tmp_path / "modelos.ili"
    p.write_text(ILI, encoding="utf-8")
    return p


@pytest.fixture
def xtf_file(tmp_path):
    d = tmp_path / "25279"
    d.mkdir()
    p = d / "entrega.xtf"
    p.write_text(XTF, encoding="utf-8")
    return p


def test_parse_ili(ili_file):
    models = {m.name: m for m in parse_ili_file(ili_file)}
    assert set(models) == {"Tipos", "Base", "App"}
    assert models["Tipos"].kind == "TYPE" and models["Tipos"].is_base
    assert models["Base"].imports == ["Tipos"]
    assert models["App"].version == "3"
    assert suggested_models(list(models.values())) == ["Base", "App"]
    assert dependency_closure(["App"], list(models.values())) == ["Tipos", "Base", "App"]


def test_duplicate_models(ili_file, tmp_path):
    copy = tmp_path / "otro.ili"
    copy.write_text(ILI, encoding="utf-8")
    models = parse_ili_file(ili_file) + parse_ili_file(copy)
    assert set(duplicate_models(models)) == {"Tipos", "Base", "App"}


def test_xtf_header_and_scan(xtf_file):
    info = read_header(xtf_file)
    assert info.error == ""
    assert info.model_names == ["Base", "App"]
    assert info.sender.startswith("ili2pg-5.5.1")
    info = scan_content(xtf_file)
    assert [b.bid for b in info.baskets] == ["b1"]
    assert info.class_counts["App.T.A"] == 2 and info.total_objects == 3


def test_xtf_invalid(tmp_path):
    bad = tmp_path / "malo.xtf"
    bad.write_text("<TRANSFER><HEADERSECTION>", encoding="utf-8")
    assert read_header(bad).error


def test_expand_sources_with_zip(xtf_file, tmp_path, monkeypatch):
    monkeypatch.setattr("ladm_admin.core.xtf.work_dir", lambda: tmp_path / "work")
    z = tmp_path / "25645_envio.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(xtf_file, "carpeta/25645.xtf")
        zf.writestr("leeme.txt", "x")
    found, errors = expand_sources([xtf_file.parent, z])
    assert not errors
    names = [s.display for s in found]
    assert "entrega.xtf" in names and "25645_envio.zip > 25645.xtf" in names
    zipped = next(s for s in found if s.origin)
    assert code_from_path(zipped.path, zipped.origin) == "25645"


def test_naming():
    n = NamingConvention("cun")
    assert n.schema_for_code("25279") == "cun25279"
    assert n.code_for_schema("cun25279") == "25279"
    assert code_from_path(Path("x/25279/entrega.xtf")) == "25279"
    assert code_from_path(Path("x/123456.xtf")) is None
    assert validate_identifier("cun25279") is None
    assert validate_identifier("25279") and validate_identifier("Cun-1")


def test_classify_and_mask():
    assert classify_line("Error: algo") == Level.ERROR
    assert classify_line("Warning: algo") == Level.WARNING
    assert classify_line("Info: errores 0") == Level.DEBUG
    assert "secreto" not in mask_command(["java", "--dbpwd", "secreto", "--x"])


def test_main_error_prefers_postgres_cause():
    r = ToolResult(1, errors=["Error: Object 1 at (line 3,col 0)", "Error:   ERROR: current transaction is aborted",
                              "Error:     ERROR: duplicate key value violates unique constraint"])
    assert r.main_error() == "duplicate key value violates unique constraint"


def test_ili2pg_command_has_options_and_masks_password():
    tools = ToolConfig("java", "ili2pg.jar")
    cmd = Ili2pg(tools, ConnectionParams("h", 5432, "db", "u", "S3cr3t&x"), modeldir="M").schema_import(
        "cun1", ["A", "B"], "9377", default_schema_options())
    assert cmd[cmd.index("--models") + 1] == "A;B"
    assert "--createBasketCol" in cmd and "--sqlEnableNull" not in cmd
    assert "S3cr3t&x" in cmd and "S3cr3t" not in mask_command(cmd)


def _item(xtf_file, schema="cun25279"):
    from ladm_admin.core.xtf import read_header
    item = ImportItem(source=SourceFile(xtf_file), header=read_header(xtf_file), code="25279", schema=schema)
    return item


def test_evaluate_item_states(xtf_file):
    req = ImportRequest(ConnectionParams(), ToolConfig("java", "x"), "", Path("."))
    info = SchemaInfo("cun25279", exists=True, is_ili2db=True, basket_col=True,
                      models=["Base", "App"], sender="ili2pg-5.5.1-x")
    item = _item(xtf_file)
    evaluate_item(item, req, info, set())
    assert item.state == PlanState.READY and item.dataset == "25279"

    info.datasets = ["25279"]
    item = _item(xtf_file)
    evaluate_item(item, req, info, set())
    assert item.state == PlanState.CONFLICT

    item = _item(xtf_file)
    evaluate_item(item, req, SchemaInfo("cun25279", exists=False), set())
    assert item.state == PlanState.BLOCKED and "no existe" in item.messages[0]

    item = _item(xtf_file)
    evaluate_item(item, req, SchemaInfo("cun25279", exists=True, is_ili2db=True, models=["Base"]), set())
    assert item.state == PlanState.BLOCKED and "App" in item.messages[0]

    # dos archivos al mismo destino
    claimed = set()
    a, b = _item(xtf_file), _item(xtf_file)
    info.datasets = []
    evaluate_item(a, req, info, claimed)
    evaluate_item(b, req, info, claimed)
    assert a.state == PlanState.READY and b.state == PlanState.BLOCKED


def test_evaluate_shared_mode_requires_basket(xtf_file):
    req = ImportRequest(ConnectionParams(), ToolConfig("java", "x"), "", Path("."),
                        storage_mode=StorageMode.SHARED, shared_schema="sinic")
    info = SchemaInfo("sinic", exists=True, is_ili2db=True, basket_col=False, models=["Base", "App"])
    item = _item(xtf_file, schema="sinic")
    evaluate_item(item, req, info, set())
    assert item.state == PlanState.BLOCKED

    info.basket_col = True
    info.datasets = ["25000"]   # otro municipio: no es conflicto en modo esquema unico
    item = _item(xtf_file, schema="sinic")
    evaluate_item(item, req, info, set())
    assert item.state == PlanState.READY


def test_evaluate_detects_classes_without_table(xtf_file):
    req = ImportRequest(ConnectionParams(), ToolConfig("java", "x"), "", Path("."))
    info = SchemaInfo("cun25279", exists=True, is_ili2db=True, basket_col=True, models=["Base", "App"])
    item = _item(xtf_file)
    item.header = scan_content(xtf_file)
    evaluate_item(item, req, info, set(), class_map={"App.T.A": "a"})
    assert item.state == PlanState.BLOCKED and "App.T.B" in item.messages[0]
