import queue
import threading
import tkinter as tk
from tkinter import ttk
from typing import Callable


class DispatcherUI:
    def __init__(self, on_submit: Callable[[str], str]) -> None:
        self._on_submit = on_submit
        self._events: queue.Queue[tuple[str, str]] = queue.Queue()

        self.root = tk.Tk()
        self.root.title("Vox Dispatcher UI")
        self.root.geometry("860x560")

        self._build_layout()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(120, self._drain_events)

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        container.columnconfigure(0, weight=1)
        container.rowconfigure(2, weight=1)

        title = ttk.Label(container, text="Vox Dispatcher Chat Input", font=("Segoe UI", 15, "bold"))
        title.grid(row=0, column=0, sticky="w")

        subtitle = ttk.Label(
            container,
            text="Type command text below. Input is sent directly to the LLM orchestrator.",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(2, 10))

        self.output = tk.Text(
            container,
            wrap=tk.WORD,
            state=tk.DISABLED,
            height=14,
            font=("Segoe UI", 11),
        )
        self.output.grid(row=2, column=0, sticky="nsew")

        input_row = ttk.Frame(container)
        input_row.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        input_row.columnconfigure(0, weight=1)

        self.input_entry = tk.Text(
            input_row,
            height=2,
            wrap=tk.WORD,
            font=("Segoe UI", 11),
            borderwidth=1,
            relief="solid",
            padx=6,
            pady=4,
        )
        self.input_entry.grid(row=0, column=0, sticky="ew")
        self.input_entry.bind("<Return>", self._on_submit_enter)
        self.input_entry.bind("<KeyPress>", self._on_input_keypress, add=True)

        send_btn = ttk.Button(input_row, text="Send", command=self._on_submit_click, takefocus=False)
        send_btn.grid(row=0, column=1, padx=(8, 0), sticky="ns")

        self.input_entry.focus_set()

    def _append_output(self, line: str) -> None:
        self.output.configure(state=tk.NORMAL)
        self.output.insert(tk.END, line + "\n")
        self.output.see(tk.END)
        self.output.configure(state=tk.DISABLED)

    def _repair_keyboard_char(self, char: str) -> str:
        if len(char) != 1:
            return char

        if char not in "ýÝþÞðÐ":
            return char

        try:
            return char.encode("latin-1").decode("cp1254")
        except UnicodeError:
            return char

    def _on_input_keypress(self, event: tk.Event) -> str | None:
        char = getattr(event, "char", "")
        if not char:
            return None

        corrected = self._repair_keyboard_char(char)
        if corrected == char:
            return None

        self.input_entry.insert(tk.INSERT, corrected)
        return "break"

    def _on_submit_click(self, _event=None) -> None:
        text = self.input_entry.get("1.0", "end-1c").strip()
        if not text:
            self.input_entry.focus_set()
            return

        self._append_output(f"YOU: {text}")
        self.input_entry.delete("1.0", tk.END)
        self.input_entry.focus_set()

        worker = threading.Thread(target=self._invoke_orchestrator, args=(text,), daemon=True)
        worker.start()

    def _on_submit_enter(self, event: tk.Event) -> str:
        self._on_submit_click(event)
        return "break"

    def _invoke_orchestrator(self, text: str) -> None:
        try:
            result = self._on_submit(text)
        except Exception as exc:
            self._events.put(("llm", f"ERROR: {exc}"))
            return

        if not result:
            result = ""
        self._events.put(("llm", result))

    def _drain_events(self) -> None:
        while True:
            try:
                kind, text = self._events.get_nowait()
            except queue.Empty:
                break

            if kind == "llm":
                self._append_output(f"LLM: {text}")

        self.root.after(120, self._drain_events)

    def _on_close(self) -> None:
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
