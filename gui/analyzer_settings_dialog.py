from __future__ import annotations
from typing import Dict, Any, Tuple

from PyQt5.QtWidgets import (
    QDialog, QTabWidget, QWidget, QFormLayout, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QDialogButtonBox, QHBoxLayout, QLabel
)
from PyQt5.QtCore import Qt

from config.analyzers_config import load_config, save_config


class AnalyzerSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Analyzer Settings")
        self.setModal(True)
        self.resize(520, 380)

        self.cfg = load_config()

        self.tabs = QTabWidget()
        self._bertopic_tab = self._make_bertopic_tab()
        self._lda_tab = self._make_lda_tab()
        self._keybert_tab = self._make_keybert_tab()
        self._gemini_tab = self._make_gemini_tab()

        self.tabs.addTab(self._bertopic_tab, "BERTopic")
        self.tabs.addTab(self._lda_tab, "LDA")
        self.tabs.addTab(self._keybert_tab, "KeyBERT")
        self.tabs.addTab(self._gemini_tab, "Gemini")

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self._save_and_close)
        buttons.rejected.connect(self.reject)

        layout = QHBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addWidget(buttons)
        layout.setStretch(0, 1)

    # ----------------- BERTopic -----------------
    def _make_bertopic_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        c = self.cfg["bertopic"]

        self.bt_embedding = QLineEdit(c.get("embedding_model", "all-MiniLM-L6-v2"))
        f.addRow("Embedding model:", self.bt_embedding)

        # nr_topics: "auto" or int
        self.bt_nr_topics_mode = QComboBox()
        self.bt_nr_topics_mode.addItems(["auto", "fixed"])
        mode = "auto" if str(c.get("nr_topics", "auto")) == "auto" else "fixed"
        self.bt_nr_topics_mode.setCurrentText(mode)
        self.bt_nr_topics = QSpinBox()
        self.bt_nr_topics.setRange(2, 200)
        if mode == "fixed" and isinstance(c.get("nr_topics"), int):
            self.bt_nr_topics.setValue(int(c["nr_topics"]))
        self.bt_nr_topics.setEnabled(mode == "fixed")
        self.bt_nr_topics_mode.currentTextChanged.connect(
            lambda t: self.bt_nr_topics.setEnabled(t == "fixed")
        )
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.addWidget(QLabel("Mode:"))
        row_layout.addWidget(self.bt_nr_topics_mode)
        row_layout.addWidget(QLabel("Value:"))
        row_layout.addWidget(self.bt_nr_topics)
        f.addRow("nr_topics:", row)

        self.bt_min_topic_size = QSpinBox()
        self.bt_min_topic_size.setRange(2, 50)
        self.bt_min_topic_size.setValue(int(c.get("min_topic_size", 2)))
        f.addRow("min_topic_size:", self.bt_min_topic_size)

        self.bt_top_n_words = QSpinBox()
        self.bt_top_n_words.setRange(3, 50)
        self.bt_top_n_words.setValue(int(c.get("top_n_words", 10)))
        f.addRow("top_n_words:", self.bt_top_n_words)

        self.bt_max_df = QDoubleSpinBox()
        self.bt_max_df.setRange(0.1, 1.0)
        self.bt_max_df.setSingleStep(0.05)
        self.bt_max_df.setDecimals(2)
        self.bt_max_df.setValue(float(c.get("vectorizer_max_df", 0.95)))
        f.addRow("vectorizer_max_df:", self.bt_max_df)

        self.bt_min_df = QSpinBox()
        self.bt_min_df.setRange(1, 20)
        self.bt_min_df.setValue(int(c.get("vectorizer_min_df", 1)))
        f.addRow("vectorizer_min_df:", self.bt_min_df)

        self.bt_ng_min = QSpinBox()
        self.bt_ng_max = QSpinBox()
        self.bt_ng_min.setRange(1, 5)
        self.bt_ng_max.setRange(1, 5)
        ng = tuple(c.get("ngram_range", (1, 2)))
        self.bt_ng_min.setValue(int(ng[0]))
        self.bt_ng_max.setValue(int(ng[1]))
        row2 = QWidget()
        row2l = QHBoxLayout(row2)
        row2l.addWidget(self.bt_ng_min)
        row2l.addWidget(QLabel("to"))
        row2l.addWidget(self.bt_ng_max)
        f.addRow("ngram_range:", row2)

        return w

    # ----------------- LDA -----------------
    def _make_lda_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        c = self.cfg["lda"]

        self.lda_topics = QSpinBox()
        self.lda_topics.setRange(2, 100)
        self.lda_topics.setValue(int(c.get("n_topics", 5)))
        f.addRow("n_topics:", self.lda_topics)

        self.lda_max_features = QSpinBox()
        self.lda_max_features.setRange(1000, 200000)
        self.lda_max_features.setSingleStep(1000)
        self.lda_max_features.setValue(int(c.get("max_features", 20000)))
        f.addRow("max_features:", self.lda_max_features)

        self.lda_top_n_words = QSpinBox()
        self.lda_top_n_words.setRange(3, 50)
        self.lda_top_n_words.setValue(int(c.get("top_n_words", 10)))
        f.addRow("top_n_words:", self.lda_top_n_words)

        self.lda_min_df = QSpinBox()
        self.lda_min_df.setRange(1, 50)
        self.lda_min_df.setValue(int(c.get("min_df", 1)))
        f.addRow("min_df:", self.lda_min_df)

        self.lda_max_df = QDoubleSpinBox()
        self.lda_max_df.setRange(0.1, 1.0)
        self.lda_max_df.setSingleStep(0.05)
        self.lda_max_df.setDecimals(2)
        self.lda_max_df.setValue(float(c.get("max_df", 0.95)))
        f.addRow("max_df:", self.lda_max_df)

        self.lda_ng_min = QSpinBox()
        self.lda_ng_max = QSpinBox()
        self.lda_ng_min.setRange(1, 5)
        self.lda_ng_max.setRange(1, 5)
        ng = tuple(c.get("ngram_range", (1, 2)))
        self.lda_ng_min.setValue(int(ng[0]))
        self.lda_ng_max.setValue(int(ng[1]))
        row = QWidget()
        rowl = QHBoxLayout(row)
        rowl.addWidget(self.lda_ng_min)
        rowl.addWidget(QLabel("to"))
        rowl.addWidget(self.lda_ng_max)
        f.addRow("ngram_range:", row)

        self.lda_random_state = QSpinBox()
        self.lda_random_state.setRange(0, 1000000)
        self.lda_random_state.setValue(int(c.get("random_state", 42)))
        f.addRow("random_state:", self.lda_random_state)

        self.lda_max_iter = QSpinBox()
        self.lda_max_iter.setRange(5, 200)
        self.lda_max_iter.setValue(int(c.get("max_iter", 15)))
        f.addRow("max_iter:", self.lda_max_iter)

        self.lda_learning = QComboBox()
        self.lda_learning.addItems(["batch", "online"])
        self.lda_learning.setCurrentText(str(c.get("learning_method", "batch")))
        f.addRow("learning_method:", self.lda_learning)

        return w

    # ----------------- KeyBERT -----------------
    def _make_keybert_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        c = self.cfg["keybert"]

        self.kb_model = QLineEdit(c.get("model_name", "all-MiniLM-L6-v2"))
        f.addRow("model_name:", self.kb_model)

        self.kb_topn = QSpinBox()
        self.kb_topn.setRange(3, 20)
        self.kb_topn.setValue(int(c.get("top_n", 5)))
        f.addRow("top_n:", self.kb_topn)

        return w

    # ----------------- Gemini -----------------
    def _make_gemini_tab(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        c = self.cfg["gemini"]

        self.gm_api = QLineEdit(c.get("api_key", ""))
        self.gm_api.setEchoMode(QLineEdit.PasswordEchoOnEdit)
        f.addRow("API key:", self.gm_api)

        self.gm_model = QLineEdit(c.get("model", "gemini-1.5-pro-latest"))
        f.addRow("model:", self.gm_model)

        self.gm_topn = QSpinBox()
        self.gm_topn.setRange(3, 20)
        self.gm_topn.setValue(int(c.get("top_n", 5)))
        f.addRow("top_n:", self.gm_topn)

        self.gm_max_words = QSpinBox()
        self.gm_max_words.setRange(200, 50000)
        self.gm_max_words.setSingleStep(100)
        self.gm_max_words.setValue(int(c.get("max_words", 1500)))
        f.addRow("max_words:", self.gm_max_words)

        return w

    # ----------------- Save -----------------
    def _save_and_close(self):
        # BERTopic
        self.cfg["bertopic"]["embedding_model"] = self.bt_embedding.text().strip() or "all-MiniLM-L6-v2"
        mode = self.bt_nr_topics_mode.currentText()
        if mode == "auto":
            self.cfg["bertopic"]["nr_topics"] = "auto"
        else:
            self.cfg["bertopic"]["nr_topics"] = int(self.bt_nr_topics.value())
        self.cfg["bertopic"]["min_topic_size"] = int(self.bt_min_topic_size.value())
        self.cfg["bertopic"]["top_n_words"] = int(self.bt_top_n_words.value())
        self.cfg["bertopic"]["vectorizer_max_df"] = float(self.bt_max_df.value())
        self.cfg["bertopic"]["vectorizer_min_df"] = int(self.bt_min_df.value())
        self.cfg["bertopic"]["ngram_range"] = (int(self.bt_ng_min.value()), int(self.bt_ng_max.value()))

        # LDA
        self.cfg["lda"]["n_topics"] = int(self.lda_topics.value())
        self.cfg["lda"]["max_features"] = int(self.lda_max_features.value())
        self.cfg["lda"]["top_n_words"] = int(self.lda_top_n_words.value())
        self.cfg["lda"]["min_df"] = int(self.lda_min_df.value())
        self.cfg["lda"]["max_df"] = float(self.lda_max_df.value())
        self.cfg["lda"]["ngram_range"] = (int(self.lda_ng_min.value()), int(self.lda_ng_max.value()))
        self.cfg["lda"]["random_state"] = int(self.lda_random_state.value())
        self.cfg["lda"]["max_iter"] = int(self.lda_max_iter.value())
        self.cfg["lda"]["learning_method"] = self.lda_learning.currentText()

        # KeyBERT
        self.cfg["keybert"]["model_name"] = self.kb_model.text().strip() or "all-MiniLM-L6-v2"
        self.cfg["keybert"]["top_n"] = int(self.kb_topn.value())

        # Gemini
        self.cfg["gemini"]["api_key"] = self.gm_api.text().strip()
        self.cfg["gemini"]["model"] = self.gm_model.text().strip() or "gemini-1.5-pro-latest"
        self.cfg["gemini"]["top_n"] = int(self.gm_topn.value())
        self.cfg["gemini"]["max_words"] = int(self.gm_max_words.value())

        save_config(self.cfg)
        self.accept()