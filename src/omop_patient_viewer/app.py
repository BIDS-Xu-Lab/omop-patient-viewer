from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import Footer, Header, ListItem, ListView, Static

from .formatters import format_record, join_lines, without_keys
from .loader import load_tables
from .repository import OmopRepository


class HelpScreen(ModalScreen[None]):
    def compose(self) -> ComposeResult:
        yield Container(
            Static(
                "\n".join(
                    [
                        "Keys",
                        "",
                        "Up/Down or j/k: move selection",
                        "Tab: switch focus",
                        "v: toggle table/visit view",
                        "]: next table",
                        "[: previous table",
                        "x: expand/collapse full records",
                        "r: reload CSV data",
                        "q: quit",
                        "?: show help",
                    ]
                ),
                id="help-text",
            ),
            id="help-dialog",
        )

    def on_key(self, event) -> None:  # type: ignore[override]
        event.stop()
        self.dismiss()


class OmopPatientViewerApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
    }

    #patient-pane {
        width: 36;
        min-width: 28;
        border: round $accent;
    }

    #details-pane {
        width: 1fr;
        border: round $accent;
    }

    #details-summary {
        border-bottom: solid $panel;
        height: auto;
    }

    #details-main {
        height: 1fr;
    }

    #detail-nav-pane {
        width: 30;
        min-width: 24;
        border-right: solid $panel;
    }

    #detail-content-pane {
        width: 1fr;
    }

    #detail-content-scroll {
        height: 1fr;
    }

    .panel-title {
        padding: 0 1;
        text-style: bold;
        color: $text;
        background: $boost;
    }

    .panel-body {
        padding: 1;
        height: 1fr;
        overflow: auto auto;
    }

    VerticalScroll:focus {
        border: round $accent-lighten-1;
    }

    #patient-list {
        height: 1fr;
    }

    #help-dialog {
        width: 60;
        height: auto;
        border: round $warning;
        background: $surface;
        padding: 1 2;
    }

    #help-text {
        width: 1fr;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("tab", "focus_next", "Next Focus"),
        Binding("shift+tab", "focus_previous", "Prev Focus"),
        Binding("v", "toggle_view", "Toggle View"),
        Binding("x", "toggle_expand", "Expand"),
        Binding("r", "reload_data", "Reload"),
        Binding("[", "prev_table", "Prev Table"),
        Binding("]", "next_table", "Next Table"),
        Binding("?", "show_help", "Help"),
        Binding("j", "cursor_down", "Down", show=False),
        Binding("k", "cursor_up", "Up", show=False),
    ]

    current_person_id = reactive("")
    current_view_mode = reactive("table")
    current_table_index = reactive(0)
    current_visit_index = reactive(0)
    expanded_records = reactive(False)

    def __init__(self, csv_dir: Path) -> None:
        super().__init__()
        self.csv_dir = csv_dir
        self.repository = self._load_repository()
        self._patient_ids: list[str] = []
        self._table_names: list[str] = []
        self._visits = []

    def _load_repository(self) -> OmopRepository:
        tables = load_tables(self.csv_dir)
        return OmopRepository(tables)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal(id="body"):
            with Vertical(id="patient-pane"):
                yield Static("Patients", classes="panel-title")
                yield ListView(id="patient-list")
            with Vertical(id="details-pane"):
                yield Static("", id="details-title", classes="panel-title")
                yield Static("", id="details-summary", classes="panel-body")
                with Horizontal(id="details-main"):
                    with Vertical(id="detail-nav-pane"):
                        yield Static("", id="detail-nav-title", classes="panel-title")
                        yield ListView(id="detail-nav")
                    with Vertical(id="detail-content-pane"):
                        yield Static("", id="detail-content-title", classes="panel-title")
                        with VerticalScroll(id="detail-content-scroll", classes="panel-body"):
                            yield Static("", id="detail-content")
        yield Footer()

    def on_mount(self) -> None:
        self._populate_patients()
        self.query_one("#patient-list", ListView).focus()

    def _populate_patients(self) -> None:
        patient_list = self.query_one("#patient-list", ListView)
        patient_list.clear()
        self._patient_ids = []
        for stats in self.repository.list_patients():
            label = f"{stats.person_id} (v={stats.visit_count}, r={stats.event_count})"
            self._patient_ids.append(stats.person_id)
            patient_list.append(ListItem(Static(label)))

        patients = self.repository.list_patients()
        if patients:
            self.current_person_id = patients[0].person_id
            patient_list.index = 0
            self._refresh_details()

    def _refresh_details(self) -> None:
        title = self.query_one("#details-title", Static)
        summary = self.query_one("#details-summary", Static)
        nav_title = self.query_one("#detail-nav-title", Static)
        content_title = self.query_one("#detail-content-title", Static)
        content = self.query_one("#detail-content", Static)
        content_scroll = self.query_one("#detail-content-scroll", VerticalScroll)

        if not self.current_person_id:
            title.update("No patient selected")
            summary.update("")
            nav_title.update("")
            content_title.update("")
            content.update("")
            content_scroll.scroll_home(animate=False)
            return

        summary_lines = self.repository.get_patient_summary_lines(self.current_person_id)
        view_label = "Table View" if self.current_view_mode == "table" else "Visit Based View"
        title.update(f"Patient {self.current_person_id} | {view_label}")
        summary.update(join_lines(summary_lines))

        if self.current_view_mode == "table":
            self._populate_table_nav()
            nav_title.update("Tables")
            content_title.update("Records")
            content.update(self._build_table_view())
        else:
            self._populate_visit_nav()
            nav_title.update("Visits")
            content_title.update("Visit Records")
            content.update(self._build_visit_view())
        content_scroll.scroll_home(animate=False)

    def _populate_table_nav(self) -> None:
        nav = self.query_one("#detail-nav", ListView)
        nav.clear()
        self._table_names = self.repository.get_patient_tables(self.current_person_id)
        for table_name in self._table_names:
            count = len(self.repository.get_patient_rows(self.current_person_id, table_name))
            nav.append(ListItem(Static(f"{table_name} ({count})")))
        if self._table_names:
            self.current_table_index = min(self.current_table_index, len(self._table_names) - 1)
            nav.index = self.current_table_index

    def _build_table_view(self) -> str:
        if not self._table_names:
            return "No patient data found."

        self.current_table_index = min(self.current_table_index, len(self._table_names) - 1)
        current_table = self._table_names[self.current_table_index]
        rows = self.repository.get_patient_rows(self.current_person_id, current_table)
        lines = [f"Table {self.current_table_index + 1}/{len(self._table_names)}: {current_table}", ""]
        if not rows:
            lines.append("No rows.")
            return join_lines(lines)

        for index, row in enumerate(rows[:50], start=1):
            lines.append(f"[{index}] {format_record(row, self.expanded_records)}")
            if self.expanded_records:
                lines.append("")

        if len(rows) > 50:
            lines.append(f"... truncated, showing 50 of {len(rows)} rows")
        return join_lines(lines)

    def _populate_visit_nav(self) -> None:
        nav = self.query_one("#detail-nav", ListView)
        nav.clear()
        self._visits = self.repository.get_patient_visits(self.current_person_id)
        if not self._visits:
            return
        for visit in self._visits:
            label = (
                f"{visit.visit_occurrence_id} "
                f"{visit.visit_start_date} "
                f"({visit.event_count})"
            )
            nav.append(ListItem(Static(label)))
        self.current_visit_index = min(self.current_visit_index, len(self._visits) - 1)
        nav.index = self.current_visit_index

    def _build_visit_view(self) -> str:
        if not self._visits:
            return "No Visit Data"

        self.current_visit_index = min(self.current_visit_index, len(self._visits) - 1)
        selected_visit = self._visits[self.current_visit_index]
        bundle = self.repository.get_visit_bundle(selected_visit.visit_occurrence_id)
        lines = [
            f"Selected Visit: {selected_visit.visit_occurrence_id}",
            f"Date Range: {selected_visit.visit_start_date} -> {selected_visit.visit_end_date}",
            f"Event Count: {selected_visit.event_count}",
            "",
        ]

        for table_name, rows in bundle.items():
            lines.extend(self._section_header(f"{table_name} ({len(rows)})"))
            if not rows:
                lines.append("  No rows")
                lines.append("")
                continue
            for row in rows[:10]:
                display_row = without_keys(row, {"person_id", "visit_occurrence_id"})
                lines.append(f"  - {format_record(display_row, self.expanded_records)}")
            if len(rows) > 10:
                lines.append(f"  ... truncated, showing 10 of {len(rows)} rows")
            lines.append("")

        unlinked = self.repository.get_unlinked_patient_records(self.current_person_id)
        if unlinked:
            lines.extend(self._section_header("Patient-level Records"))
            for table_name, rows in unlinked.items():
                lines.append(f"{table_name} ({len(rows)})")
                for row in rows[:5]:
                    display_row = without_keys(row, {"person_id", "visit_occurrence_id"})
                    lines.append(f"  - {format_record(display_row, self.expanded_records)}")
                if len(rows) > 5:
                    lines.append(f"  ... truncated, showing 5 of {len(rows)} rows")
                lines.append("")
        return join_lines(lines)

    def _section_header(self, title: str) -> list[str]:
        line = "-" * 22
        return [line, title, line]

    @on(ListView.Selected, "#patient-list")
    def _on_patient_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is None:
            return
        self.current_person_id = self._patient_ids[event.list_view.index]
        self.current_table_index = 0
        self.current_visit_index = 0
        self._refresh_details()

    @on(ListView.Selected, "#detail-nav")
    def _on_detail_nav_selected(self, event: ListView.Selected) -> None:
        if event.list_view.index is None:
            return
        if self.current_view_mode == "table":
            self.current_table_index = event.list_view.index
        else:
            self.current_visit_index = event.list_view.index
        self._refresh_details()

    def action_toggle_view(self) -> None:
        self.current_view_mode = "visit" if self.current_view_mode == "table" else "table"
        self.current_table_index = 0
        self.current_visit_index = 0
        self._refresh_details()

    def action_toggle_expand(self) -> None:
        self.expanded_records = not self.expanded_records
        self._refresh_details()

    def action_reload_data(self) -> None:
        self.repository = self._load_repository()
        self.current_table_index = 0
        self._populate_patients()
        self.notify(f"Reloaded data from {self.csv_dir}")

    def action_prev_table(self) -> None:
        if self.current_view_mode != "table":
            return
        if self.current_table_index > 0:
            self.current_table_index -= 1
            self.query_one("#detail-nav", ListView).index = self.current_table_index
            self._refresh_details()

    def action_next_table(self) -> None:
        if self.current_view_mode != "table":
            return
        if self.current_table_index < len(self._table_names) - 1:
            self.current_table_index += 1
            self.query_one("#detail-nav", ListView).index = self.current_table_index
            self._refresh_details()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_cursor_down(self) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            focused.action_cursor_down()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_down(animate=False)

    def action_cursor_up(self) -> None:
        focused = self.focused
        if isinstance(focused, ListView):
            focused.action_cursor_up()
        elif isinstance(focused, VerticalScroll):
            focused.scroll_up(animate=False)
