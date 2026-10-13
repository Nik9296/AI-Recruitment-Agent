"""Canonical skill aliases used after LLM extraction."""

SKILL_ALIASES: dict[str, str] = {
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "py": "Python",
    "python": "Python",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "react.js": "React",
    "reactjs": "React",
    "react": "React",
    "next": "Next.js",
    "nextjs": "Next.js",
    "next.js": "Next.js",
    "node": "Node.js",
    "nodejs": "Node.js",
    "node.js": "Node.js",
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "postgressql": "PostgreSQL",
    "tf": "TensorFlow",
    "tensorflow": "TensorFlow",
    "pytorch": "PyTorch",
    "sklearn": "scikit-learn",
    "scikit-learn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "powerbi": "Power BI",
    "power bi": "Power BI",
    "ms excel": "Excel",
    "microsoft excel": "Excel",
    "excel": "Excel",
    "html5": "HTML",
    "css3": "CSS",
    "golang": "Go",
}


def canonicalize_skill(skill: str) -> str:
    key = " ".join(skill.strip().lower().split())
    return SKILL_ALIASES.get(key, skill.strip())
