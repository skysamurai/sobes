# sobes_modules/preparation/analyzer.py
"""Combined vacancy + resume analysis for interview preparation."""
import re
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

TECH_KEYWORDS = [
    "Python", "Java", "Go", "C\\+\\+", "C#", "Rust", "JavaScript", "TypeScript",
    "Ruby", "PHP", "Kotlin", "Swift", "Scala", "R", "MATLAB",
    "Django", "Flask", "FastAPI", "Spring", "ASP\\.NET", "Express", "React",
    "Vue", "Angular", "Svelte", "Next\\.js", "Nuxt", "jQuery",
    "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch", "Cassandra",
    "ClickHouse", "Oracle", "MS SQL", "SQLite", "DynamoDB",
    "Docker", "Kubernetes", "Helm", "Terraform", "Ansible", "Jenkins",
    "GitLab CI", "GitHub Actions", "ArgoCD", "Prometheus", "Grafana",
    "Kafka", "RabbitMQ", "NATS", "gRPC", "GraphQL", "REST",
    "AWS", "GCP", "Azure", "Yandex Cloud", "S3", "EC2", "Lambda",
    "Linux", "Bash", "Nginx", "Apache", "Git", "CI/CD", "DevOps",
    "Machine Learning", "ML", "Deep Learning", "NLP", "Computer Vision",
    "PyTorch", "TensorFlow", "Keras", "Pandas", "NumPy", "Scikit-learn",
    "Agile", "Scrum", "Kanban", "Jira", "Confluence", "Figma",
    "микросервисы", "highload", "high-load", "высоконагружен", "распредел[её]н",
]

EXPERIENCE_PATTERNS = [
    r"(?:опыт|experience).*?(\d+)[\s-]*(?:год|лет|года|year|yrs?)",
    r"(\d+)[\s-]*(?:год|лет|года|year|yrs?)\s+(?:опыта|experience)",
    r"(?:стаж|seniority)[:\s]+(\d+)[\s-]*(?:год|лет|года|year)",
    r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|опыт)",
]

EDUCATION_PATTERNS = [
    r"(?:образование|education|университет|university|вуз|институт)[:\s]+(.+?)(?:\n|$)",
    r"(?:бакалавр|магистр|bachelor|master|phd|кандидат|доктор|MBA)[а-я]*\s+(.+?)(?:\n|$)",
    r"(.+?)\s+(?:университет|university|институт)",
]

ACHIEVEMENT_PATTERNS = [
    r"(?:достижени[ея]|achievement|результат|увеличил|сократил|внедрил|разработал|improved|reduced|implemented|optimized|migrated|built|led|managed)",
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
    (r"(?:работа\s+на\s+результат\s+любой\s+ценой)", "работа на результат любой ценой"),
]

MARKET_SALARY = {
    "junior": "80 000 – 150 000 ₽",
    "middle": "150 000 – 300 000 ₽",
    "senior": "300 000 – 500 000 ₽",
    "lead": "400 000 – 700 000+ ₽",
    "unknown": "150 000 – 350 000 ₽",
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
        tech = self._extract_technologies(vacancy_text + " " + resume_text)
        vac_tech = self._extract_technologies(vacancy_text)
        res_tech = self._extract_technologies(resume_text)
        years = self._extract_experience_years(resume_text)
        education = self._extract_education(resume_text)
        achievements = self._extract_achievements(resume_text)
        salary = self._extract_salary(vacancy_text)
        level = self._detect_role_level(role + " " + vacancy_text)
        gaps = [t for t in vac_tech if t not in res_tech]
        red_flags = self._detect_red_flags(vacancy_text)

        return AnalysisResult(
            self_presentation=self._build_self_presentation(
                company, role, years, tech, res_tech & vac_tech, education, achievements),
            anticipated_questions=self._build_questions(
                role, interview_type, vac_tech, res_tech, gaps, tech),
            salary_recommendation=self._build_salary_recommendation(
                years, level, salary, role),
            employer_questions=self._build_employer_questions(
                vac_tech, red_flags, vacancy_text),
            raw={"backend": "template"},
            created_at=datetime.now().isoformat(),
        )

    # ---- extractors ----

    def _extract_technologies(self, text: str) -> set[str]:
        found = set()
        for kw in TECH_KEYWORDS:
            if re.search(kw, text, re.IGNORECASE):
                clean = kw.replace("\\", "").replace("+", "+").replace(".", ".")
                if clean.endswith("+") and clean[:-1].rstrip("\\") in found:
                    continue
                found.add(clean)
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
                    clean = re.sub(r"^[•\-\s\d.]+\s*", "", line.strip())
                    if clean and clean not in results:
                        results.append(clean)
        return results[:5]

    def _extract_salary(self, text: str) -> str:
        for pat in SALARY_PATTERNS:
            m = re.search(pat, text, re.IGNORECASE)
            if m and m.lastindex and m.lastindex >= 2:
                return f"{m.group(1).strip()} – {m.group(2).strip()}"
            elif m:
                return m.group(0).strip()[:80]
        return ""

    def _detect_role_level(self, text: str) -> str:
        text_lower = text.lower()
        if any(w in text_lower for w in ["lead", "team lead", "тимлид", "руководитель", "principal", "staff", "ведущий"]):
            return "lead"
        if any(w in text_lower for w in ["senior", "старший", "сеньор", "сеньёр"]):
            return "senior"
        if any(w in text_lower for w in ["middle", "мидл", "миддл"]):
            return "middle"
        if any(w in text_lower for w in ["junior", "джуниор", "младший", "стаж[её]р"]):
            return "junior"
        return "unknown"

    def _detect_vacancy_gaps(self, vac_text: str, res_text: str) -> list[dict]:
        return []

    def _detect_red_flags(self, text: str) -> list[str]:
        found = []
        for pat, label in RED_FLAG_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                found.append(label)
        return found

    # ---- builders ----

    def _build_self_presentation(self, company: str, role: str, years: int,
                                  all_tech: set, matching: set, education: str,
                                  achievements: list[str]) -> str:
        parts = []
        parts.append("### САМОПРЕЗЕНТАЦИЯ\n")

        # Intro
        intro = "Здравствуйте!"
        if years:
            intro += f" Я специалист с {years} годами опыта"
        parts.append(intro)

        # Role connection
        if role:
            parts.append(f"\nЦелевая позиция: **{role}**")
            if company:
                parts.append(f"в компании **{company}**")
            parts.append("")

        # Skills
        if matching:
            skills = ", ".join(sorted(matching)[:8])
            parts.append(f"\n**Ключевые навыки, релевантные вакансии:**")
            parts.append(skills)
        elif all_tech:
            skills = ", ".join(sorted(all_tech)[:8])
            parts.append(f"\n**Технический стек:** {skills}")

        # Experience summary
        if years and role:
            level = self._detect_role_level(role)
            if level != "unknown":
                level_label = {"junior": "Junior", "middle": "Middle",
                               "senior": "Senior", "lead": "Lead/Team Lead"}
                parts.append(f"\nУровень: **{level_label.get(level, level)}**")

        # Education
        if education:
            parts.append(f"\n**Образование:** {education}")

        # Achievements
        if achievements:
            parts.append("\n**Ключевые достижения:**")
            for a in achievements[:3]:
                parts.append(f"• {a}")

        # Motivation
        if company:
            parts.append(f"\nМеня заинтересовала эта вакансия в **{company}**.")
            if role:
                parts.append(f"Вижу отличную возможность применить свой опыт на позиции {role}.")
        parts.append("\nГотов(а) обсудить детали и ответить на ваши вопросы.")

        return "\n".join(parts).strip()

    def _build_questions(self, role: str, itype: str,
                          vac_tech: set, res_tech: set, gaps: list[str],
                          all_tech: list[str]) -> list[dict]:
        questions = []

        # Tech-specific questions
        for t in sorted(vac_tech)[:5]:
            if t in res_tech:
                questions.append({
                    "question": f"Расскажите о вашем опыте работы с {t}. В каких проектах применяли?",
                    "suggested_answer": f"Опишите 1-2 проекта, где вы использовали {t}: какие задачи решали, каких результатов достигли. Упомяните конкретные метрики (производительность, масштаб, сроки)."
                })
            else:
                questions.append({
                    "question": f"В вакансии указан {t}, но в резюме этого нет. Как быстро вы осваиваете новые технологии?",
                    "suggested_answer": f"Подчеркните свою способность быстро учиться. Приведите пример, когда вы осваивали новую технологию «на лету» и достигали результата."
                })

        # Gaps
        for g in gaps[:2]:
            questions.append({
                "question": f"У вас нет опыта с {g} — как планируете закрывать этот пробел?",
                "suggested_answer": "Расскажите о смежном опыте, который поможет быстро освоить эту технологию. Покажите мотивацию к обучению."
            })

        # Role-specific
        tech_questions = {
            "tech": [
                {"question": "Расскажите о самой сложной технической проблеме, которую вы решали.",
                 "suggested_answer": "Опишите проблему, контекст, ваш подход к решению, альтернативы, которые вы рассматривали, и конечный результат. Используйте метод STAR."},
                {"question": "Как вы подходите к архитектурным решениям? Приведите пример.",
                 "suggested_answer": "Расскажите о проекте, где вы принимали архитектурные решения: какие trade-off рассматривали, как обосновывали выбор, какие результаты получили."},
                {"question": "Как вы обеспечиваете качество кода в команде?",
                 "suggested_answer": "Опишите практики: код-ревью, тестирование, CI/CD, статический анализ. Приведите пример, когда ваши действия предотвратили баг в проде."},
            ],
            "hr": [
                {"question": "Почему вы ушли с последнего места работы?",
                 "suggested_answer": "Будьте честны, но дипломатичны. Фокусируйтесь на том, что вы ищете (развитие, новые вызовы), а не на том, от чего уходите."},
                {"question": "Кем вы видите себя через 3 года?",
                 "suggested_answer": "Покажите амбиции, соразмерные позиции. Свяжите свой рост с развитием компании."},
                {"question": "Расскажите о конфликтной ситуации в команде и как вы её разрешили.",
                 "suggested_answer": "Опишите конкретную ситуацию, вашу роль в разрешении конфликта и уроки, которые вы извлекли."},
            ],
            "final": [
                {"question": "Какие у вас зарплатные ожидания?",
                 "suggested_answer": "Назовите реалистичный диапазон, основанный на рыночных данных. См. раздел рекомендаций по зарплате."},
                {"question": "Когда вы готовы выйти на работу?",
                 "suggested_answer": "Укажите реалистичный срок с учётом необходимости завершить дела на текущем месте."},
            ],
        }
        defaults = tech_questions.get(itype, tech_questions["tech"])
        questions.extend(defaults)

        # Generic questions always included
        questions.append({
            "question": "Почему вы хотите работать именно в этой компании?",
            "suggested_answer": "Изучите продукты, миссию и культуру компании. Свяжите свой опыт с их задачами. Покажите искренний интерес."
        })
        questions.append({
            "question": "Расскажите о вашем самом большом профессиональном провале.",
            "suggested_answer": "Выберите реальный пример, где вы ошиблись, но извлекли урок. Покажите, как изменили подход после этого опыта."
        })

        return questions

    def _build_salary_recommendation(self, years: int, level: str,
                                      salary_from_vac: str, role: str) -> str:
        parts = ["### РЕКОМЕНДАЦИИ ПО ЗАРПЛАТЕ\n"]

        if level == "unknown" and years > 0:
            if years < 2:
                level = "junior"
            elif years < 5:
                level = "middle"
            elif years < 8:
                level = "senior"
            else:
                level = "lead"

        market_range = MARKET_SALARY.get(level, MARKET_SALARY["unknown"])
        level_label = {"junior": "Junior", "middle": "Middle",
                       "senior": "Senior", "lead": "Lead"}.get(level, "Не определён")

        parts.append(f"**Уровень позиции:** {level_label}")
        parts.append(f"**Опыт:** {years} лет" if years else "**Опыт:** не указан")
        parts.append(f"**Рыночный диапазон для этого уровня:** {market_range}")

        if salary_from_vac:
            parts.append(f"**Зарплата в вакансии:** {salary_from_vac}")

        parts.append("")
        parts.append("**Стратегия переговоров:**")

        if salary_from_vac and level != "unknown":
            parts.append(f"1. Отталкивайтесь от вилки в вакансии ({salary_from_vac}).")
            parts.append(f"2. При обсуждении ссылайтесь на рыночные данные для {level_label}-специалистов ({market_range}).")
        else:
            parts.append(f"1. Ориентируйтесь на рыночный диапазон: {market_range}.")
            parts.append("2. На первом контакте не называйте точную цифру — спросите бюджет.")

        parts.append("3. Обсуждайте полный компенсационный пакет (бонусы, опционы, ДМС, обучение).")
        parts.append("4. Подготовьте аргументы: опыт, достижения, уникальные навыки, релевантные проекты.")
        parts.append("5. Если предложение ниже ожиданий — вежливо обсудите возможности пересмотра через 3-6 месяцев.")

        if level == "senior" or level == "lead":
            parts.append("\n💡 Как Senior/Lead вы можете также обсуждать: опционы, участие в прибыли, бюджет на команду/инструменты.")

        return "\n".join(parts)

    def _build_employer_questions(self, vac_tech: set[str],
                                   red_flags: list[str], vac_text: str) -> list[str]:
        questions = []

        # Tech / team questions
        if not vac_tech:
            questions.append("Какой стек технологий используется в команде?")
        else:
            questions.append(f"Какой стек технологий используется? Какие версии, есть ли планы по миграции?")

        questions.append("Сколько человек в команде? Как распределены роли (разработчики, QA, DevOps, PM)?")

        # Project
        if not re.search(r"(?:проект|продукт|product|project|стадия)", vac_text, re.IGNORECASE):
            questions.append("На какой стадии находится проект/продукт? Какие ключевые цели на ближайший год?")

        # Process
        questions.append("Как организованы процессы разработки: Agile/Scrum/Kanban? Как часто релизы?")

        # Growth
        questions.append("Какие возможности для профессионального роста и обучения предоставляет компания?")

        # Work format
        if not re.search(r"(?:офис|удал[её]н|гибрид|remote|office|hybrid)", vac_text, re.IGNORECASE):
            questions.append("Какой формат работы: офис, удалёнка или гибрид? Есть ли требования по посещению офиса?")

        # Tools
        questions.append("Какие инструменты используются: CI/CD, мониторинг, таск-трекер, коммуникация?")

        # Red flag follow-ups
        for rf in red_flags:
            if rf == "переработки":
                questions.append("Как часто случаются переработки? Компенсируются ли они (отгулы, оплата)?")
            elif rf == "режим стартапа":
                questions.append("Какие процессы уже выстроены, а что предстоит создавать с нуля?")
            elif rf == "многозадачность":
                questions.append("Сколько проектов/задач обычно ведёт один разработчик одновременно?")
            elif rf == "стрессоустойчивость":
                questions.append("Какие факторы создают основной стресс в работе? Как компания помогает с ними справляться?")

        # Onboarding
        questions.append("Как организован процесс онбординга? Есть ли ментор или buddy-система?")

        return questions[:10]
