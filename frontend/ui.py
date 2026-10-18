from __future__ import annotations

import time

import pandas as pd
from PyQt5.QtCore import Qt, QUrl, pyqtSlot
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend.scrap import (
    MAX_PAGES,
    TARGET_ENTITY_COUNT,
    ScraperThread,
    build_search_url,
)
from backend.sorting import sorting_algorithms as sa
from frontend import utility as ut


PAGE_SIZE = 250
BENCHMARK_SAMPLE_SIZE = 100
SORTERS = {
    "Bubble Sort": sa.bubbleSort,
    "Selection Sort": sa.selectionSort,
    "Insertion Sort": sa.insertionSort,
    "Merge Sort": sa.mergeSort,
    "Quick Sort": sa.quickSort,
    "Gnome Sort": sa.gnomeSort,
    "Heap Sort": sa.heapSort,
    "Counting Sort": sa.countingSort,
    "Radix Sort": sa.radixSort,
    "Bucket Sort": sa.bucketSort,
    "Odd-Even Sort": sa.oddEvenSort,
}
FILTER_OPERATORS = [
    "Contains",
    "Ends with",
    "Starts with",
    "Greater than",
    "Less than",
    "Equals",
]


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("eBay Product Explorer | DSA Project")
        self.resize(1180, 900)
        self.setMinimumSize(960, 740)
        self.data: pd.DataFrame | None = None
        self.filtered_data: pd.DataFrame | None = None
        self.scraper_thread: ScraperThread | None = None
        self.current_page = 0
        self.single_sort_time = 0.0
        self.scrape_file_name = ""

        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background-color: #111318;
                color: #e7eaf0;
                font-family: "Segoe UI";
                font-size: 10pt;
            }
            QGroupBox {
                border: 1px solid #303642;
                border-radius: 8px;
                margin-top: 12px;
                padding: 12px 10px 10px 10px;
                font-weight: 600;
                color: #f3c969;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 5px;
            }
            QLabel#brand {
                color: #f5c451;
                font-size: 24pt;
                font-weight: 800;
            }
            QLabel#subtitle, QLabel#muted {
                color: #aab2c0;
            }
            QLineEdit, QComboBox {
                background-color: #1b2029;
                color: #f3f5f8;
                border: 1px solid #394252;
                border-radius: 5px;
                padding: 7px;
                min-height: 20px;
            }
            QComboBox QAbstractItemView {
                background-color: #1b2029;
                color: #f3f5f8;
                selection-background-color: #38465d;
            }
            QPushButton {
                background-color: #252c38;
                color: #edf0f5;
                border: 1px solid #414c5e;
                border-radius: 5px;
                padding: 8px 13px;
                min-height: 20px;
            }
            QPushButton:hover { background-color: #333d4e; }
            QPushButton:disabled { color: #747d8b; background-color: #1a1e25; }
            QPushButton[role="primary"] {
                color: #151515;
                background-color: #f5c451;
                border-color: #f5c451;
                font-weight: 700;
            }
            QPushButton[role="primary"]:hover { background-color: #ffd675; }
            QPushButton[role="danger"] {
                color: white;
                background-color: #a43d4b;
                border-color: #a43d4b;
            }
            QTableWidget {
                background-color: #171b22;
                alternate-background-color: #1d232d;
                color: #e6eaf0;
                gridline-color: #303744;
                border: 1px solid #303744;
                selection-background-color: #3b506d;
                selection-color: white;
            }
            QHeaderView::section {
                background-color: #252c38;
                color: #f5c451;
                border: 0;
                border-bottom: 1px solid #3a4351;
                padding: 7px;
                font-weight: 700;
            }
            QProgressBar {
                background-color: #1b2029;
                color: #f3f5f8;
                border: 1px solid #394252;
                border-radius: 5px;
                text-align: center;
                min-height: 18px;
            }
            QProgressBar::chunk { background-color: #e6b948; border-radius: 4px; }
            QCheckBox { spacing: 7px; }
            QDialog { background-color: #111318; }
            """
        )
        self._build_ui()
        self.file_name_input.setText("Scraped")
        self.load_data_from_csv()

    def _button(self, text: str, role: str = "") -> QPushButton:
        button = QPushButton(text)
        if role:
            button.setProperty("role", role)
        return button

    def _build_ui(self) -> None:
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        title_row = QHBoxLayout()
        brand = QLabel("eBay")
        brand.setObjectName("brand")
        heading = QLabel("Product Explorer")
        heading.setStyleSheet("font-size: 19pt; font-weight: 700; color: #f3f5f8;")
        title_copy = QVBoxLayout()
        title_copy.addWidget(heading)
        subtitle = QLabel("Collect, search, sort, and compare product listings")
        subtitle.setObjectName("subtitle")
        title_copy.addWidget(subtitle)
        title_row.addWidget(brand)
        title_row.addSpacing(12)
        title_row.addLayout(title_copy)
        title_row.addStretch()
        layout.addLayout(title_row)

        scrape_group = QGroupBox("1  Collect eBay listings")
        scrape_layout = QGridLayout(scrape_group)
        self.data_scrap_product = QLineEdit()
        self.data_scrap_product.setPlaceholderText(
            "Product search term (for example: wireless headphones)"
        )
        self.search_url_input = QLineEdit()
        self.search_url_input.setPlaceholderText(
            "Optional: paste an eBay search-results URL (https://www.ebay.com/sch/...)"
        )
        self.open_search_btn = self._button("Open search")
        self.open_search_btn.clicked.connect(self.open_ebay_search)
        self.start_scrap_btn = self._button("Start scrape", "primary")
        self.start_scrap_btn.clicked.connect(self.start_scraping)
        self.pause_scrap_btn = self._button("Pause")
        self.pause_scrap_btn.clicked.connect(self.pause_scraping)
        self.resume_scrap_btn = self._button("Resume")
        self.resume_scrap_btn.clicked.connect(self.resume_scraping)
        self.stop_scrap_btn = self._button("Stop", "danger")
        self.stop_scrap_btn.clicked.connect(self.stop_scraping)
        self.pause_scrap_btn.setEnabled(False)
        self.resume_scrap_btn.setEnabled(False)
        self.stop_scrap_btn.setEnabled(False)

        scrape_layout.addWidget(QLabel("Product"), 0, 0)
        scrape_layout.addWidget(self.data_scrap_product, 0, 1, 1, 5)
        scrape_layout.addWidget(QLabel("eBay URL"), 1, 0)
        scrape_layout.addWidget(self.search_url_input, 1, 1, 1, 3)
        scrape_layout.addWidget(self.open_search_btn, 1, 4)
        scrape_layout.addWidget(self.start_scrap_btn, 1, 5)
        scrape_layout.addWidget(self.pause_scrap_btn, 1, 6)
        scrape_layout.addWidget(self.resume_scrap_btn, 1, 7)
        scrape_layout.addWidget(self.stop_scrap_btn, 1, 8)
        self.scrap_progress = QProgressBar()
        self.scrap_progress.setRange(0, 100)
        self.scrap_progress.setValue(0)
        self.scrape_count_label = QLabel(f"0 / {TARGET_ENTITY_COUNT:,} listings")
        self.scrape_count_label.setObjectName("muted")
        scrape_layout.addWidget(self.scrap_progress, 2, 0, 1, 8)
        scrape_layout.addWidget(self.scrape_count_label, 2, 8)
        layout.addWidget(scrape_group)

        load_row = QHBoxLayout()
        self.file_name_input = QLineEdit()
        self.file_name_input.setPlaceholderText(
            "CSV name in backend/data (example: Scraped or phone)"
        )
        self.load_from_csv_btn = self._button("Load CSV", "primary")
        self.load_from_csv_btn.clicked.connect(self.load_data_from_csv)
        self.dataset_info_label = QLabel("No dataset loaded")
        self.dataset_info_label.setObjectName("muted")
        load_row.addWidget(QLabel("Dataset"))
        load_row.addWidget(self.file_name_input, 2)
        load_row.addWidget(self.load_from_csv_btn)
        load_row.addWidget(self.dataset_info_label, 2)
        layout.addLayout(load_row)

        self.data_table = QTableWidget()
        self.data_table.setAlternatingRowColors(True)
        self.data_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.data_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.data_table.setWordWrap(False)
        self.data_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.verticalHeader().setDefaultSectionSize(25)
        layout.addWidget(self.data_table, 1)

        page_row = QHBoxLayout()
        self.previous_page_btn = self._button("Previous")
        self.previous_page_btn.clicked.connect(self.previous_table_page)
        self.table_page_label = QLabel("No rows")
        self.table_page_label.setAlignment(Qt.AlignCenter)
        self.table_page_label.setObjectName("muted")
        self.next_page_btn = self._button("Next")
        self.next_page_btn.clicked.connect(self.next_table_page)
        page_row.addStretch()
        page_row.addWidget(self.previous_page_btn)
        page_row.addWidget(self.table_page_label)
        page_row.addWidget(self.next_page_btn)
        page_row.addStretch()
        layout.addLayout(page_row)

        controls_row = QHBoxLayout()
        sort_group = QGroupBox("2  Sort")
        sort_form = QFormLayout(sort_group)
        self.algorithm_combobox = QComboBox()
        self.algorithm_combobox.addItems(SORTERS)
        self.sorting_column = QComboBox()
        self.sort_order_combobox = QComboBox()
        self.sort_order_combobox.addItems(["Ascending", "Descending"])
        self.secondary_sort_column = QComboBox()
        self.tertiary_sort_column = QComboBox()
        self.single_column_sort_btn = self._button("Sort column", "primary")
        self.single_column_sort_btn.clicked.connect(self.sort_data)
        self.multi_sort_btn = self._button("Multi-sort")
        self.multi_sort_btn.clicked.connect(self.multi_sort_data)
        self.single_sort_time_label = QLabel("Sort time: --")
        sort_form.addRow("Algorithm", self.algorithm_combobox)
        sort_form.addRow("Primary column", self.sorting_column)
        sort_form.addRow("Also by", self.secondary_sort_column)
        sort_form.addRow("Then by", self.tertiary_sort_column)
        sort_buttons = QHBoxLayout()
        sort_buttons.addWidget(self.sort_order_combobox)
        sort_buttons.addWidget(self.single_column_sort_btn)
        sort_buttons.addWidget(self.multi_sort_btn)
        sort_form.addRow(sort_buttons)
        sort_form.addRow(self.single_sort_time_label)
        controls_row.addWidget(sort_group, 1)

        filter_group = QGroupBox("3  Search and filter")
        filter_form = QFormLayout(filter_group)
        self.search_column_combobox = QComboBox()
        self.filter_combobox = QComboBox()
        self.filter_combobox.addItems(FILTER_OPERATORS)
        self.search_column_input = QLineEdit()
        self.search_column_input.setPlaceholderText("First condition")
        filter_form.addRow(self._condition_row(1))
        self.second_search_column_combobox = QComboBox()
        self.second_filter_combobox = QComboBox()
        self.second_filter_combobox.addItems(FILTER_OPERATORS)
        self.second_search_column_input = QLineEdit()
        self.second_search_column_input.setPlaceholderText("Optional second condition")
        filter_form.addRow(self._condition_row(2))
        logic_row = QHBoxLayout()
        self.search_logic_combobox = QComboBox()
        self.search_logic_combobox.addItems(["AND", "OR"])
        self.not_checkbox = QCheckBox("NOT (exclude matches)")
        self.search_column_sort_btn = self._button("Apply filters", "primary")
        self.search_column_sort_btn.clicked.connect(self.apply_filter)
        self.clear_filter_btn = self._button("Clear")
        self.clear_filter_btn.clicked.connect(self.clear_filter)
        logic_row.addWidget(self.search_logic_combobox)
        logic_row.addWidget(self.not_checkbox)
        logic_row.addWidget(self.search_column_sort_btn)
        logic_row.addWidget(self.clear_filter_btn)
        filter_form.addRow("Combine", logic_row)
        controls_row.addWidget(filter_group, 2)
        layout.addLayout(controls_row)

        footer_row = QHBoxLayout()
        self.benchmark_btn = self._button("Benchmark algorithms")
        self.benchmark_btn.clicked.connect(self.benchmark_sorting)
        self.message_box = QLabel(
            "Loaded sample data is ready. Search or sort the table, or enter an eBay URL above."
        )
        self.message_box.setWordWrap(True)
        footer_row.addWidget(self.benchmark_btn)
        footer_row.addWidget(self.message_box, 1)
        layout.addLayout(footer_row)
        self._set_column_choices([])

    def _condition_row(self, row: int) -> QWidget:
        container = QWidget()
        row_layout = QHBoxLayout(container)
        row_layout.setContentsMargins(0, 0, 0, 0)
        if row == 1:
            column, operator, query = (
                self.search_column_combobox,
                self.filter_combobox,
                self.search_column_input,
            )
        else:
            column, operator, query = (
                self.second_search_column_combobox,
                self.second_filter_combobox,
                self.second_search_column_input,
            )
        row_layout.addWidget(column, 2)
        row_layout.addWidget(operator, 1)
        row_layout.addWidget(query, 2)
        return container

    def _set_column_choices(self, columns: list[str]) -> None:
        selectors = (
            self.sorting_column,
            self.secondary_sort_column,
            self.tertiary_sort_column,
            self.search_column_combobox,
            self.second_search_column_combobox,
        )
        for selector in selectors:
            old_value = selector.currentText()
            selector.clear()
            if selector in (self.secondary_sort_column, self.tertiary_sort_column):
                selector.addItem("None")
            selector.addItems(columns)
            index = selector.findText(old_value)
            if index >= 0:
                selector.setCurrentIndex(index)

    def open_ebay_search(self) -> None:
        try:
            url = build_search_url(
                self.data_scrap_product.text().strip(),
                1,
                self.search_url_input.text().strip(),
            )
            if not QDesktopServices.openUrl(QUrl(url)):
                raise RuntimeError("Windows could not open the eBay search link.")
            self.message_box.setText("Opened the eBay search page in your browser.")
        except (ValueError, RuntimeError) as exc:
            self.message_box.setText(str(exc))

    def start_scraping(self) -> None:
        if self.scraper_thread is not None:
            self.message_box.setText("A scrape is already running.")
            return
        try:
            product_name = self.data_scrap_product.text().strip()
            search_url = self.search_url_input.text().strip()
            scraper = ScraperThread(
                product_name=product_name,
                total_pages=MAX_PAGES,
                search_url=search_url,
                target_entities=TARGET_ENTITY_COUNT,
            )
            scraper.progress_signal.connect(self.update_progress)
            scraper.entity_progress_signal.connect(self.update_entity_progress)
            scraper.finished_signal.connect(self.scraping_finished)
            self.scrape_file_name = scraper._output_path().stem
            self.scraper_thread = scraper
            self.scrap_progress.setValue(0)
            self.scrape_count_label.setText(f"0 / {TARGET_ENTITY_COUNT:,} listings")
            scraper.start()
            self.start_scrap_btn.setEnabled(False)
            self.pause_scrap_btn.setEnabled(True)
            self.resume_scrap_btn.setEnabled(False)
            self.stop_scrap_btn.setEnabled(True)
            self.message_box.setText(
                f"Scraping started. Target: {TARGET_ENTITY_COUNT:,} unique listings."
            )
        except (ValueError, RuntimeError) as exc:
            self.scraper_thread = None
            self.message_box.setText(str(exc))

    def pause_scraping(self) -> None:
        if self.scraper_thread is not None:
            self.scraper_thread.pause()
            self.pause_scrap_btn.setEnabled(False)
            self.resume_scrap_btn.setEnabled(True)
            self.message_box.setText("Scraping paused.")

    def resume_scraping(self) -> None:
        if self.scraper_thread is not None:
            self.scraper_thread.resume()
            self.pause_scrap_btn.setEnabled(True)
            self.resume_scrap_btn.setEnabled(False)
            self.message_box.setText("Scraping resumed.")

    def stop_scraping(self) -> None:
        if self.scraper_thread is not None:
            self.scraper_thread.stop()
            self.pause_scrap_btn.setEnabled(False)
            self.resume_scrap_btn.setEnabled(False)
            self.stop_scrap_btn.setEnabled(False)
            self.message_box.setText("Stopping after the current page finishes...")

    @pyqtSlot(int)
    def update_progress(self, progress: int) -> None:
        self.scrap_progress.setValue(progress)

    @pyqtSlot(int, int)
    def update_entity_progress(self, count: int, target: int) -> None:
        self.scrape_count_label.setText(f"{count:,} / {target:,} listings")

    @pyqtSlot(str)
    def scraping_finished(self, message: str) -> None:
        self.start_scrap_btn.setEnabled(True)
        self.pause_scrap_btn.setEnabled(False)
        self.resume_scrap_btn.setEnabled(False)
        self.stop_scrap_btn.setEnabled(False)
        self.scraper_thread = None
        self.message_box.setText(message)
        self.file_name_input.setText(self.scrape_file_name)

    def load_data_from_csv(self) -> None:
        file_name = self.file_name_input.text().strip()
        if not file_name:
            self.message_box.setText("Enter a CSV name, such as Scraped or phone.")
            return
        try:
            self.data = ut.load_data(file_name)
            self.filtered_data = None
            self.current_page = 0
            self._set_column_choices([str(column) for column in self.data.columns])
            self.load_data_to_table()
            self.dataset_info_label.setText(
                f"{len(self.data):,} records  |  {len(self.data.columns)} attributes"
            )
            self.message_box.setText(
                f"Loaded {len(self.data):,} records from {file_name}."
            )
        except (FileNotFoundError, OSError, ValueError, pd.errors.ParserError) as exc:
            self.message_box.setText(f"Could not load CSV: {exc}")

    def _active_data(self) -> pd.DataFrame | None:
        return self.filtered_data if self.filtered_data is not None else self.data

    def _ascending(self) -> bool:
        return self.sort_order_combobox.currentText() == "Ascending"

    def sort_data(self) -> None:
        if self.data is None:
            self.message_box.setText("Load data before sorting.")
            return
        column = self.sorting_column.currentText()
        if not column:
            self.message_box.setText("Choose a column to sort.")
            return
        source = self._active_data()
        sorter = SORTERS[self.algorithm_combobox.currentText()]
        start = time.perf_counter()
        result = sorter(
            source.copy(), column, ascending=self._ascending(), return_metrics=True
        )
        self.single_sort_time = (time.perf_counter() - start) * 1000
        if not result.success:
            self.message_box.setText(f"Sort failed: {result.message}")
            return
        if self.filtered_data is not None:
            self.filtered_data = result.data
        else:
            self.data = result.data
        self.single_sort_time_label.setText(
            f"Sort time: {result.execution_time_ms:.2f} ms"
        )
        self.message_box.setText(
            f"{result.algorithm} sorted {len(result.data):,} rows by {column}; "
            f"{result.comparisons:,} comparisons and {result.swaps:,} swaps."
        )
        self.current_page = 0
        self.load_data_to_table()

    def multi_sort_data(self) -> None:
        source = self._active_data()
        if source is None:
            self.message_box.setText("Load data before sorting.")
            return
        columns = [
            column
            for column in (
                self.sorting_column.currentText(),
                self.secondary_sort_column.currentText(),
                self.tertiary_sort_column.currentText(),
            )
            if column and column != "None"
        ]
        columns = list(dict.fromkeys(columns))
        if len(columns) < 2:
            self.message_box.setText("Select at least two different sort columns.")
            return

        start = time.perf_counter()
        ordered = source.copy()
        for column in reversed(columns):
            ordered = ordered.sort_values(
                by=column, ascending=self._ascending(), kind="mergesort", na_position="last"
            )
        ordered = ordered.reset_index(drop=True)
        elapsed = (time.perf_counter() - start) * 1000
        if self.filtered_data is not None:
            self.filtered_data = ordered
        else:
            self.data = ordered
        self.single_sort_time_label.setText(f"Sort time: {elapsed:.2f} ms")
        self.message_box.setText(f"Multi-column sorted by {' then '.join(columns)}.")
        self.current_page = 0
        self.load_data_to_table()

    def benchmark_sorting(self) -> None:
        source = self._active_data()
        column = self.sorting_column.currentText()
        if source is None or not column:
            self.message_box.setText("Load a dataset and choose a column to benchmark.")
            return
        sample = source.head(BENCHMARK_SAMPLE_SIZE).copy()
        results = sa.benchmark_algorithms(sample, column, ascending=self._ascending())

        dialog = QDialog(self)
        dialog.setWindowTitle("Sorting algorithm benchmark")
        dialog.resize(920, 430)
        dialog_layout = QVBoxLayout(dialog)
        intro = QLabel(
            f"Comparing algorithms on the first {len(sample):,} of {len(source):,} "
            f"rows, column “{column}”. A sample keeps slow O(n²) algorithms responsive."
        )
        intro.setWordWrap(True)
        dialog_layout.addWidget(intro)
        table = QTableWidget(len(results), 7)
        table.setHorizontalHeaderLabels(
            ["Algorithm", "Time (ms)", "Comparisons", "Swaps", "Writes", "Complexity", "Status"]
        )
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        for row, result in enumerate(results):
            values = [
                result.algorithm,
                f"{result.execution_time_ms:.2f}",
                f"{result.comparisons:,}",
                f"{result.swaps:,}",
                f"{result.writes:,}",
                f"{result.time_complexity} · {result.stability}",
                "OK" if result.success else result.message,
            ]
            for col, value in enumerate(values):
                table.setItem(row, col, QTableWidgetItem(value))
        dialog_layout.addWidget(table)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        dialog_layout.addWidget(buttons)
        dialog.exec_()

    def _criterion_mask(
        self, column_name: str, operator: str, query: str
    ) -> pd.Series:
        if self.data is None or column_name not in self.data.columns:
            raise ValueError("Choose a valid column for each search condition.")
        column = self.data[column_name]
        if operator in {"Greater than", "Less than", "Equals"}:
            if not pd.api.types.is_numeric_dtype(column):
                raise ValueError(f"{operator} requires a numeric column ({column_name}).")
            try:
                value = float(query)
            except ValueError as exc:
                raise ValueError(f"Enter a number for {column_name}.") from exc
            if operator == "Greater than":
                return column > value
            if operator == "Less than":
                return column < value
            return column == value

        values = column.astype("string").str.lower()
        needle = query.lower()
        if operator == "Contains":
            return values.str.contains(needle, na=False, regex=False)
        if operator == "Starts with":
            return values.str.startswith(needle, na=False)
        return values.str.endswith(needle, na=False)

    def apply_filter(self) -> None:
        if self.data is None:
            self.message_box.setText("Load data before searching.")
            return
        conditions = [
            (
                self.search_column_combobox.currentText(),
                self.filter_combobox.currentText(),
                self.search_column_input.text().strip(),
            ),
            (
                self.second_search_column_combobox.currentText(),
                self.second_filter_combobox.currentText(),
                self.second_search_column_input.text().strip(),
            ),
        ]
        active = [condition for condition in conditions if condition[2]]
        if not active:
            self.clear_filter()
            return
        try:
            masks = [
                self._criterion_mask(column, operator, query)
                for column, operator, query in active
            ]
        except ValueError as exc:
            self.message_box.setText(str(exc))
            return

        matches = masks[0]
        if len(masks) == 2:
            if self.search_logic_combobox.currentText() == "AND":
                matches = matches & masks[1]
            else:
                matches = matches | masks[1]
        if self.not_checkbox.isChecked():
            matches = ~matches
        self.filtered_data = self.data.loc[matches].reset_index(drop=True)
        self.current_page = 0
        self.load_data_to_table()
        self.message_box.setText(
            f"Found {len(self.filtered_data):,} matching records "
            f"({self.search_logic_combobox.currentText()}"
            f"{' + NOT' if self.not_checkbox.isChecked() else ''})."
        )

    def clear_filter(self) -> None:
        self.filtered_data = None
        self.search_column_input.clear()
        self.second_search_column_input.clear()
        self.not_checkbox.setChecked(False)
        self.current_page = 0
        self.load_data_to_table()
        self.message_box.setText("Search filters cleared.")

    def load_data_to_table(self) -> None:
        display_data = self._active_data()
        if display_data is None:
            self.data_table.clear()
            self.data_table.setRowCount(0)
            self.data_table.setColumnCount(0)
            self.table_page_label.setText("No rows")
            self.previous_page_btn.setEnabled(False)
            self.next_page_btn.setEnabled(False)
            return

        self.data_table.setUpdatesEnabled(False)
        start = self.current_page * PAGE_SIZE
        page = display_data.iloc[start : start + PAGE_SIZE]
        self.data_table.clear()
        self.data_table.setColumnCount(len(display_data.columns))
        self.data_table.setRowCount(len(page))
        self.data_table.setHorizontalHeaderLabels(
            [str(column) for column in display_data.columns]
        )
        for row_index, (_, row) in enumerate(page.iterrows()):
            for column_index, value in enumerate(row):
                text = "" if pd.isna(value) else str(value)
                self.data_table.setItem(
                    row_index, column_index, QTableWidgetItem(text)
                )
        self.data_table.setUpdatesEnabled(True)

        total = len(display_data)
        first = start + 1 if total else 0
        last = min(start + len(page), total)
        pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
        self.table_page_label.setText(
            f"Rows {first:,}–{last:,} of {total:,}  ·  Page "
            f"{self.current_page + 1} of {pages}"
        )
        self.previous_page_btn.setEnabled(self.current_page > 0)
        self.next_page_btn.setEnabled((self.current_page + 1) * PAGE_SIZE < total)

    def previous_table_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self.load_data_to_table()

    def next_table_page(self) -> None:
        source = self._active_data()
        if source is not None and (self.current_page + 1) * PAGE_SIZE < len(source):
            self.current_page += 1
            self.load_data_to_table()

    def closeEvent(self, event) -> None:
        if self.scraper_thread is not None:
            self.scraper_thread.stop()
        event.accept()
