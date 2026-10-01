import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from xpost_dashboard import mock_page, render, runner, status_store
from xpost_dashboard.action_states import CATEGORY_LABEL, EVENT_TYPE_LABEL, STATE_CATEGORY, STATE_STYLE

_TESTDATA = Path(__file__).parent / "testdata"
_SAMPLE_STATUS = json.loads((_TESTDATA / "status_sample.json").read_text())


def _fresh_status() -> dict:
    """`_SAMPLE_STATUS`'s `generated_at` is a fixed timestamp, so it reads as
    stale by the time the suite runs; tests of the "not stale" path need a
    snapshot generated_at "now" instead."""
    return {**_SAMPLE_STATUS, "generated_at": datetime.now(timezone.utc).isoformat()}


@pytest.fixture()
def client():
    runner.app.config["TESTING"] = True
    with runner.app.test_client() as c:
        yield c


# status_store.load_status(): the three paths it must keep distinguishable


def test_load_status_returns_empty_when_nothing_has_reported(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_store, "STATUS_FILE", tmp_path / "status.json")
    result = status_store.load_status()
    assert result == status_store.EMPTY_STATUS
    assert "status_error" not in result


def test_load_status_flags_invalid_json_as_an_error_not_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text("{not valid json")
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    result = status_store.load_status()
    assert result["actions"] == []
    assert result["instance"] is None
    assert "status_error" in result
    assert "valid JSON" in result["status_error"]


def test_load_status_flags_a_non_object_json_document_as_an_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text("[1, 2, 3]")
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    result = status_store.load_status()
    assert "status_error" in result
    assert "not a JSON object" in result["status_error"]


def test_load_status_flags_a_schema_version_mismatch_as_an_error_not_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps({"schema_version": 3, "actions": []}))
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    result = status_store.load_status()
    assert result["actions"] == []
    assert "status_error" in result
    assert "version 3" in result["status_error"]
    assert str(status_store.SCHEMA_VERSION) in result["status_error"]


def test_load_status_returns_a_valid_snapshot_unchanged(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps(_SAMPLE_STATUS))
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    result = status_store.load_status()
    assert result == _SAMPLE_STATUS
    assert "status_error" not in result


def test_write_status_then_load_status_round_trips(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(status_store, "DATA_DIR", tmp_path / "nested")
    monkeypatch.setattr(status_store, "STATUS_FILE", tmp_path / "nested" / "status.json")
    status_store.write_status(_SAMPLE_STATUS)
    assert status_store.load_status() == _SAMPLE_STATUS


# render_dashboard(): banner logic (none / stale / status_error)


def test_render_dashboard_has_no_banner_for_a_fresh_valid_status() -> None:
    html = render.render_dashboard(_fresh_status())
    assert 'class="banner' not in html


def test_render_dashboard_shows_the_status_error_banner() -> None:
    status = {**status_store.EMPTY_STATUS, "status_error": "The status file is broken."}
    html = render.render_dashboard(status)
    assert 'class="banner bad"' in html
    assert "The status file is broken." in html


def test_render_dashboard_shows_a_stale_banner_and_overrides_the_phase_pill() -> None:
    stale_status = {
        **_SAMPLE_STATUS,
        "generated_at": "2020-01-01T00:00:00+00:00",
    }
    html = render.render_dashboard(stale_status)
    assert 'class="banner warn"' in html
    assert "not live" in html
    # The instance card's own "running" claim is overridden, not repeated.
    assert 'class="pill warn"><span class="dot"></span>stale' in html
    assert 'class="pill ok"><span class="dot"></span>running' not in html


def test_render_dashboard_status_error_takes_precedence_over_stale() -> None:
    status = {
        **_fresh_status(),
        "generated_at": "2020-01-01T00:00:00+00:00",
        "status_error": "Broken and old.",
    }
    html = render.render_dashboard(status)
    assert html.count('class="banner') == 1
    assert 'class="banner bad"' in html
    assert "Broken and old." in html


def test_render_dashboard_empty_instance_shows_the_honest_empty_state() -> None:
    html = render.render_dashboard(status_store.EMPTY_STATUS)
    assert "No bridge instance has reported its status yet." in html
    assert "No actions recorded yet." in html
    assert "No other dashboards in the mesh yet." in html


# action_states.py: state -> category derivation


def test_every_display_state_has_a_category() -> None:
    assert set(STATE_STYLE) == set(STATE_CATEGORY)


def test_every_category_value_is_a_known_category() -> None:
    assert set(STATE_CATEGORY.values()) <= set(CATEGORY_LABEL)


def test_bridged_is_the_only_acted_state() -> None:
    acted = {state for state, category in STATE_CATEGORY.items() if category == "acted"}
    assert acted == {"bridged"}


def test_detected_is_the_only_pending_state() -> None:
    pending = {state for state, category in STATE_CATEGORY.items() if category == "pending"}
    assert pending == {"detected"}


def test_action_to_grid_row_derives_category_and_labels_from_state(monkeypatch: pytest.MonkeyPatch) -> None:
    row = render._action_to_grid_row(_SAMPLE_STATUS["actions"][0])
    assert row["state"] == "bridged"
    assert row["category"] == "acted"
    assert row["categoryLabel"] == CATEGORY_LABEL["acted"]
    assert row["eventTypeLabel"] == EVENT_TYPE_LABEL["posted"]


# mock_page.py: must render through render_dashboard, not reimplement it


def test_build_mock_page_delegates_to_render_dashboard_exactly(monkeypatch: pytest.MonkeyPatch) -> None:
    # _mock_status() computes "now" internally on every call, so freeze it to
    # one fixed status shared by both sides of the comparison below.
    fixed_status = mock_page._mock_status()
    monkeypatch.setattr(mock_page, "_mock_status", lambda: fixed_status)
    expected = render.render_dashboard(
        fixed_status, extra_banner=mock_page._REFERENCE_BANNER, title_suffix=" (reference)"
    )
    assert mock_page.build_mock_page() == expected


def test_mock_page_reuses_the_real_css_instead_of_hand_copying_it() -> None:
    html = mock_page.build_mock_page()
    assert html.count("<style>") == 1
    assert render.CSS in html


def test_mock_page_and_a_real_empty_page_share_the_same_section_structure() -> None:
    mock_html = mock_page.build_mock_page()
    real_html = render.render_dashboard(status_store.EMPTY_STATUS)
    for heading in ("This instance", "Recent actions", "Other operators"):
        assert f"<h2>{heading}</h2>" in mock_html
        assert f"<h2>{heading}</h2>" in real_html


def test_mock_page_covers_every_known_state() -> None:
    states_shown = {action["state"] for action in mock_page._mock_status()["actions"]}
    assert states_shown == set(STATE_STYLE)


# Contract: no raw message text anywhere


def test_no_raw_message_text_field_in_the_action_contract() -> None:
    row = render._action_to_grid_row(_SAMPLE_STATUS["actions"][0])
    for banned in ("snippet", "text", "message", "content"):
        assert banned not in row


def test_mock_page_never_invents_message_text() -> None:
    html = mock_page.build_mock_page()
    assert "snippet" not in html.lower()


# runner.py routes


def test_index_route_renders_the_honest_empty_state_with_no_status_file(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(status_store, "STATUS_FILE", tmp_path / "status.json")
    response = client.get("/")
    assert response.status_code == 200
    assert "No bridge instance has reported its status yet." in response.get_data(as_text=True)


def test_index_route_surfaces_a_status_error_banner(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, client) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text("not json")
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    response = client.get("/")
    assert 'class="banner bad"' in response.get_data(as_text=True)


def test_index_route_includes_the_shell_connection_script(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(status_store, "STATUS_FILE", tmp_path / "status.json")
    html = client.get("/").get_data(as_text=True)
    assert "connectToShell" in html
    assert html.rstrip().endswith("</html>")


def test_mock_route_renders_the_full_reference_page(client) -> None:
    response = client.get("/mock")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Reference page, not live data" in html
    assert "connectToShell" in html


def test_api_status_route_returns_the_same_data_load_status_would(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_file = tmp_path / "status.json"
    status_file.write_text(json.dumps(_SAMPLE_STATUS))
    monkeypatch.setattr(status_store, "STATUS_FILE", status_file)
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.get_json() == _SAMPLE_STATUS


def test_health_route(client) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_static_module_route_rejects_names_outside_the_allowlist(client) -> None:
    assert client.get("/_static/not-a-real-module.js").status_code == 404
    assert client.get("/_static/../../etc/passwd").status_code == 404


def test_static_module_route_404s_when_the_shell_build_is_missing(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Relative to the repo root every supervised program runs from -- see runner.py.
    monkeypatch.chdir(tmp_path)
    response = client.get("/_static/app_contract.js")
    assert response.status_code == 404


def test_static_module_route_serves_the_built_shell_module(
    client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    built = tmp_path / runner.SHELL_STATIC_MODULES_DIR / "app_contract.js"
    built.parent.mkdir(parents=True)
    built.write_text("export function connectToShell() {}\n")
    response = client.get("/_static/app_contract.js")
    assert response.status_code == 200
    assert response.mimetype == "text/javascript"
    assert "connectToShell" in response.get_data(as_text=True)
