# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

PyBLNET is a Python client for the BL-NET gateway by Technische Alternative, which sits in front of a UVR1611 heating controller. It reads analog/digital values and can set switches to ON/OFF/AUTO. Managed with uv: `uv_build` backend, dev tools in the `dev` dependency group, and `uv.lock` committed. The only runtime dependency is `requests`. CI tests Python 3.11–3.15 with `uv sync --locked`, so run `uv lock` after changing dependencies. Pushing a `*.*.*` tag triggers the release workflow: `uv build`, then a GitHub release with the wheel and sdist attached. This fork is not published to PyPI (the `PyBLNET` package there belongs to upstream); users install from GitHub. When releasing, bump the version in both `pyproject.toml` and `VERSION` in `pyblnet/__init__.py`.

## Commands

```bash
uv sync                                # create .venv with package + dev group
uv run pytest tests                    # full suite
uv run pytest tests/test_web.py::BLNETWebTest::test_blnet_fetch   # single test
uv run coverage run --source=pyblnet -m pytest tests && uv run coverage report   # what CI runs
uv run --isolated --python 3.11 pytest tests   # oldest supported Python, leaves .venv alone
uv run ruff check pyblnet tests        # ruff defaults + pyupgrade (UP); UP is clean, other default rules still report issues; CI does not run ruff
uv build                               # sdist + wheel into dist/
```

## Architecture

Two independent transports, plus a facade over both:

- **`BLNETWeb`** (`blnet_web.py`) scrapes the device's German-language HTTP interface with `requests` and the standard library's `html.parser` (`_element_texts()` keeps entities like `&nbsp;` as written and turns `<br>` into newlines, which the value regexes rely on). Login POSTs to `/main.html` and stores the `TAID` cookie. `logged_in()` works by checking whether a restricted page sends back `Set-Cookie`. Use it as a context manager: `__enter__`/`__exit__` call `log_in`/`log_out`. Logging out matters because the device blocks all web access for about 150s after a session that wasn't logged out. The constructor calls `blnet_test()` and raises `ValueError` if no BL-NET answers. Switch values use the device's German strings `"EIN"`, `"AUS"`, `"AUTO"`. Only this transport can set switches, read manual/auto mode, and select a CAN node.
- **`BLNETDirect`** (`blnet_conn.py`) speaks TA's binary bootloader protocol over TCP (port 40000). It is a Python port of berwinter's PHP `blnet-connection.inc.php`. On construction it queries the device mode: `CAN_MODE`, `DL_MODE` or `DL2_MODE`. That mode decides frame counts, dataset sizes and how `_split_latest`/`_split_datasets` slice the response. The README still calls this transport buggy and discourages it. The `timeout` is set on each socket it opens, not process-wide. `get_latest()` lists frames that never arrived in `info["timeout"]` and raises `ConnectionError` if no frame arrived. Read paths (`get_latest`, `get_count`, `_get_data`, `_check_mode`) are wrapped in `_reset_on_error`: on any error the socket is closed and the read state is reset, so the next call reconnects; empty or malformed replies are raised as `ConnectionError`. Errors reaching callers are therefore `OSError` subclasses (`ConnectionError` or `TimeoutError`). A one-byte `0xAB` reply means the device has no new data yet (real devices say so for up to ~5 s after a read); `get_latest()` then waits `NO_DATA_WAIT` seconds before the next try. `_query_latest()` derives the reply length from its first byte and reads the reply completely, because BL-NETs sometimes send the first byte in a TCP segment of its own; reading only part of it shifted all following replies by one byte, and the weak sum checksum let some of those shifted datasets through as garbage values. After a reply with a bad checksum `get_latest()` reconnects so stray bytes can't reach the next reply.
- **`BLNETParser`** (`blnet_parser.py`) decodes one binary dataset (55 bytes, or 61 with a timestamp) into `{'analog','digital','speed','energy','power'}` dicts keyed by 1-based ID. Inactive values are `None`: unused inputs (type bits `000`), temperature inputs without sensor (raw `0x2FFF` = 409.5 °C, `TEMP_NO_SENSOR`), inactive speed controls and inactive heat meters. `analog_types` maps each input to `"temperature"`, `"volume_flow"`, `"radiation"`, `"digital"` or `None` (`ANALOG_TYPES`, units in `ANALOG_UNITS`). It is used only by `BLNETDirect`.
- **`BLNET`** (`blnet.py`) is the high-level facade, with each transport switched on by `use_web` (default on) and `use_ta` (default off). `fetch()` returns a dict with all five domains. The web transport supplies analog/digital entries as dicts (`id`, `name`, `value`, `mode`). Direct data then overwrites `value` on those entries. If web is disabled ("DL-only" mode), `fetch()` creates entries from direct data alone and skips `None` values; analog entries carry `type` and `unit_of_measurement`, digital ones only `value`. Web analog entries get `type` derived from their unit (`WEB_UNIT_TYPES`). `speed`/`energy`/`power` come only from direct, with `unit_of_measurement` `None` (speed is a level 0-30), `"kWh"` and `"kW"`. `get_value()` matches on `name` (when given) or on the id key, so it works for both entry shapes.

## Device documentation

- Official BL-NET manual (German, v2.19): https://www.ta.co.at/download/datei/416. Its "Zugriff per Browser" chapter describes the web interface that `BLNETWeb` scrapes. Facts from it that the code relies on:
  - Only one user can be logged in at a time.
  - A session ends after 2.5 minutes without traffic. If a session isn't logged out, nobody can log in for those 2.5 minutes.
  - There are three access levels: Experte, Anwender and "nur ansehen". The login form field `blu=1` selects Experte.
  - From the factory no password is set. Code passes `password=None` to skip login.
  - The default ports are HTTP 80 and TA port 40000.
  - For CAN data logging, one UVR1611 must be node 1.
- The binary protocol used by `BLNETDirect` isn't in that manual. TA's spec "Schnittstelle Winsol <> Bootloader" (2006) describes it. The haus-terra link in the README is dead (404); an archived copy is at http://web.archive.org/web/20160122124754/http://www.haus-terra.at:80/heizung/download/Schnittstelle/Schnittstelle_PC_Bootloader.pdf. The spec covers:
  - The DL modes only: 1DL `0xA8` and 2DL `0xD1`.
  - The commands `0x81` (mode), `0x82` (firmware), `0xAA` (header), `0xAB` (latest data), `0xAC` (read logged block), `0xAD` (end read) and `0xAF` (reset logged data).
  - The dataset layouts.
- Not in the spec: CAN mode (`0xDC`), the `0xBA` "wait" response, and the frame-number byte sent after `0xAB`. These come from berwinter's reverse-engineered PHP code. In DL mode the spec's `0xAB` request is one byte, but the code sends two, and a real device accepts that.

## Tests

- `tests/test_parser.py` checks `BLNETParser` against raw byte fixtures.
- `tests/test_web.py` runs `BLNETWeb`/`BLNET` against a local mock HTTP server (`tests/test_structure/blnet_mock_server.py`, started in a thread by `server_control.py`). The mock serves the saved device pages in `tests/test_structure/*.htm` and emulates login cookies, password (`0123`), node switching and a "blocked" state. Expected parse results live in `tests/web_raw/web_state.py`.
- `tests/test_direct.py` runs `BLNET` in DL-only mode against a fake TCP BL-NET (`tests/test_structure/blnet_direct_mock_server.py`). The fake replays mode, header and latest-data responses recorded from a real device in DL mode. Only `GET_MODE`, `GET_HEADER`, `GET_LATEST` and `END_READ` are emulated; CAN/DL2 modes and reading stored data (`_get_data`) are untested.
