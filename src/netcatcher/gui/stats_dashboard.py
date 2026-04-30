"""Statistics dashboard showing protocol distribution and traffic charts."""

from __future__ import annotations

from collections import Counter

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QGridLayout
from PyQt6.QtCore import Qt

from PyQt6.QtCharts import QChart, QChartView, QPieSeries, QBarSeries, QBarSet, QBarCategoryAxis
from PyQt6.QtGui import QPainter


class StatsDashboard(QWidget):
    """Dashboard widget showing capture statistics and charts."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._protocol_counts: Counter = Counter()
        self._total_packets = 0
        self._total_bytes = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # Summary cards
        cards_layout = QHBoxLayout()

        self._total_label = self._create_card("Total Packets", "0")
        cards_layout.addWidget(self._total_label)

        self._bytes_label = self._create_card("Total Bytes", "0 B")
        cards_layout.addWidget(self._bytes_label)

        self._protocols_label = self._create_card("Protocols", "0")
        cards_layout.addWidget(self._protocols_label)

        layout.addLayout(cards_layout)

        # Charts
        charts_layout = QHBoxLayout()

        # Protocol distribution pie chart
        self._pie_series = QPieSeries()
        self._pie_chart = QChart()
        self._pie_chart.addSeries(self._pie_series)
        self._pie_chart.setTitle("Protocol Distribution")
        self._pie_chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)

        self._pie_view = QChartView(self._pie_chart)
        self._pie_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        charts_layout.addWidget(self._pie_view)

        layout.addLayout(charts_layout, 1)

    def _create_card(self, title: str, value: str) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        label = QLabel(value)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(label)
        group._value_label = label
        return group

    def update_stats(self, protocol: str, length: int):
        """Update statistics with a new packet."""
        self._protocol_counts[protocol] += 1
        self._total_packets += 1
        self._total_bytes += length

        # Update summary cards
        self._total_label._value_label.setText(str(self._total_packets))
        self._bytes_label._value_label.setText(self._format_bytes(self._total_bytes))
        self._protocols_label._value_label.setText(str(len(self._protocol_counts)))

        # Update pie chart (refresh every 10 packets)
        if self._total_packets % 10 == 0:
            self._refresh_pie_chart()

    def _refresh_pie_chart(self):
        self._pie_series.clear()
        for protocol, count in self._protocol_counts.most_common(10):
            slice_ = self._pie_series.append(protocol, count)
            slice_.setLabel(f"{protocol}: {count}")

    def _format_bytes(self, size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def clear(self):
        self._protocol_counts.clear()
        self._total_packets = 0
        self._total_bytes = 0
        self._total_label._value_label.setText("0")
        self._bytes_label._value_label.setText("0 B")
        self._protocols_label._value_label.setText("0")
        self._pie_series.clear()
