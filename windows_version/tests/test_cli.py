"""El CLI debe aceptar exactamente las opciones documentadas en el README y el manual de usuario."""

import re
import shlex
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ladm_admin.cli import build_parser  # noqa: E402

COMMANDS = [
    "listar",
    "herramientas",
    "validar xtf --perfil SINIC --modeldir M --modelos A;B --todos-accesibles",
    "crear --conexion local --perfil SINIC --esquemas cun1,cun2 --si-existe recrear",
    "importar xtf --conexion local --perfil SINIC --esquema-unico sinic --si-hay-datos reemplazar "
    "--sin-validacion --solo-analizar",
    "exportar --conexion local --perfil SINIC --salida out --todos",
    "exportar --salida out --esquemas cun1,cun2",
    "exportar --salida out --esquema-unico sinic",
]


@pytest.mark.parametrize("line", COMMANDS)
def test_documented_commands_parse(line):
    build_parser().parse_args(shlex.split(line, posix=False))


def test_options_are_ascii():
    """Las opciones del CLI no deben llevar tildes (se escriben en consola)."""
    for action in build_parser()._subparsers._group_actions[0].choices.values():
        for opt in action._actions:
            for name in opt.option_strings:
                assert name.isascii(), name


def test_docs_only_use_existing_options():
    parser = build_parser()
    known = {name for sub in parser._subparsers._group_actions[0].choices.values()
             for a in sub._actions for name in a.option_strings}
    for doc in (ROOT / "README.md", ROOT.parent / "docs" / "manual_usuario.md"):
        used = set(re.findall(r"(?<![\w-])--[A-Za-z][A-Za-z-]+", doc.read_text(encoding="utf-8")))
        ili_flags = {u for u in used if u not in known}
        # Lo que no es opcion del CLI debe ser una opcion de ili2pg/ilivalidator mencionada en el texto
        assert ili_flags <= {"--schemaimport", "--import", "--replace", "--export", "--models", "--dbpwd",
                             "--dbparams", "--allObjectsAccessible", "--xtflog", "--dataset", "--version"}, (doc.name, ili_flags)
