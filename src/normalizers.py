import re
import phonenumbers
from typing import Optional


def normalize_date(date_str: Optional[str]) -> Optional[str]:
    if not date_str:
        return None
    match = re.search(r'(\d{4})[-/]?(\d{2})?', date_str)
    if match:
        year, month = match.group(1), match.group(2)
        return f"{year}-{month}" if month else year
    return date_str


def normalize_phone(phone_str: Optional[str]) -> Optional[str]:
    if not phone_str:
        return None
    for region in ["US", "IN"]:
        try:
            parsed = phonenumbers.parse(phone_str, region)
            if phonenumbers.is_possible_number(parsed):
                return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except phonenumbers.phonenumberutil.NumberParseException:
            continue
    return phone_str


def normalize_skill(skill_name: Optional[str]) -> Optional[str]:
    if not skill_name:
        return None
    skill = skill_name.strip().lower()
    mapping = {
        "js": "javascript", "javascript": "javascript",
        "typescript": "typescript", "ts": "typescript",
        "node": "node.js", "nodejs": "node.js", "node.js": "node.js",
        "react": "react.js", "reactjs": "react.js", "react.js": "react.js",
        "nextjs": "next.js", "next.js": "next.js",
        "vue": "vue.js", "vuejs": "vue.js",
        "angular": "angular",
        "express": "express.js", "expressjs": "express.js",
        "py": "python", "python": "python", "python3": "python",
        "flask": "flask", "fastapi": "fastapi", "django": "django",
        "pandas": "pandas", "numpy": "numpy",
        "sklearn": "scikit-learn", "scikit-learn": "scikit-learn", "scikit learn": "scikit-learn",
        "pytorch": "pytorch", "torch": "pytorch",
        "tensorflow": "tensorflow", "tf": "tensorflow",
        "keras": "keras", "streamlit": "streamlit",
        "golang": "go", "go": "go",
        "postgres": "postgresql", "postgresql": "postgresql",
        "mysql": "mysql",
        "mongo": "mongodb", "mongodb": "mongodb",
        "redis": "redis", "elasticsearch": "elasticsearch",
        "sql": "sql", "nosql": "nosql", "sqlite": "sqlite",
        "java": "java",
        "spring": "spring boot", "spring boot": "spring boot",
        "kotlin": "kotlin",
        "docker": "docker",
        "k8s": "kubernetes", "kubernetes": "kubernetes",
        "aws": "aws", "gcp": "gcp", "azure": "azure",
        "ci/cd": "ci/cd", "cicd": "ci/cd",
        "git": "git", "linux": "linux",
        "ml": "machine learning", "machine learning": "machine learning",
        "deep learning": "deep learning", "dl": "deep learning",
        "nlp": "nlp",
        "cv": "computer vision", "computer vision": "computer vision",
        "genai": "generative ai", "llm": "llm",
        "html": "html", "css": "css",
        "tailwind": "tailwind css", "tailwindcss": "tailwind css",
        "graphql": "graphql",
        "rest": "rest api", "restapi": "rest api", "rest api": "rest api",
        "c++": "c++", "cpp": "c++",
        "c#": "c#", "csharp": "c#",
        "rust": "rust", "scala": "scala", "r": "r", "matlab": "matlab",
        "jupyter": "jupyter", "excel": "excel",
        "tableau": "tableau", "powerbi": "power bi", "power bi": "power bi",
        "react native": "react native",
        "flutter": "flutter", "android": "android", "ios": "ios", "swift": "swift",
    }
    return mapping.get(skill, skill)


def normalize_country(country_str: Optional[str]) -> Optional[str]:
    if not country_str:
        return None
    country = country_str.strip().lower()
    mapping = {
        "united states": "US", "united states of america": "US", "usa": "US", "us": "US",
        "united kingdom": "GB", "uk": "GB", "great britain": "GB",
        "india": "IN", "in": "IN",
        "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR",
        "singapore": "SG", "netherlands": "NL", "sweden": "SE",
        "norway": "NO", "denmark": "DK", "switzerland": "CH",
        "japan": "JP", "china": "CN",
        "south korea": "KR", "korea": "KR",
        "brazil": "BR", "mexico": "MX",
    }
    if country in mapping:
        return mapping[country]
    if len(country_str.strip()) == 2:
        return country_str.strip().upper()
    return country_str
