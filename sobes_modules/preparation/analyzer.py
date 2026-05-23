# sobes_modules/preparation/analyzer.py
"""Combined vacancy + resume analysis for interview preparation."""
import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

TECH_KEYWORDS = [
    # Languages (word-boundary for short names to avoid substring matches)
    (r"\bPython\b", "Python"),
    (r"\bJava\b(?!\s*Script)", "Java"),
    (r"\bGo\b", "Go"),
    (r"\bRust\b", "Rust"),
    (r"\bC\#", "C#"),
    (r"\bC\+\+", "C++"),
    (r"\bJavaScript\b", "JavaScript"),
    (r"\bTypeScript\b", "TypeScript"),
    (r"\bKotlin\b", "Kotlin"),
    (r"\bSwift\b", "Swift"),
    (r"\bScala\b", "Scala"),
    (r"\bPHP\b", "PHP"),
    (r"\bRuby\b", "Ruby"),
    (r"\bR\b", "R"),
    (r"\bMATLAB\b", "MATLAB"),
    # Frameworks
    (r"\bDjango\b", "Django"),
    (r"\bFlask\b", "Flask"),
    (r"\bFastAPI\b", "FastAPI"),
    (r"\bSpring\b", "Spring"),
    (r"\bExpress\b", "Express"),
    (r"\bReact\b", "React"),
    (r"\bVue\b", "Vue"),
    (r"\bAngular\b", "Angular"),
    (r"\bSvelte\b", "Svelte"),
    (r"\bNext\.js\b", "Next.js"),
    (r"\bNuxt\b", "Nuxt"),
    (r"\bASP\.NET\b", "ASP.NET"),
    # Databases
    (r"\bPostgreSQL\b", "PostgreSQL"),
    (r"\bMySQL\b", "MySQL"),
    (r"\bMongoDB\b", "MongoDB"),
    (r"\bRedis\b", "Redis"),
    (r"\bElasticsearch\b", "Elasticsearch"),
    (r"\bCassandra\b", "Cassandra"),
    (r"\bClickHouse\b", "ClickHouse"),
    (r"\bOracle\b", "Oracle"),
    (r"\bSQLite\b", "SQLite"),
    (r"\bDynamoDB\b", "DynamoDB"),
    (r"\bMS\s+SQL\b", "MS SQL"),
    # Infrastructure
    (r"\bDocker\b", "Docker"),
    (r"\bKubernetes\b", "Kubernetes"),
    (r"\bHelm\b", "Helm"),
    (r"\bTerraform\b", "Terraform"),
    (r"\bAnsible\b", "Ansible"),
    (r"\bJenkins\b", "Jenkins"),
    (r"\bGitLab\s+CI\b", "GitLab CI"),
    (r"\bGitHub\s+Actions\b", "GitHub Actions"),
    (r"\bArgoCD\b", "ArgoCD"),
    (r"\bPrometheus\b", "Prometheus"),
    (r"\bGrafana\b", "Grafana"),
    # Messaging / integration
    (r"\bKafka\b", "Kafka"),
    (r"\bRabbitMQ\b", "RabbitMQ"),
    (r"\bNATS\b", "NATS"),
    (r"\bgRPC\b", "gRPC"),
    (r"\bGraphQL\b", "GraphQL"),
    (r"\bREST\b", "REST"),
    # Cloud
    (r"\bAWS\b", "AWS"),
    (r"\bGCP\b", "GCP"),
    (r"\bAzure\b", "Azure"),
    (r"\bYandex\s+Cloud\b", "Yandex Cloud"),
    (r"\bS3\b", "S3"),
    (r"\bEC2\b", "EC2"),
    (r"\bLambda\b", "Lambda"),
    # General
    (r"\bLinux\b", "Linux"),
    (r"\bBash\b", "Bash"),
    (r"\bNginx\b", "Nginx"),
    (r"\bGit\b", "Git"),
    # ML / Data
    (r"\bPyTorch\b", "PyTorch"),
    (r"\bTensorFlow\b", "TensorFlow"),
    (r"\bKeras\b", "Keras"),
    (r"\bPandas\b", "Pandas"),
    (r"\bNumPy\b", "NumPy"),
    (r"\bScikit-learn\b", "Scikit-learn"),
    # Russian tech terms
    (r"\bмикросервис", "микросервисы"),
    (r"\bhigh-?load", "highload"),
    (r"\bвысоконагруж", "highload"),
    (r"\bраспредел[её]н", "распределённые системы"),
    # Methodologies
    (r"\bAgile\b", "Agile"),
    (r"\bScrum\b", "Scrum"),
    (r"\bKanban\b", "Kanban"),
    (r"\bCI/CD\b", "CI/CD"),
    (r"\bDevOps\b", "DevOps"),
    (r"\bFigma\b", "Figma"),
    (r"\bJira\b", "Jira"),
    (r"\bConfluence\b", "Confluence"),
]

EXPERIENCE_PATTERNS = [
    r"(?:опыт|experience).*?(\d+)[\s-]*(?:год|лет|года|year|yrs?)",
    r"(\d+)[\s-]*(?:год|лет|года|year|yrs?)\s+(?:опыта|experience)",
    r"(?:стаж|seniority)[:\s]+(\d+)[\s-]*(?:год|лет|года|year)",
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|опыт)",
]

EDUCATION_PATTERNS = [
    r"(?:образование|education|университет|university|вуз|институт|факультет|окончил|закончил)[:\s]+(.+?)(?:\n|$|\.)",
    r"(?:бакалавр|магистр|bachelor|master|phd|кандидат|доктор|MBA)[а-я]*\s+(.+?)(?:\n|$|\.)",
    r"(.+?)\s+(?:университет|university|институт)",
]

ACHIEVEMENT_PATTERNS = [
    r"(?:достижени[ея]|achievement|результат|увеличил|сократил|внедрил|разработал|improved|reduced|implemented|optimized|migrated|built|led|managed|создал|запустил|автоматизировал|ускорил|оптимизировал|мигрировал)",
]

SALARY_PATTERNS = [
    r"(?i)(?:зарплата|оклад|salary|доход|compensation|от\s+\d+)\s*[:\s—]*.*?(\d[\d\s]*[kк]?\s*(?:rub|руб|₽|\$|€)?)[\s—]*[-–до]+\s*(\d[\d\s]*[kк]?\s*(?:rub|руб|₽|\$|€)?)",
    r"(?i)(?:зарплата|оклад|salary).*?(\d[\d\s]*)\s*(?:000|k|к|тыс)",
    r"(?i)до\s+(\d[\d\s]*[kк]?)\s*(?:rub|руб|₽)",
]

RED_FLAG_PATTERNS = [
    (r"(?:ненормирован|сверхуроч|overtime|переработк)", "переработки"),
    (r"(?:режим\s+стартапа|startup\s+mode|быстро\s+меняющ)", "режим стартапа"),
    (r"(?:многозадачность|multitasking)", "многозадачность"),
    (r"(?:стрессоустойчивость|stress\s+resistance)", "стрессоустойчивость"),
    (r"(?:горящие\s+сроки|tight\s+deadlines)", "горящие сроки"),
    (r"(?:работа\s+на\s+результат)", "работа на результат любой ценой"),
]

MARKET_SALARY = {
    "junior": {"range": "80 000 - 150 000 руб.", "negotiation": "Акцент на потенциал роста и желание развиваться в стеке компании."},
    "middle": {"range": "150 000 - 300 000 руб.", "negotiation": "Опирайтесь на конкретные достижения и самостоятельно реализованные проекты."},
    "senior": {"range": "300 000 - 500 000 руб.", "negotiation": "Подчеркните влияние на продукт, менторство и архитектурные решения."},
    "lead": {"range": "400 000 - 700 000+ руб.", "negotiation": "Обсуждайте полный пакет: командные результаты, стратегическое влияние, опционы."},
    "unknown": {"range": "150 000 - 350 000 руб.", "negotiation": "Изучите рынок схожих позиций и уточните бюджет на первом контакте."},
}


@dataclass
class AnalysisResult:
    self_presentation: str = ""
    anticipated_questions: list[dict] = field(default_factory=list)
    salary_recommendation: str = ""
    employer_questions: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["created_at"] = self.created_at or datetime.now().isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AnalysisResult":
        return cls(
            self_presentation=d.get("self_presentation", ""),
            anticipated_questions=d.get("anticipated_questions", []),
            salary_recommendation=d.get("salary_recommendation", ""),
            employer_questions=d.get("employer_questions", []),
            raw=d.get("raw", {}),
            created_at=d.get("created_at", ""),
        )


class TemplateAnalysisBackend:
    """Produces interview analysis from regex + keyword matching."""

    def analyze(self, vacancy_text: str = "", resume_text: str = "",
                company: str = "", role: str = "", gathered_info: str = "",
                interview_type: str = "tech") -> AnalysisResult:
        all_text = vacancy_text + " " + resume_text + " " + gathered_info
        vac_tech = self._extract_technologies(vacancy_text)
        res_tech = self._extract_technologies(resume_text + " " + gathered_info)
        all_tech = vac_tech | res_tech
        years = self._extract_experience_years(resume_text)
        education = self._extract_education(resume_text)
        achievements = self._extract_achievements(resume_text)
        salary = self._extract_salary(vacancy_text)
        level = self._detect_role_level(role + " " + vacancy_text)
        gaps = sorted(t for t in vac_tech if t not in res_tech)
        matching = vac_tech & res_tech
        red_flags = self._detect_red_flags(vacancy_text)
        name = self._extract_name(resume_text, gathered_info)
        # Extract analysis content from gathered_info if present
        gi_analysis = self._parse_gathered_analysis(gathered_info)

        return AnalysisResult(
            self_presentation=self._build_self_presentation(
                company, role, years, all_tech, matching, gaps,
                education, achievements, resume_text, gathered_info,
                name, gi_analysis),
            anticipated_questions=self._build_questions(
                role, interview_type, vac_tech, res_tech, gaps, matching,
                years, education, achievements, gathered_info),
            salary_recommendation=self._build_salary_recommendation(
                years, level, salary, role),
            employer_questions=self._build_employer_questions(
                vac_tech, matching, red_flags, vacancy_text, company),
            raw={"backend": "template"},
            created_at=datetime.now().isoformat(),
        )

    # ---- extractors ----

    def _extract_technologies(self, text: str) -> set[str]:
        found = set()
        for pattern, name in TECH_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                found.add(name)
        return found

    def _extract_experience_years(self, text: str) -> int:
        for pat in EXPERIENCE_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return int(m.group(1))
        return 0

    def _extract_education(self, text: str) -> str:
        for pat in EDUCATION_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m:
                return m.group(1).strip()
        return ""

    def _extract_achievements(self, text: str) -> list[str]:
        results = []
        lines = text.split("\n")
        for pat in ACHIEVEMENT_PATTERNS:
            for line in lines:
                if re.search(pat, line, re.IGNORECASE):
                    # Strip leading markers, numbers, and common labels like "Достижения:"
                    clean = re.sub(r"^[•\-\s\d.]+\s*", "", line.strip())
                    clean = re.sub(r"^(?:достижени[ея]|achievements?)\s*:\s*", "", clean, flags=re.IGNORECASE).strip()
                    # Split on comma/semicolon if multiple achievements in one line
                    parts = [p.strip() for p in re.split(r"\s*[,;]\s*(?=[а-яa-z])", clean, flags=re.IGNORECASE) if p.strip()]
                    for part in parts:
                        if part and part not in results:
                            results.append(part)
        return results[:5]

    def _extract_salary(self, text: str) -> str:
        for pat in SALARY_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m and m.lastindex and m.lastindex >= 2:
                return f"{m.group(1).strip()} - {m.group(2).strip()}"
            elif m:
                return m.group(0).strip()[:80]
        return ""

    def _extract_name(self, resume_text: str, gathered_info: str = "") -> str:
        """Extract candidate name from resume or gathered_info."""
        combined = resume_text + "\n" + gathered_info
        # Try common Russian name patterns (Фамилия Имя Отчество or Имя Фамилия)
        name_patterns = [
            # First line of resume often contains name
            r"^([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
            # Labeled: "Имя: ..." or "ФИО: ..."
            r"(?:Имя|ФИО|Ф\.И\.О\.?|Name)[:\s]+\s*([А-ЯЁ][а-яё]+\s+[А-ЯЁ][а-яё]+(?:\s+[А-ЯЁ][а-яё]+)?)",
            # Labeled in English
            r"(?:Name|Full\s+Name)[:\s]+\s*([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        for pat in name_patterns:
            m = re.search(pat, combined, re.MULTILINE)
            if m:
                name = m.group(1).strip()
                if len(name) > 5 and len(name) < 60:
                    return name
        return ""

    def _parse_gathered_analysis(self, gathered_info: str) -> dict:
        """Try to extract structured analysis sections from gathered_info text."""
        if not gathered_info or len(gathered_info.strip()) < 50:
            return {}
        result = {}
        # Detect if gathered_info looks like analysis (has section headers)
        section_map = {
            "самопрезентация": "self_presentation",
            "self.presentation": "self_presentation",
            "self_presentation": "self_presentation",
            "презентация": "self_presentation",
            "вопросы": "questions",
            "questions": "questions",
            "anticipated": "questions",
            "зарплат": "salary",
            "salary": "salary",
            "работодател": "employer_questions",
            "employer": "employer_questions",
            "спросить": "employer_questions",
        }
        lines = gathered_info.split("\n")
        current_section = None
        buffer = []
        for line in lines:
            lower = line.strip().lower()
            matched = None
            for key, section in section_map.items():
                if key in lower and (line.startswith("#") or line.startswith("**") or ":" in line):
                    matched = section
                    break
            if matched:
                if current_section and buffer:
                    result[current_section] = "\n".join(buffer).strip()
                current_section = matched
                buffer = []
            elif current_section:
                buffer.append(line)
        if current_section and buffer:
            result[current_section] = "\n".join(buffer).strip()
        # If no structured sections found, treat the whole thing as self_presentation hint
        if not result and len(gathered_info.strip()) > 30:
            result["_raw"] = gathered_info.strip()
        return result

    def _detect_role_level(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["lead", "team lead", "тимлид", "руководитель", "principal", "staff", "ведущий"]):
            return "lead"
        if any(w in text_lower for w in ["senior", "старший", "сеньор", "сеньёр"]):
            return "senior"
        if any(w in text_lower for w in ["middle", "мидл", "миддл"]):
            return "middle"
        if any(w in text_lower for w in ["junior", "джуниор", "младший", "стажёр", "стажер"]):
            return "junior"
        return "unknown"

    def _detect_red_flags(self, text: str) -> list[str]:
        found = []
        for pat, label in RED_FLAG_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                found.append(label)
        return found

    # ---- builders ----

    def _build_self_presentation(self, company: str, role: str, years: int,
                                  all_tech: set, matching: set, gaps: list[str],
                                  education: str, achievements: list[str],
                                  resume_text: str, gathered_info: str,
                                  name: str, gi_analysis: dict) -> str:
        lines = []

        # -- Greeting with name --
        lines.append("## Самопрезентация\n")
        if name:
            lines.append(f"Здравствуйте! Меня зовут **{name}**.")
        else:
            lines.append("Здравствуйте! Меня зовут [Имя].")

        # -- Experience-led intro --
        if years >= 5:
            lines.append(f"\nЯ разработчик с **{years} годами** коммерческого опыта.")
            if role:
                lines.append(f"Рассматриваю позицию **{role}**" + (f" в компании **{company}**." if company else "."))
        elif years >= 2:
            lines.append(f"\nЯ разработчик с **{years} годами** опыта.")
            if role:
                lines.append(f"Заинтересован(а) в позиции **{role}**" + (f" в **{company}**." if company else "."))
        elif years > 0:
            lines.append(f"\nУ меня **{years} год** опыта в разработке, ищу возможности для роста на позиции **{role}**." + (f" в **{company}**." if company else "."))
        else:
            lines.append(f"\nЯ специализируюсь на разработке и заинтересован(а) в позиции **{role}**." + (f" в **{company}**." if company else "."))

        # ---- CORE CONTENT: prefer gathered_info analysis, fall back to template ----
        gi_pres = gi_analysis.get("self_presentation", "")
        gi_raw = gi_analysis.get("_raw", "")
        has_gi_content = bool(gi_pres or gi_raw)

        if has_gi_content:
            # Use user's own analysis as the primary content
            lines.append("")
            content = gi_pres if gi_pres else gi_raw
            lines.append(content)
        else:
            # -- Template-based content --
            # Skills block
            lines.append("")
            lines.append("### Ключевые компетенции")
            if matching:
                matched_list = sorted(matching)
                lines.append(f"\n**Стек, совпадающий с требованиями вакансии:** {', '.join(matched_list)}.")
            if gaps:
                lines.append(f"**Технологии для освоения:** {', '.join(gaps)} — готов(а) быстро изучить в процессе работы.")
            if all_tech and not matching:
                lines.append(f"**Технический стек:** {', '.join(sorted(all_tech))}.")

            # Experience narrative
            lines.append("")
            lines.append("### Опыт и проекты")
            if achievements:
                lines.append("\n**Ключевые результаты на предыдущих местах:**")
                for i, a in enumerate(achievements, 1):
                    lines.append(f"{i}. {a}")
            elif years:
                lines.append(f"\nЗа {years} лет коммерческой разработки участвовал(а) в проектах разного масштаба — от стартапов до enterprise-решений. Решал(а) задачи полного цикла: от проектирования до эксплуатации.")
            else:
                lines.append("\nУчаствовал(а) в проектах полного цикла разработки, решал(а) как продуктовые, так и инфраструктурные задачи.")

            # Education
            if education:
                lines.append("")
                lines.append("### Образование")
                lines.append(f"\n{education}")

            # Motivation
            lines.append("")
            lines.append("### Почему эта вакансия")
            if company:
                lines.append(f"\nМеня привлекает **{company}** — компания с сильной инженерной культурой и масштабными задачами.")
            if role:
                lines.append(f"Позиция **{role}** соответствует моему опыту и карьерным целям — хочу развиваться в этой области и приносить measurable impact.")

        # ---- Closing ----
        lines.append("")
        lines.append("Готов(а) подробно обсудить проекты и ответить на вопросы. Буду рад(а) стать частью команды!")

        return "\n".join(lines)

    def _build_questions(self, role: str, itype: str,
                          vac_tech: set, res_tech: set, gaps: list[str],
                          matching: set, years: int, education: str,
                          achievements: list[str],
                          gathered_info: str = "") -> list[dict]:
        questions = []

        # If gathered_info has substantial content, mine it for questions
        gi_text = gathered_info if len(gathered_info) > 50 else ""

        # ---- Deep tech questions for matching skills ----
        for t in sorted(matching)[:4]:
            questions.append({
                "question": f"Расскажите о вашем опыте с **{t}**: в каких проектах применяли, какие задачи решали?",
                "suggested_answer": (
                    f"Опишите 1-2 конкретных проекта с {t}. Структурируйте ответ по STAR:\n"
                    f"- Situation: контекст проекта, масштаб (пользователи, объём данных, нагрузка)\n"
                    f"- Task: какую задачу вы решали с помощью {t}\n"
                    f"- Action: какие решения и паттерны применяли, с какими трудностями столкнулись\n"
                    f"- Result: конкретные метрики — производительность, время доставки, стоимость, надёжность\n"
                    f"Пример: «В проекте интернет-магазина (500k MAU) я использовал {t} для... В результате задержка API сократилась на 40%.»"
                )
            })

        # ---- Gap questions ----
        for g in gaps[:3]:
            questions.append({
                "question": f"В вакансии указан(а) **{g}**, но в вашем резюме этого нет. Как быстро вы осваиваете новые инструменты?",
                "suggested_answer": (
                    f"Не отрицайте пробел — покажите, как вы его закроете:\n"
                    f"1. Признайте: «Действительно, с {g} у меня пока нет коммерческого опыта.»\n"
                    f"2. Приведите пример быстрого освоения другой технологии (за 2-4 недели до первого результата).\n"
                    f"3. Покажите, что уже начали изучать: «Я уже посмотрел(а) документацию/прошёл(ла) туториал по {g}.»\n"
                    f"4. Подчеркните смежный опыт, который поможет освоить {g} быстрее."
                )
            })

        # ---- Architecture / system design (for senior+) ----
        level = self._detect_role_level(role)
        if level in ("senior", "lead"):
            questions.append({
                "question": "Расскажите о самом сложном архитектурном решении, которое вы принимали. Какие были альтернативы?",
                "suggested_answer": (
                    "Опишите архитектурную задачу с высокими ставками (производительность, стоимость ошибки, масштаб):\n"
                    "- Какие trade-off вы рассматривали (consistency vs availability, latency vs throughput, монолит vs микросервисы)?\n"
                    "- Как вы собирали данные для принятия решения (метрики, бенчмарки, нагрузочное тестирование)?\n"
                    "- Как обосновывали выбор перед командой/руководством?\n"
                    "- Какой был результат и что бы вы сделали иначе сейчас?"
                )
            })
            questions.append({
                "question": "Как вы выстраивали процессы разработки в команде? Приходилось ли вам менторить коллег?",
                "suggested_answer": (
                    "Приведите примеры:\n"
                    "- Внедрение практик: код-ревью, парное программирование, CI/CD\n"
                    "- Менторство: сколько человек, какие темы, как изменилась их эффективность\n"
                    "- Командные метрики: cycle time, частота релизов, количество инцидентов"
                )
            })

        # ---- Role-type specific ----
        if itype == "tech":
            questions.append({
                "question": "Как вы подходите к тестированию своего кода? Какие виды тестов считаете обязательными?",
                "suggested_answer": (
                    "Опишите свою пирамиду тестирования:\n"
                    "- Unit-тесты: покрытие критической логики, какие фреймворки\n"
                    "- Интеграционные тесты: подход к тестированию внешних зависимостей\n"
                    "- E2E / контрактные тесты: когда и зачем\n"
                    "- Баланс между скоростью разработки и надёжностью\n"
                    "- Конкретный пример, когда тест спас от бага в проде."
                )
            })
            questions.append({
                "question": "Расскажите о случае, когда вам пришлось разбираться с багом в продакшене под давлением времени.",
                "suggested_answer": (
                    "Опишите конкретный инцидент:\n"
                    "- Как обнаружили проблему (мониторинг, жалобы пользователей)?\n"
                    "- Ваши шаги по диагностике: логи, метрики, дебаггинг\n"
                    "- Как исправляли (hotfix, rollback, feature flag)?\n"
                    "- Какие выводы сделали для предотвращения в будущем (post-mortem, новые тесты, алерты)?"
                )
            })
        elif itype == "hr":
            questions.append({
                "question": "Почему вы уходите с текущего места работы? Что для вас важно в новом месте?",
                "suggested_answer": (
                    "Будьте честны, но дипломатичны:\n"
                    "- Не критикуйте текущего работодателя — фокусируйтесь на том, что вы ищете\n"
                    "- Говорите о развитии: «Хочу больше сложных задач / другую технологию / работу над продуктом с большим масштабом»\n"
                    "- Покажите, что ваш выбор осознанный: «Я изучал(а) компанию, и мне близка ваша инженерная культура»."
                )
            })
            questions.append({
                "question": "Расскажите о конфликтной ситуации на работе. Как вы её разрешили?",
                "suggested_answer": (
                    "Используйте конкретный пример, но не переходите на личности:\n"
                    "- Опишите ситуацию: разногласия по техдолгу vs. фичи, или архитектурный спор\n"
                    "- Ваши действия: выслушали аргументы, предложили компромисс, привлекли данные\n"
                    "- Результат: решение устроило обе стороны, процессы улучшились\n"
                    "- Урок: что вы поняли о коммуникации и работе в команде."
                )
            })
        else:  # final / management
            questions.append({
                "question": "Как вы измеряете успех своей работы? Какие KPI считаете ключевыми?",
                "suggested_answer": (
                    "Покажите системный подход:\n"
                    "- Технические метрики: uptime, latency, качество кода\n"
                    "- Продуктовые метрики: влияние на бизнес-показатели\n"
                    "- Командные метрики: скорость поставки, удовлетворённость команды\n"
                    "- Приведите пример, как вы улучшили конкретный показатель."
                )
            })

        # ---- Experience-based question ----
        if years >= 5:
            questions.append({
                "question": "Как изменился ваш подход к разработке за последние несколько лет?",
                "suggested_answer": (
                    "Покажите профессиональный рост:\n"
                    "- Технический: от написания кода к проектированию систем\n"
                    "- Процессный: от индивидуальных задач к командной эффективности\n"
                    "- Ментальный: от «сделать работает» к «сделать надёжно, поддерживаемо и вовремя»\n"
                    "- Приведите конкретный контраст: «Раньше я ..., а теперь я ...»."
                )
            })

        # ---- Generic but important ----
        questions.append({
            "question": "Почему вы хотите работать именно в этой компании? Что знаете о нас?",
            "suggested_answer": (
                "Подготовьтесь заранее:\n"
                "- Изучите сайт компании, блог, технические доклады сотрудников на конференциях\n"
                "- Найдите, что вас действительно привлекает: технологический стек, масштаб, культура, продукт\n"
                "- Свяжите со своим опытом: «Мой опыт в X поможет вам решить задачу Y.»\n"
                "- Будьте конкретны — общие фразы про «хорошую компанию» звучат неубедительно."
            )
        })
        questions.append({
            "question": "Расскажите о вашем самом большом профессиональном провале или ошибке.",
            "suggested_answer": (
                "Это вопрос про рефлексию и зрелость, а не про некомпетентность:\n"
                "- Выберите реальный, но не катастрофический пример\n"
                "- Опишите контекст и что пошло не так\n"
                "- Главное — что вы сделали, чтобы исправить ситуацию\n"
                "- И самый важный пункт: какой урок вы извлекли и как изменили свои действия в будущем."
            )
        })

        return questions[:12]

    def _build_salary_recommendation(self, years: int, level: str,
                                      salary_from_vac: str, role: str) -> str:
        # Infer level from years if unknown
        inferred = level
        if inferred == "unknown" and years > 0:
            if years <= 2:
                inferred = "junior"
            elif years <= 5:
                inferred = "middle"
            elif years <= 8:
                inferred = "senior"
            else:
                inferred = "lead"

        info = MARKET_SALARY.get(inferred, MARKET_SALARY["unknown"])
        level_labels = {"junior": "Junior", "middle": "Middle", "senior": "Senior", "lead": "Lead/Team Lead"}

        lines = [
            "## Рекомендации по зарплате\n",
            f"**Уровень позиции:** {level_labels.get(inferred, 'Не определён')}",
            f"**Опыт:** {years} лет" if years else "**Опыт:** не указан в резюме",
            f"**Рыночный диапазон:** {info['range']}",
        ]

        if salary_from_vac:
            lines.append(f"**Зарплатная вилка в вакансии:** {salary_from_vac}")

        lines.append("")
        lines.append("### Стратегия переговоров\n")
        lines.append(f"1. **Ориентир:** рыночный диапазон для вашего уровня — {info['range']}.")
        if salary_from_vac:
            lines.append(f"2. **Вилка вакансии:** {salary_from_vac} — это стартовая точка для обсуждения, а не потолок.")
        lines.append(f"{'3' if salary_from_vac else '2'}. **Первый контакт:** не называйте точную цифру первым — спросите бюджет вилки.")
        lines.append(f"{'4' if salary_from_vac else '3'}. **Аргументация:** {info['negotiation']}")
        lines.append(f"{'5' if salary_from_vac else '4'}. **Полный пакет:** обсуждайте не только оклад, но и годовой бонус, ДМС, опционы/акции, бюджет на обучение и конференции.")
        lines.append(f"{'6' if salary_from_vac else '5'}. **Точка выхода:** определите для себя минимальную приемлемую сумму заранее. Если предложение ниже — вежливо обсудите пересмотр через испытательный срок (3-6 месяцев).")

        if inferred in ("senior", "lead"):
            lines.append("")
            lines.append("### Дополнительно для Senior/Lead\n")
            lines.append("- Обсуждайте не только зарплату, но и: опционы/акции, процент от прибыли, бюджет на команду и инструменты.")
            lines.append("- Уточните: какой % годового бонуса, условия его получения (личные KPI, командные, бизнес-показатели).")
            lines.append("- Возможность влиять на техническую стратегию и нанимать людей в свою команду — тоже часть компенсации.")

        return "\n".join(lines)

    def _build_employer_questions(self, vac_tech: set[str], matching: set,
                                   red_flags: list[str], vac_text: str,
                                   company: str) -> list[str]:
        questions = []

        # 1. Tech stack
        if vac_tech:
            main_tech = ", ".join(sorted(vac_tech)[:5])
            questions.append(f"Какой стек технологий используется в команде? Я вижу {main_tech} в вакансии — какие версии, есть ли планы по миграции или обновлению?")
        else:
            questions.append("Какой стек технологий используется в команде? Какие версии, есть ли планы по миграции?")

        # 2. Team structure
        questions.append("Сколько человек в команде, как распределены роли? Есть ли отдельные QA, DevOps, продакт-менеджер?")

        # 3. Project stage
        questions.append("На какой стадии находится проект/продукт? Какие ключевые цели на ближайшие 6-12 месяцев?")

        # 4. Development process
        if not re.search(r"(?:Agile|Scrum|Kanban|методолог|процесс)", vac_text, re.IGNORECASE):
            questions.append("Как организованы процессы разработки? Как часто релизы, кто отвечает за приоритеты?")
        else:
            questions.append("Как у вас устроен процесс код-ревью? Есть ли практика парного программирования?")

        # 5. Growth
        questions.append("Какие возможности для профессионального роста предоставляет компания? Есть ли бюджет на обучение и конференции?")

        # 6. Work format
        if not re.search(r"(?:офис|удал[её]н|гибрид|remote|office|hybrid|формат)", vac_text, re.IGNORECASE):
            questions.append("Какой формат работы: офис, удалёнка или гибрид? Есть ли требования по посещению офиса?")

        # 7. Tools
        if not re.search(r"(?:CI/CD|Jira|Confluence|GitLab|GitHub|трекер)", vac_text, re.IGNORECASE):
            questions.append("Какие инструменты используются: CI/CD, мониторинг, таск-трекер, система коммуникации?")
        else:
            questions.append("Как устроен CI/CD пайплайн? Сколько времени занимает от коммита до продакшена?")

        # 8. Red flags follow-up
        for rf in red_flags:
            if rf == "переработки":
                questions.append("Как часто случаются переработки? Компенсируются ли они (отгулы, дополнительная оплата)?")
            elif rf == "режим стартапа":
                questions.append("Какие процессы уже выстроены, а что предстоит создавать с нуля?")
            elif rf == "многозадачность":
                questions.append("Сколько проектов/задач обычно ведёт один разработчик одновременно? Как устроена приоритизация?")
            elif rf == "стрессоустойчивость":
                questions.append("Какие факторы создают основной стресс в работе? Как компания помогает команде справляться с нагрузкой?")
            elif rf == "горящие сроки":
                questions.append("Как часто возникают ситуации с горящими сроками? Есть ли практика планирования спринтов с запасом?")
            break  # max one red-flag-specific question

        # 9. Onboarding
        questions.append("Как организован процесс онбординга? Есть ли ментор или buddy в первые недели?")

        # 10. Company-specific
        if company:
            questions.append(f"Что вы особенно цените в инженерной культуре **{company}**? Какие инженерные практики считаете ключевыми?")

        return questions[:10]
