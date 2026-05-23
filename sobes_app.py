# sobes_app.py
import json
import re
import sys
import os
import logging
from datetime import datetime

import certifi

# Fix SSL cert path when running as PyInstaller frozen bundle
if getattr(sys, 'frozen', False):
    # certifi.where() returns a non-existent path in PyInstaller;
    # use sys._MEIPASS to find the bundled cacert.pem
    ca_path = os.path.join(sys._MEIPASS, 'certifi', 'cacert.pem')
    os.environ['SSL_CERT_FILE'] = ca_path
    os.environ['REQUESTS_CA_BUNDLE'] = ca_path
    # Also patch certifi to return the correct path
    certifi.where = lambda: ca_path

import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfReader

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QComboBox, QPushButton, QTextEdit, QListWidget,
    QListWidgetItem, QMessageBox, QGroupBox, QFormLayout, QSplitter,
    QStatusBar, QFileDialog, QScrollArea,
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QPalette, QColor

from sobes_core.config import Config
from sobes_core.storage import SqliteStore
from sobes_core.session_runner import SessionRunner
from sobes_modules.preparation.service import PreparationService
from sobes_modules.audio.capturer import list_audio_devices

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sobes_app")

DARK_STYLE = """
QMainWindow, QWidget { background: #1e1e2e; color: #cdd6f4; }
QTabWidget::pane { border: 1px solid #313244; background: #1e1e2e; }
QTabBar::tab { background: #181825; color: #6c7086; padding: 8px 20px; border: none; }
QTabBar::tab:selected { background: #313244; color: #cdd6f4; border-bottom: 2px solid #a6e3a1; }
QLineEdit, QTextEdit, QComboBox {
    background: #11111b; color: #cdd6f4; border: 1px solid #313244;
    border-radius: 6px; padding: 6px; font-size: 13px;
}
QPushButton {
    background: #313244; color: #cdd6f4; border: none;
    border-radius: 6px; padding: 8px 16px; font-size: 13px;
}
QPushButton:hover { background: #45475a; }
QPushButton#startBtn { background: #a6e3a1; color: #1e1e2e; font-weight: bold; }
QPushButton#startBtn:hover { background: #94e2d5; }
QPushButton#stopBtn { background: #f38ba8; color: #1e1e2e; font-weight: bold; }
QPushButton#stopBtn:hover { background: #eba0ac; }
QGroupBox { border: 1px solid #313244; border-radius: 8px; margin-top: 12px;
             padding-top: 16px; color: #a6adc8; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 6px; }
QListWidget { background: #11111b; border: 1px solid #313244; border-radius: 6px; }
QListWidget::item { padding: 6px; border-bottom: 1px solid #1e1e2e; }
QListWidget::item:selected { background: #313244; }
QStatusBar { background: #181825; color: #6c7086; }
QLabel { color: #a6adc8; }
"""


class PrepareTab(QWidget):
    def __init__(self, prep_service: PreparationService, store: SqliteStore):
        super().__init__()
        self.prep = prep_service
        self.store = store
        self._profile = None
        self._scripts: list[dict] = []

        layout = QVBoxLayout(self)

        # Interview form
        form_group = QGroupBox("Информация о собеседовании")
        form = QFormLayout()
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Яндекс")
        self.role_input = QLineEdit()
        self.role_input.setPlaceholderText("Backend Developer")
        self.type_combo = QComboBox()
        self.type_combo.addItems(["tech", "hr", "final", "other"])
        form.addRow("Компания:", self.company_input)
        form.addRow("Должность:", self.role_input)
        form.addRow("Тип:", self.type_combo)

        # Vacancy URL + PDF
        vac_hl = QHBoxLayout()
        self.vacancy_url = QLineEdit()
        self.vacancy_url.setPlaceholderText("https://hh.ru/vacancy/...")
        self.load_pdf_btn = QPushButton("📄 Загрузить PDF")
        self.load_pdf_btn.clicked.connect(self._load_pdf)
        vac_hl.addWidget(self.vacancy_url)
        vac_hl.addWidget(self.load_pdf_btn)
        form.addRow("Вакансия (URL):", vac_hl)

        self.vacancy_text = QTextEdit()
        self.vacancy_text.setPlaceholderText("Текст вакансии (загрузите PDF или вставьте вручную)...")
        self.vacancy_text.setMaximumHeight(80)
        form.addRow("Текст вакансии:", self.vacancy_text)

        # Resume section
        res_hl = QHBoxLayout()
        self.resume_url = QLineEdit()
        self.resume_url.setPlaceholderText("https://hh.ru/resume/...")
        self.resume_pdf_btn = QPushButton("📄 Загрузить PDF резюме")
        self.resume_pdf_btn.clicked.connect(self._load_resume_pdf)
        res_hl.addWidget(self.resume_url)
        res_hl.addWidget(self.resume_pdf_btn)
        form.addRow("Резюме (URL):", res_hl)

        self.resume_text = QTextEdit()
        self.resume_text.setPlaceholderText("Текст резюме (загрузите PDF или вставьте вручную)...")
        self.resume_text.setMaximumHeight(80)
        form.addRow("Текст резюме:", self.resume_text)

        self.gathered_info = QTextEdit()
        self.gathered_info.setPlaceholderText("Что удалось узнать: контакты, требования, зарплата, детали...")
        self.gathered_info.setMaximumHeight(80)
        form.addRow("Собранная информация:", self.gathered_info)

        self.analyze_btn = QPushButton("🔍 Анализировать вакансию")
        self.analyze_btn.setStyleSheet(
            "background: #89b4fa; color: #1e1e2e; font-weight: bold;"
            "padding: 10px; font-size: 13px; border-radius: 6px;"
        )
        self.analyze_btn.clicked.connect(self._analyze_vacancy)
        form.addRow(self.analyze_btn)

        form_group.setLayout(form)
        layout.addWidget(form_group)

        # Scripts
        scripts_group = QGroupBox("Скрипты (заготовки ответов)")
        sl = QVBoxLayout()

        add_hl = QHBoxLayout()
        self.script_title = QLineEdit()
        self.script_title.setPlaceholderText("Название (пример: уход из компании)")
        self.script_tags = QLineEdit()
        self.script_tags.setPlaceholderText("Теги через запятую (уход, мотивация)")
        add_hl.addWidget(self.script_title)
        add_hl.addWidget(self.script_tags)
        sl.addLayout(add_hl)

        self.script_content = QTextEdit()
        self.script_content.setPlaceholderText("Текст скрипта...")
        self.script_content.setMaximumHeight(100)
        sl.addWidget(self.script_content)

        btn_hl = QHBoxLayout()
        add_btn = QPushButton("+ Добавить скрипт")
        add_btn.clicked.connect(self._add_script)
        load_btn = QPushButton("Загрузить из JSON")
        load_btn.clicked.connect(self._load_scripts)
        save_btn = QPushButton("Сохранить в JSON")
        save_btn.clicked.connect(self._save_scripts)
        btn_hl.addWidget(add_btn)
        btn_hl.addWidget(load_btn)
        btn_hl.addWidget(save_btn)
        sl.addLayout(btn_hl)

        self.scripts_list = QListWidget()
        sl.addWidget(self.scripts_list)

        scripts_group.setLayout(sl)
        layout.addWidget(scripts_group)

        # Create session button
        self.create_btn = QPushButton("Создать сессию и подготовиться")
        self.create_btn.setStyleSheet(
            "background: #a6e3a1; color: #1e1e2e; font-weight: bold;"
            "padding: 12px; font-size: 14px; border-radius: 8px;"
        )
        self.create_btn.clicked.connect(self._create_session)
        layout.addWidget(self.create_btn)

        layout.addStretch()

    def _add_script(self):
        title = self.script_title.text().strip()
        content = self.script_content.toPlainText().strip()
        tags = [t.strip() for t in self.script_tags.text().split(",") if t.strip()]
        if not title or not content:
            QMessageBox.warning(self, "Ошибка", "Название и текст скрипта обязательны")
            return
        self._scripts.append({"title": title, "content": content, "tags": tags})
        self.scripts_list.addItem(f"[{', '.join(tags)}] {title}")
        self.script_title.clear()
        self.script_content.clear()
        self.script_tags.clear()

    def _load_scripts(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить скрипты", "", "JSON (*.json)")
        if path:
            with open(path, "r", encoding="utf-8") as f:
                self._scripts = json.load(f)
            self._refresh_list()

    def _save_scripts(self):
        path, _ = QFileDialog.getSaveFileName(self, "Сохранить скрипты", "scripts.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._scripts, f, ensure_ascii=False, indent=2)

    def _load_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить PDF вакансии", "", "PDF (*.pdf)")
        if not path:
            return
        try:
            reader = PdfReader(path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
            self.vacancy_text.setText(text.strip())
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать PDF: {e}")

    def _load_resume_pdf(self):
        path, _ = QFileDialog.getOpenFileName(self, "Загрузить PDF резюме", "", "PDF (*.pdf)")
        if not path:
            return
        try:
            reader = PdfReader(path)
            text = "\n".join(p.extract_text() or "" for p in reader.pages)
            self.resume_text.setText(text.strip())
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось прочитать PDF: {e}")

    def _analyze_vacancy(self):
        text = self.vacancy_text.toPlainText().strip()
        url = self.vacancy_url.text().strip()
        extracted = {}

        if url and not text:
            soup = None
            for attempt in range(2):
                try:
                    kwargs = {
                        "url": url,
                        "timeout": 15,
                        "headers": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    }
                    if attempt == 1:
                        kwargs["verify"] = False
                    resp = requests.get(**kwargs)
                    resp.raise_for_status()
                    soup = BeautifulSoup(resp.text, "html.parser")
                    break
                except requests.exceptions.SSLError as e:
                    if attempt == 0:
                        logger.warning("SSL failed, retrying without verification")
                        continue
                    logger.warning(f"SSL error after retry: {e}")
                except Exception as e:
                    logger.warning(f"Failed to fetch URL: {e}")
                    break

            if soup is None:
                QMessageBox.warning(self, "Ошибка", f"Не удалось загрузить URL: {url}")
                return

            # 1. JSON-LD structured data (most reliable)
            extracted = self._parse_jsonld(soup)

            # 2. hh.ru data-qa attributes
            self._parse_hhru(soup, extracted)

            # 3. Meta tags (og:title, description)
            self._parse_meta(soup, extracted)

            # 4. Build clean text from vacancy description only
            desc_div = soup.find(attrs={"data-qa": "vacancy-description"})
            if desc_div:
                text = desc_div.get_text(separator="\n")
            else:
                for junk in soup.select("footer, nav, header, script, style, .similar-vacancies"):
                    if junk:
                        junk.decompose()
                text = soup.get_text(separator="\n")

            lines = [l.strip() for l in text.splitlines() if l.strip()]
            text = "\n".join(lines)
            self.vacancy_text.setText(text[:5000])

        if not text:
            QMessageBox.warning(self, "Ошибка", "Добавьте ссылку или текст вакансии для анализа")
            return

        # Fill fields: prefer structured data, fall back to regex
        company = self.company_input.text().strip() or extracted.get("company", "")
        if not company:
            company = self._extract_company(text)

        role = self.role_input.text().strip() or extracted.get("role", "")
        if not role:
            role = self._extract_role(text)

        itype = self._detect_type(text)

        extra = extracted.get("extra", "")
        if not extra:
            extra = self._extract_extra(text)

        if company:
            self.company_input.setText(company)
        if role:
            self.role_input.setText(role)
        if itype:
            idx = self.type_combo.findText(itype)
            if idx >= 0:
                self.type_combo.setCurrentIndex(idx)

        current_info = self.gathered_info.toPlainText().strip()
        if extra and not current_info:
            self.gathered_info.setText(extra)

        filled = []
        if company: filled.append(f"Компания: {company}")
        if role: filled.append(f"Должность: {role}")
        if itype: filled.append(f"Тип: {itype}")
        QMessageBox.information(
            self, "Анализ завершён",
            "Заполнено:\n" + "\n".join(filled) if filled else "Ничего не найдено"
        )

    def _parse_jsonld(self, soup) -> dict:
        result = {}
        for ld in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(ld.string)
            except (json.JSONDecodeError, AttributeError):
                continue
            if data.get("@type") != "JobPosting":
                continue
            if data.get("title"):
                result["role"] = data["title"]
            org = data.get("hiringOrganization")
            if isinstance(org, dict):
                result["company"] = org.get("name", "")
            elif isinstance(org, str):
                result["company"] = org
            if data.get("description"):
                result["desc"] = BeautifulSoup(data["description"], "html.parser").get_text()
        return result

    def _parse_hhru(self, soup, extracted: dict) -> None:
        el = soup.find(attrs={"data-qa": "vacancy-company-name"})
        if el and not extracted.get("company"):
            extracted["company"] = el.get_text(strip=True)

        el = soup.find(attrs={"data-qa": "vacancy-title"})
        if el and not extracted.get("role"):
            extracted["role"] = el.get_text(strip=True)

        parts = []
        el = soup.find(attrs={"data-qa": "vacancy-experience"})
        if el:
            parts.append(f"Опыт: {el.get_text(strip=True)}")
        el = soup.find(attrs={"data-qa": "vacancy-view-raw-address"})
        if el:
            parts.append(f"Адрес: {el.get_text(strip=True)}")
        if parts:
            extracted["extra"] = "\n".join(parts)

    def _parse_meta(self, soup, extracted: dict) -> None:
        og = soup.find("meta", property="og:title")
        if og and og.get("content"):
            t = og["content"]
            if not extracted.get("role"):
                m = re.match(r"Вакансия\s+(.+?)(?:\s+в\s+|\s*—\s*)", t)
                if m:
                    extracted["role"] = m.group(1).strip()
            if not extracted.get("company"):
                m = re.search(r"в\s+(.+?)(?:\s*—|\s*$)", t)
                if m:
                    extracted["company"] = m.group(1).strip()

        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content") and not extracted.get("company"):
            m = re.search(r"(?:компани[ия]|работодател[ья])\s*[—:\s]+(.+?)(?:\.|,|$)",
                          meta["content"], re.IGNORECASE)
            if m:
                extracted["company"] = m.group(1).strip()

    def _extract_company(self, text: str) -> str:
        patterns = [
            r"Компания[:\s—]+(.+?)(?:\n|$)",
            r"О компании\s*[«\"](.+?)[»\"]",
            r"в компани[юи]\s*[«\"](.+?)[»\"]",
            r"работ[ае]\s+в\s+[«\"](.+?)[»\"]",
            r"Вакансия\s+(?:.+\s+)?(?:в|от)\s+[«\"](.+?)[»\"]",
            r"(?:Яндекс|VK|Ozon|WB|Wildberries|Сбер|Тинькофф|Avito|Ozon|МТС|Билайн|Мегафон|Lamoda|Касперский|Positive Technologies)",
            r"(?:Google|Apple|Microsoft|Amazon|Meta|Netflix|Spotify|Uber|Airbnb|Stripe|GitHub|GitLab)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                return m.group(1).strip() if m.lastindex else m.group(0).strip()
        return ""

    def _extract_role(self, text: str) -> str:
        patterns = [
            r"(?:Должность|Позиция|Role)[:\s—]+(.+?)(?:\n|$)",
            r"Вакансия[:\s]+(.+?)(?:\n|,|в|\()",
            r"(?i)(Senior|Middle|Junior|Lead|Staff|Principal)?\s*(Python|Java|Go|C\+\+|C#|Rust|JavaScript|TypeScript|Ruby|PHP|Kotlin|Swift|Scala)\s*(?:Developer|Engineer|Programmer|разработчик|программист)",
            r"(?i)(Frontend|Front-end|Backend|Back-end|Fullstack|Full-stack|DevOps|ML|Machine Learning|Data\s+Scientist|Data\s+Engineer|QA|SDET|SRE|System\s+Administrator|Product\s+Manager|Project\s+Manager|Team\s+Lead|Tech\s+Lead|Architect|Analyst|Designer)",
            r"(?i)(разработчик|программист|инженер|аналитик|дизайнер|тестировщик|менеджер|руководитель|архитектор)[а-я]*\s*(?:по\s+)?(.+?)(?:\n|,|$)",
            r"(?i)(\w+(?:\s+\w+){0,3})\s*\((?:\w+\s+)?(?:Developer|Engineer)\)",
        ]
        for p in patterns:
            m = re.search(p, text, re.IGNORECASE)
            if m:
                if m.lastindex and m.lastindex >= 1:
                    parts = [g for g in m.groups() if g]
                    return " ".join(parts).strip()
                return m.group(0).strip()
        return ""

    def _detect_type(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["техническ", "tech", "technical", "алгоритм", "coding", "кодинг"]):
            return "tech"
        if any(w in text_lower for w in ["hr", "эйчар", "рекрутер", "soft skills", "софт скиллы", "знакомство"]):
            return "hr"
        if any(w in text_lower for w in ["финальн", "final", "последн", "заключитель"]):
            return "final"
        if any(w in text_lower for w in ["скрининг", "screening", "первичн"]):
            return "other"
        return ""

    def _extract_extra(self, text: str) -> str:
        found = []
        # Salary
        m = re.search(r"(?i)(?:зарплата|оклад|salary|compensation|до\s+\d+[kк]?\s*(?:rub|руб|₽)?)[:\s—]*([\d\s–\-kкrubруб₽$€]+)", text)
        if m:
            found.append(f"💰 Зарплата: {m.group(1).strip()}")
        # Stack
        m = re.search(r"(?i)(?:стек|технологии|stack)[:\s—]+(.+?)(?:\n\n|\n[А-ЯA-Z])", text)
        if m:
            found.append(f"🔧 Стек: {m.group(1).strip()[:200]}")
        # Requirements
        m = re.search(r"(?i)(?:требования|requirements|ты будешь|ожида[ею]м)[:\s—]*(.+?)(?:\n\n|\n[А-ЯA-Z]|\Z)", text, re.DOTALL)
        if m:
            req = m.group(1).strip()[:500]
            found.append(f"📋 Требования:\n{req}")
        # Format
        m = re.search(r"(?i)(?:формат|format|офис|удал[её]н|гибрид|office|remote|hybrid)[:\s—]*(.+?)(?:\n|$)", text)
        if m:
            found.append(f"🏢 Формат: {m.group(1).strip()}")
        return "\n\n".join(found)

    def _refresh_list(self):
        self.scripts_list.clear()
        for s in self._scripts:
            tags = ", ".join(s.get("tags", []))
            self.scripts_list.addItem(f"[{tags}] {s['title']}")

    def _create_session(self):
        company = self.company_input.text().strip()
        role = self.role_input.text().strip()
        itype = self.type_combo.currentText()
        if not company or not role:
            QMessageBox.warning(self, "Ошибка", "Компания и должность обязательны")
            return

        profile = self.prep.create_session_profile(
            company, role, itype,
            vacancy_url=self.vacancy_url.text().strip(),
            vacancy_text=self.vacancy_text.toPlainText().strip(),
            gathered_info=self.gathered_info.toPlainText().strip(),
            resume_url=self.resume_url.text().strip(),
            resume_text=self.resume_text.toPlainText().strip(),
        )
        for s in self._scripts:
            self.prep.add_script(
                session_id=profile["id"],
                title=s["title"],
                content=s["content"],
                tags=s.get("tags", [])
            )
        self.prep.index_scripts(profile["id"])

        # Run combined vacancy + resume analysis
        analysis = self.prep.run_combined_analysis(profile["id"])

        report = self.prep.get_readiness_report(profile["id"])

        self._profile = profile

        QMessageBox.information(
            self, "Готово",
            f"Сессия создана: {profile['id']}\n"
            f"Скриптов: {report['scripts_count']}\n"
            f"Статус: {report['status']}"
            + (f"\nАнализ: выполнен" if analysis else "")
        )

    def get_profile(self):
        return self._profile


class LiveTab(QWidget):
    status_signal = Signal(str)

    def __init__(self, runner: SessionRunner, store: SqliteStore,
                 prep_service=None):
        super().__init__()
        self.runner = runner
        self.store = store
        self.prep = prep_service
        self._overlay_timer = QTimer()

        self.status_signal.connect(self._update_status_label)

        # Wrap in scroll area to fit all sections
        outer = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)

        # Status
        status_group = QGroupBox("Статус")
        sl = QVBoxLayout()
        self.status_label = QLabel("Не запущено")
        self.status_label.setStyleSheet("color: #6c7086; font-size: 14px;")
        sl.addWidget(self.status_label)
        status_group.setLayout(sl)
        layout.addWidget(status_group)

        # Device info
        dev_group = QGroupBox("Аудио-устройство")
        dl = QVBoxLayout()
        self.device_combo = QComboBox()
        self._refresh_devices()
        refresh_dev_btn = QPushButton("Обновить список")
        refresh_dev_btn.clicked.connect(self._refresh_devices)
        dl.addWidget(self.device_combo)
        dl.addWidget(refresh_dev_btn)
        dev_group.setLayout(dl)
        layout.addWidget(dev_group)

        # Controls
        ctrl_hl = QHBoxLayout()
        self.start_btn = QPushButton("▶ Начать сессию")
        self.start_btn.setObjectName("startBtn")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)
        ctrl_hl.addWidget(self.start_btn)
        ctrl_hl.addWidget(self.stop_btn)
        layout.addLayout(ctrl_hl)

        # Transcript preview
        transcript_group = QGroupBox("Транскрипт (последние строки)")
        tl = QVBoxLayout()
        self.transcript_view = QTextEdit()
        self.transcript_view.setReadOnly(True)
        self.transcript_view.setMaximumHeight(150)
        tl.addWidget(self.transcript_view)
        transcript_group.setLayout(tl)
        layout.addWidget(transcript_group)

        # Analysis display
        self.analysis_group = QGroupBox("Анализ собеседования")
        al = QVBoxLayout()

        al.addWidget(QLabel("Самопрезентация:"))
        self.self_presentation_text = QTextEdit()
        self.self_presentation_text.setReadOnly(True)
        self.self_presentation_text.setMaximumHeight(120)
        al.addWidget(self.self_presentation_text)

        al.addWidget(QLabel("Ответы на предполагаемые вопросы:"))
        self.anticipated_questions_text = QTextEdit()
        self.anticipated_questions_text.setReadOnly(True)
        self.anticipated_questions_text.setMaximumHeight(150)
        al.addWidget(self.anticipated_questions_text)

        al.addWidget(QLabel("Рекомендации по зарплате:"))
        self.salary_recommendation_text = QTextEdit()
        self.salary_recommendation_text.setReadOnly(True)
        self.salary_recommendation_text.setMaximumHeight(80)
        al.addWidget(self.salary_recommendation_text)

        al.addWidget(QLabel("Что спрашивать у работодателя:"))
        self.employer_questions_text = QTextEdit()
        self.employer_questions_text.setReadOnly(True)
        self.employer_questions_text.setMaximumHeight(100)
        al.addWidget(self.employer_questions_text)

        self.analysis_group.setLayout(al)
        self.analysis_group.setVisible(False)
        layout.addWidget(self.analysis_group)

        layout.addStretch()
        scroll.setWidget(scroll_widget)
        outer.addWidget(scroll)

        runner.set_status_callback(self._on_status)

    def _refresh_devices(self):
        self.device_combo.clear()
        for d in list_audio_devices():
            if d["max_input_channels"] > 0:
                label = f"[{d['index']}] {d['name']}"
                self.device_combo.addItem(label, d["index"])

    def _start(self):
        if self.device_combo.currentData() is not None:
            self.runner.cfg.audio_device_index = self.device_combo.currentData()
        try:
            self.runner.initialize_modules()
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось инициализировать: {e}")
            return
        self.runner.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._overlay_timer.timeout.connect(self._update_transcript)
        self._overlay_timer.start(1000)

    def _stop(self):
        self.runner.stop()
        self._overlay_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("Остановлено")
        self.status_label.setStyleSheet("color: #f38ba8; font-size: 14px;")

    def _on_status(self, msg: str):
        self.status_signal.emit(msg)

    def _update_status_label(self, msg: str):
        self.status_label.setText(msg)

    def _update_transcript(self):
        lines = self.runner._transcript[-20:]
        text = "\n".join(
            f"[{e['timestamp']}] {e['speaker']}: {e['text']}"
            for e in lines
        )
        self.transcript_view.setText(text)

    def display_analysis(self, analysis: dict):
        if not analysis:
            self.analysis_group.setVisible(False)
            return

        self.analysis_group.setVisible(True)

        # Self-presentation
        self.self_presentation_text.setText(
            analysis.get("self_presentation", "Нет данных")
        )

        # Anticipated questions
        questions = analysis.get("anticipated_questions", [])
        if questions:
            q_text = ""
            for i, qa in enumerate(questions, 1):
                q_text += f"{i}. Вопрос: {qa.get('question', '')}\n"
                q_text += f"   Ответ: {qa.get('suggested_answer', '')}\n\n"
            self.anticipated_questions_text.setText(q_text.strip())
        else:
            self.anticipated_questions_text.setText("Нет данных")

        # Salary recommendation
        self.salary_recommendation_text.setText(
            analysis.get("salary_recommendation", "Нет данных")
        )

        # Employer questions
        eq_list = analysis.get("employer_questions", [])
        if eq_list:
            self.employer_questions_text.setText(
                "\n".join(f"• {q}" for q in eq_list)
            )
        else:
            self.employer_questions_text.setText("Нет данных")


class ReportsTab(QWidget):
    def __init__(self, store: SqliteStore):
        super().__init__()
        self.store = store

        layout = QVBoxLayout(self)

        hl = QHBoxLayout()
        self.company_filter = QLineEdit()
        self.company_filter.setPlaceholderText("Фильтр по компании...")
        self.company_filter.textChanged.connect(self._refresh)
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self._refresh)
        hl.addWidget(self.company_filter)
        hl.addWidget(refresh_btn)
        layout.addLayout(hl)

        self.sessions_list = QListWidget()
        self.sessions_list.itemClicked.connect(self._show_detail)
        layout.addWidget(self.sessions_list)

        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setMaximumHeight(200)
        layout.addWidget(self.detail_view)

        self._refresh()

    def _refresh(self):
        self.sessions_list.clear()
        company = self.company_filter.text().strip() or None
        sessions = self.store.list_sessions(company=company)
        for s in sessions:
            self.sessions_list.addItem(f"[{s.id}] {s.company} — {s.role} ({s.interview_type}) {s.started_at[:10]}")

    def _show_detail(self, item: QListWidgetItem):
        sid = int(item.text().split("]")[0].strip("["))
        session = self.store.get_session(sid)
        if session:
            self.detail_view.setText(
                f"Компания: {session.company}\n"
                f"Роль: {session.role}\n"
                f"Тип: {session.interview_type}\n"
                f"Начало: {session.started_at}\n"
                f"Конец: {session.ended_at}\n"
                f"Статистика: {session.stats}\n\n"
                f"Транскрипт:\n{session.transcript[:500]}..."
            )


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sobes — Interview Assistant")
        self.setMinimumSize(720, 800)
        self.setStyleSheet(DARK_STYLE)

        self.cfg = Config()
        self.store = SqliteStore(self.cfg.sqlite_path)
        self.store.initialize()
        self.prep = PreparationService(self.cfg, self.store)

        # Initialize analysis backend
        if self.cfg.llm_provider == "template":
            from sobes_modules.preparation.analyzer import TemplateAnalysisBackend
            self.prep.set_analyzer(TemplateAnalysisBackend())

        self.runner = SessionRunner(self.cfg, self.store, prep_service=self.prep)

        self.tabs = QTabWidget()
        self.prepare_tab = PrepareTab(self.prep, self.store)
        self.live_tab = LiveTab(self.runner, self.store, prep_service=self.prep)
        self.reports_tab = ReportsTab(self.store)

        self.tabs.addTab(self.prepare_tab, "📋 Подготовка")
        self.tabs.addTab(self.live_tab, "🎙️ Сессия")
        self.tabs.addTab(self.reports_tab, "📊 Отчёты")

        self.setCentralWidget(self.tabs)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов")

        # Wire prepare → live: when user switches to Live tab, auto-load session
        self.tabs.currentChanged.connect(self._on_tab_changed)

    def _on_tab_changed(self, index):
        if index == 1:  # Live tab
            profile = self.prepare_tab.get_profile()
            if profile:
                self.runner.load_session(profile["id"])
                self.status_bar.showMessage(f"Session loaded: {profile['id']}")

                # Load and display analysis
                analysis = self.prep.get_analysis(profile["id"])
                if analysis:
                    self.live_tab.display_analysis(analysis)
                else:
                    # Try to run analysis if not yet done
                    analysis = self.prep.run_combined_analysis(profile["id"])
                    if analysis:
                        self.live_tab.display_analysis(analysis)


def main():
    app = QApplication(sys.argv)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor("#1e1e2e"))
    app.setPalette(palette)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
