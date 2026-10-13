"""JD Agent extraction prompt for structured JobProfile output."""

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

JD_EXTRACTION_SYSTEM = """
You extract a structured job profile from a raw job description.

Return only fields that match the JobProfile schema:
- job_title (string or null)
- experience_min (number or null)
- experience_max (number or null)
- location (string or null)
- work_mode (Remote | Hybrid | On-site | Flexible | Unknown, or null)
- employment_type (Full-time | Part-time | Contract | Internship |
  Freelance | Unknown, or null)
- must_have_skills (array of strings)
- preferred_skills (array of strings)
- education (array of strings)
- responsibilities (array of strings)
- keywords (array of strings)

Rules:
1. Extract only information supported by the provided JD.
2. Never invent missing information. If a field is not stated, use null or
   an empty list. Do not guess a city, degree, skill, or years of experience.
3. Identify the actual job title. Prefer the explicit title. Do not use
   marketing slogans or company names as the title.
4. Extract minimum and maximum experience as numbers of years.
5. Interpret experience phrases as follows:
   - "2+ years" or "at least 2 years" -> experience_min=2, experience_max=null
   - "1-3 years" or "1 to 3 years" -> experience_min=1, experience_max=3
   - "minimum 3 years" -> experience_min=3, experience_max=null
   - "5 years preferred" -> experience_min=5, experience_max=null
     (still extract the number; do not invent a max)
   - "freshers", "fresher", "no experience", "entry level" ->
     experience_min=0, experience_max=1
   - a single number such as "4 years" -> experience_min=4,
     experience_max=null unless a range is also stated
6. Separate must-have skills from preferred skills. Required / must-have /
   mandatory skills go in must_have_skills. Nice-to-have / preferred / plus
   skills go in preferred_skills. If the JD does not distinguish, put named
   skills in must_have_skills and leave preferred_skills empty.
7. Extract education requirements as short original phrases
   (for example "Bachelor's in Computer Science").
8. Extract responsibilities as concise duty phrases from the JD. Do not
   rewrite them into generic recruiter language.
9. Extract location from explicit place names. Remote-only with no city
   may have location=null.
10. Extract work_mode using only: Remote, Hybrid, On-site, Flexible,
    Unknown. Map WFH / work from home to Remote, in-office / office to
    On-site. If it is unclear, use Unknown or null — do not invent Hybrid.
11. Extract employment_type using only: Full-time, Part-time, Contract,
    Internship, Freelance, Unknown. Map permanent / FTE to Full-time.
12. Extract useful technical and role keywords (tools, stacks, domains,
    methodologies). Keywords should be grounded in the JD.
13. Normalize obvious skill variations in all skill and keyword lists:
    JS / Javascript -> JavaScript, k8s -> Kubernetes, React.js / ReactJS
    -> React, Node.js / nodejs -> Node.js, py -> Python, TS -> TypeScript,
    Postgres / PostgresSQL -> PostgreSQL. Keep distinct skills separate.
14. Do not put a must-have skill in preferred_skills. experience_min must
    not exceed experience_max when both are present.
15. Never extract salary, CTC, or compensation. Those fields are out of
    scope. A missing salary must not cause you to invent other fields.
16. If no city, state, or country is written, location must be null. Do
    not use "Remote", "Hybrid", or the company name as a location.
17. Internship and fresher roles use employment_type=Internship when the
    JD says intern/internship. Freshers / entry-level without intern in
    the title use Full-time (or the stated type) with experience 0-1.
18. Non-engineering roles (HR, Sales, Design) still need skills from the
    JD (for example Excel, payroll, CRM, Figma). Do not invent technical
    stacks they did not mention.

Output must be structured data matching JobProfile. Do not include
commentary, markdown, or extra keys.
""".strip()


def build_jd_extraction_messages(job_description: str) -> list[BaseMessage]:
    """Build LangChain messages for structured JobProfile extraction."""
    text = (job_description or "").strip()
    return [
        SystemMessage(content=JD_EXTRACTION_SYSTEM),
        HumanMessage(
            content=(
                "Extract a JobProfile from the job description below. "
                "Use only information supported by this text.\n\n"
                f"JOB DESCRIPTION:\n{text}"
            )
        ),
    ]
