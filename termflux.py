"""A terminal client for Miniflux."""

import json
import pathlib

import appdirs
import markdownify
import miniflux
from textual import app, screen, widgets

APPNAME = "termflux"


def config_file() -> pathlib.Path:
    return pathlib.Path(appdirs.user_config_dir(APPNAME)) / "config.json"


def read_config() -> dict:
    return json.loads(config_file().read_text()) if config_file().exists() else {}


def write_config(config: dict) -> None:
    config_file().parent.mkdir(parents=True, exist_ok=True)
    config_file().write_text(json.dumps(config))


def login() -> None:
    instance = input("instance url ")
    api_key = input("api key ")

    config = read_config()
    config["instance"] = instance
    config["api_key"] = api_key
    write_config(config)


def client() -> miniflux.Client:
    config = read_config()
    return miniflux.Client(config["instance"], api_key=config["api_key"])


class Termflux(app.App):
    BINDINGS = [
        ("q", "quit()", "quit"),
        ("r", "read()", "mark as read"),
    ]

    def on_mount(self) -> None:
        self.client = client()

        self.table = self.query_one("#entries")
        self.entries = self.client.get_entries(status="unread", order="published_at")[
            "entries"
        ]

        self.table.add_column("R", key="read")
        self.table.add_column("title", width=120)
        self.table.add_column("feed")

        for index, entry in enumerate(self.entries):
            self.table.add_row("*", entry["title"], entry["feed"]["title"], key=index)

    def on_data_table_row_selected(self) -> None:
        self.action_select()
        self.action_open()

    def on_data_table_row_highlighted(self) -> None:
        self.action_select()

    def compose(self) -> None:
        yield widgets.DataTable(id="entries", cursor_type="row")
        yield widgets.Footer()

    def action_select(self) -> None:
        self.selected_entry = self.entries[self.table.cursor_coordinate.row]

    def action_open(self) -> None:
        self.push_screen(EntryScreen())

    def action_read(self) -> None:
        self.client.update_entries([self.selected_entry["id"]], "read")
        row_key, _ = self.table.coordinate_to_cell_key(self.table.cursor_coordinate)
        self.table.update_cell(row_key, "read", "")
        self.table.move_cursor(row=self.table.cursor_coordinate.row + 1)


class EntryScreen(screen.ModalScreen):
    BINDINGS = [
        ("q", "app.pop_screen()", "back"),
        ("right", "next()", "next"),
    ]

    def compose(self) -> None:
        entry = self.app.selected_entry

        content = "# " + entry["title"] + "\n\n"
        content += markdownify.markdownify(entry["content"])

        yield widgets.Markdown(content)
        yield widgets.Footer()

    def action_next(self) -> None:
        self.app.pop_screen()
        self.app.action_read()
        self.app.action_select()
        self.app.action_open()


def ui() -> None:
    Termflux().run()


if __name__ == "__main__":
    ui()
