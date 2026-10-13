"""Labeled JD evaluation dataset (20+ realistic descriptions)."""

CASES: list[dict] = [
    {
        "id": "software_developer",
        "category": "Software Developer",
        "job_description": """
Job Title: Software Developer
Location: Bengaluru, India
Work mode: Hybrid (3 days office)
Employment type: Full-time
Experience: 3-5 years

Must have: Java, SQL, Git
Preferred: AWS

Education: Bachelor's in Computer Science

Responsibilities:
- Build and maintain backend services
- Write unit tests
- Participate in code reviews
""",
        "expected": {
            "job_title": "Software Developer",
            "experience_min": 3,
            "experience_max": 5,
            "location": "Bengaluru",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Java", "SQL", "Git"],
            "preferred_skills": ["AWS"],
            "education": ["Bachelor's in Computer Science"],
            "responsibilities": ["backend services"],
            "keywords": ["Java", "SQL"],
        },
        "noisy_llm": {
            "job_title": "Software Developer",
            "experience_min": None,
            "experience_max": None,
            "location": "Bengaluru, India",
            "work_mode": None,
            "employment_type": "full time",
            "must_have_skills": ["Java", "SQL", "Git"],
            "preferred_skills": ["AWS"],
            "education": ["Bachelor's in Computer Science"],
            "responsibilities": ["Build and maintain backend services"],
            "keywords": ["Java", "SQL"],
        },
    },
    {
        "id": "java_developer",
        "category": "Java Developer",
        "job_description": """
Java Developer — Pune (On-site)
Permanent full-time role. Minimum 4 years of experience.

Required skills: Java, Spring Boot, Microservices, SQL
Nice to have: Kafka, Redis

Education: B.Tech / B.E.

Responsibilities: design REST APIs, optimize JVM performance, mentor juniors.
""",
        "expected": {
            "job_title": "Java Developer",
            "experience_min": 4,
            "experience_max": None,
            "location": "Pune",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["Java", "Spring Boot", "SQL"],
            "preferred_skills": ["Kafka", "Redis"],
            "education": ["B.Tech"],
            "responsibilities": ["REST APIs"],
            "keywords": ["Java", "Spring Boot"],
        },
        "noisy_llm": {
            "job_title": "Java Developer",
            "must_have_skills": ["Java", "Spring Boot", "Microservices", "SQL"],
            "preferred_skills": ["Kafka", "Redis"],
            "education": ["B.Tech / B.E."],
            "responsibilities": ["design REST APIs"],
            "keywords": ["Java"],
        },
    },
    {
        "id": "python_developer",
        "category": "Python Developer",
        "job_description": """
Python Developer
Hyderabad | Hybrid | Full-time
Experience: 2-4 years

Must-have: Python, Django, PostgreSQL, REST
Preferred: FastAPI, Redis

Education: Any graduate

You will build APIs, integrate payment gateways, and fix production issues.
""",
        "expected": {
            "job_title": "Python Developer",
            "experience_min": 2,
            "experience_max": 4,
            "location": "Hyderabad",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "Django", "PostgreSQL"],
            "preferred_skills": ["FastAPI", "Redis"],
            "education": ["Any graduate"],
            "responsibilities": ["build APIs"],
            "keywords": ["Python", "Django"],
        },
        "noisy_llm": {
            "job_title": "Python Developer",
            "location": "Hyderabad",
            "must_have_skills": ["py", "Django", "Postgres", "REST"],
            "preferred_skills": ["FastAPI", "Redis"],
            "education": ["Any graduate"],
            "responsibilities": ["build APIs"],
            "keywords": ["py", "Django"],
        },
    },
    {
        "id": "full_stack_developer",
        "category": "Full Stack Developer",
        "job_description": """
Full Stack Developer
Gurgaon, Haryana. Office-based (WFO). FTE.
3+ years of experience.

Must have: React.js, Node.js, Typescript, MongoDB
Preferred: GraphQL, Docker

Education: Bachelor's degree

Responsibilities: deliver end-to-end features, review PRs, work with design.
""",
        "expected": {
            "job_title": "Full Stack Developer",
            "experience_min": 3,
            "experience_max": None,
            "location": "Gurgaon",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["React", "Node.js", "TypeScript", "MongoDB"],
            "preferred_skills": ["GraphQL", "Docker"],
            "education": ["Bachelor's"],
            "responsibilities": ["end-to-end features"],
            "keywords": ["React", "Node.js"],
        },
        "noisy_llm": {
            "job_title": "Full Stack Developer",
            "location": "Gurgaon, Haryana",
            "must_have_skills": ["React.js", "nodejs", "Typescript", "MongoDB"],
            "preferred_skills": ["GraphQL", "Docker"],
            "education": ["Bachelor's degree"],
            "responsibilities": ["deliver end-to-end features"],
            "keywords": ["React.js", "Node.js"],
        },
    },
    {
        "id": "react_developer",
        "category": "React Developer",
        "job_description": """
React Developer (Remote)
Fully remote, work from home. Full-time.
Experience: 1-3 years.

Required: React, JavaScript, HTML, CSS
Preferred: Next.js, Redux

Education: Bachelor's preferred

Build reusable UI components and improve frontend performance.
""",
        "expected": {
            "job_title": "React Developer",
            "experience_min": 1,
            "experience_max": 3,
            "location": None,
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "must_have_skills": ["React", "JavaScript", "HTML", "CSS"],
            "preferred_skills": ["Next.js", "Redux"],
            "education": ["Bachelor's"],
            "responsibilities": ["UI components"],
            "keywords": ["React", "JavaScript"],
        },
        "noisy_llm": {
            "job_title": "React Developer",
            "location": "Remote",
            "must_have_skills": ["React", "JS", "HTML", "CSS"],
            "preferred_skills": ["Next.js", "Redux"],
            "education": ["Bachelor's preferred"],
            "responsibilities": ["Build reusable UI components"],
            "keywords": ["React", "JS"],
        },
    },
    {
        "id": "ai_ml_engineer",
        "category": "AI/ML Engineer",
        "job_description": """
AI/ML Engineer
Bengaluru, on-site, full-time. 5-8 years of experience.

Must have: Python, TensorFlow, PyTorch, NLP
Preferred: LangChain, Kubernetes

Education: Master's in CS / AI preferred

Responsibilities: train models, deploy inference services, evaluate model quality.
""",
        "expected": {
            "job_title": "AI/ML Engineer",
            "experience_min": 5,
            "experience_max": 8,
            "location": "Bengaluru",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "TensorFlow", "PyTorch", "NLP"],
            "preferred_skills": ["LangChain", "Kubernetes"],
            "education": ["Master's"],
            "responsibilities": ["train models"],
            "keywords": ["Python", "NLP"],
        },
        "noisy_llm": {
            "job_title": "AI/ML Engineer",
            "experience_min": 5,
            "experience_max": 8,
            "location": "Bengaluru",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "tf", "PyTorch", "NLP"],
            "preferred_skills": ["LangChain", "k8s"],
            "education": ["Master's in CS / AI preferred"],
            "responsibilities": ["train models"],
            "keywords": ["Python", "NLP", "k8s"],
        },
    },
    {
        "id": "data_analyst",
        "category": "Data Analyst",
        "job_description": """
Data Analyst
Mumbai | Hybrid | Full-time
2 years of experience required.

Must have: SQL, Excel, Tableau
Preferred: Python, Power BI

Education: Bachelor's in Statistics, Economics, or related field

Analyze business metrics, build dashboards, and present insights to stakeholders.
Salary/CTC: not disclosed.
""",
        "expected": {
            "job_title": "Data Analyst",
            "experience_min": 2,
            "experience_max": None,
            "location": "Mumbai",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["SQL", "Excel", "Tableau"],
            "preferred_skills": ["Python", "Power BI"],
            "education": ["Bachelor's"],
            "responsibilities": ["dashboards"],
            "keywords": ["SQL", "Tableau"],
        },
        "noisy_llm": {
            "job_title": "Data Analyst",
            "location": "Mumbai",
            "must_have_skills": ["SQL", "MS Excel", "Tableau"],
            "preferred_skills": ["Python", "PowerBI"],
            "education": ["Bachelor's in Statistics, Economics, or related field"],
            "responsibilities": ["build dashboards"],
            "keywords": ["SQL", "Excel"],
        },
    },
    {
        "id": "data_scientist",
        "category": "Data Scientist",
        "job_description": """
Data Scientist — Remote
Work from home, full-time. 4-6 years.

Required: Python, scikit-learn, SQL, statistics
Preferred: Spark, AWS

Education: Master's preferred

Own experimentation, feature engineering, and model monitoring.
""",
        "expected": {
            "job_title": "Data Scientist",
            "experience_min": 4,
            "experience_max": 6,
            "location": None,
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "scikit-learn", "SQL"],
            "preferred_skills": ["Spark", "AWS"],
            "education": ["Master's"],
            "responsibilities": ["experimentation"],
            "keywords": ["Python", "SQL"],
        },
        "noisy_llm": {
            "job_title": "Data Scientist",
            "experience_min": 4,
            "experience_max": 6,
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "sklearn", "SQL", "statistics"],
            "preferred_skills": ["Spark", "AWS"],
            "education": ["Master's preferred"],
            "responsibilities": ["Own experimentation"],
            "keywords": ["Python", "sklearn"],
        },
    },
    {
        "id": "devops_engineer",
        "category": "DevOps Engineer",
        "job_description": """
DevOps Engineer
Pune, hybrid, full-time. 3-5 years.

Must have: Docker, k8s, Terraform, CI/CD
Preferred: AWS, Ansible

Education: B.E. / B.Tech

Responsibilities: maintain pipelines, manage clusters, improve observability.
""",
        "expected": {
            "job_title": "DevOps Engineer",
            "experience_min": 3,
            "experience_max": 5,
            "location": "Pune",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Docker", "Kubernetes", "Terraform"],
            "preferred_skills": ["AWS", "Ansible"],
            "education": ["B.Tech"],
            "responsibilities": ["pipelines"],
            "keywords": ["Docker", "Kubernetes"],
        },
        "noisy_llm": {
            "job_title": "DevOps Engineer",
            "location": "Pune",
            "must_have_skills": ["Docker", "k8s", "Terraform", "CI/CD"],
            "preferred_skills": ["AWS", "Ansible"],
            "education": ["B.E. / B.Tech"],
            "responsibilities": ["maintain pipelines"],
            "keywords": ["Docker", "k8s"],
        },
    },
    {
        "id": "qa_engineer",
        "category": "QA Engineer",
        "job_description": """
QA Engineer
Chennai | On-site | Full-time
Experience: 1-3 years

Must-have: Selenium, Java, TestNG
Preferred: Cypress, API testing

Education: Bachelor's

Write test cases, automate regression, log defects.
""",
        "expected": {
            "job_title": "QA Engineer",
            "experience_min": 1,
            "experience_max": 3,
            "location": "Chennai",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["Selenium", "Java"],
            "preferred_skills": ["Cypress"],
            "education": ["Bachelor's"],
            "responsibilities": ["test cases"],
            "keywords": ["Selenium", "Java"],
        },
        "noisy_llm": {
            "job_title": "QA Engineer",
            "location": "Chennai",
            "work_mode": "onsite",
            "employment_type": "Full-time",
            "must_have_skills": ["Selenium", "Java", "TestNG"],
            "preferred_skills": ["Cypress", "API testing"],
            "education": ["Bachelor's"],
            "responsibilities": ["Write test cases"],
            "keywords": ["Selenium"],
        },
    },
    {
        "id": "ui_ux_designer",
        "category": "UI/UX Designer",
        "job_description": """
UI/UX Designer
Hyderabad, hybrid, full-time. 2+ years.

Required: Figma, user research, wireframing
Preferred: HTML, CSS, prototyping

Education: Design degree preferred

Create user flows, run usability tests, partner with engineering.
""",
        "expected": {
            "job_title": "UI/UX Designer",
            "experience_min": 2,
            "experience_max": None,
            "location": "Hyderabad",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Figma", "user research", "wireframing"],
            "preferred_skills": ["HTML", "CSS"],
            "education": ["Design degree"],
            "responsibilities": ["user flows"],
            "keywords": ["Figma"],
        },
        "noisy_llm": {
            "job_title": "UI/UX Designer",
            "location": "Hyderabad",
            "must_have_skills": ["Figma", "user research", "wireframing"],
            "preferred_skills": ["HTML", "CSS", "prototyping"],
            "education": ["Design degree preferred"],
            "responsibilities": ["Create user flows"],
            "keywords": ["Figma"],
        },
    },
    {
        "id": "hr_executive",
        "category": "HR Executive",
        "job_description": """
HR Executive
Delhi NCR, in-office, full-time. 1-3 years.

Must have: recruitment, onboarding, MS Excel, payroll coordination
Preferred: HRMS, labour law basics

Education: MBA / PGDM in HR

Responsibilities: screen candidates, schedule interviews, maintain employee records.
""",
        "expected": {
            "job_title": "HR Executive",
            "experience_min": 1,
            "experience_max": 3,
            "location": "Delhi",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["recruitment", "onboarding", "Excel"],
            "preferred_skills": ["HRMS"],
            "education": ["MBA"],
            "responsibilities": ["screen candidates"],
            "keywords": ["recruitment", "Excel"],
        },
        "noisy_llm": {
            "job_title": "HR Executive",
            "location": "Delhi NCR",
            "must_have_skills": ["recruitment", "onboarding", "MS Excel", "payroll coordination"],
            "preferred_skills": ["HRMS", "labour law basics"],
            "education": ["MBA / PGDM in HR"],
            "responsibilities": ["screen candidates"],
            "keywords": ["recruitment", "MS Excel"],
        },
    },
    {
        "id": "sales_executive",
        "category": "Sales Executive",
        "job_description": """
Sales Executive
Jaipur. Field + office (hybrid). Full-time.
0-2 years of experience. Freshers with strong communication may apply.

Must have: lead generation, CRM, negotiation
Preferred: Salesforce

Education: Any graduate

Meet clients, close deals, update the pipeline weekly.
""",
        "expected": {
            "job_title": "Sales Executive",
            "experience_min": 0,
            "experience_max": 2,
            "location": "Jaipur",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["lead generation", "CRM", "negotiation"],
            "preferred_skills": ["Salesforce"],
            "education": ["Any graduate"],
            "responsibilities": ["Meet clients"],
            "keywords": ["CRM", "Salesforce"],
        },
        "noisy_llm": {
            "job_title": "Sales Executive",
            "experience_min": 0,
            "experience_max": 2,
            "location": "Jaipur",
            "must_have_skills": ["lead generation", "CRM", "negotiation"],
            "preferred_skills": ["Salesforce"],
            "education": ["Any graduate"],
            "responsibilities": ["Meet clients"],
            "keywords": ["CRM"],
        },
    },
    {
        "id": "internship",
        "category": "Internship",
        "job_description": """
Software Engineering Intern — Summer Internship
Bengaluru, hybrid, 3-month internship.
Freshers / college students. No prior full-time experience required.

Skills: Python, Git, SQL
Preferred: React.js

Education: currently pursuing B.Tech

Pair with engineers, write tests, attend standups.
""",
        "expected": {
            "job_title": "Software Engineering Intern",
            "experience_min": 0,
            "experience_max": 1,
            "location": "Bengaluru",
            "work_mode": "Hybrid",
            "employment_type": "Internship",
            "must_have_skills": ["Python", "Git", "SQL"],
            "preferred_skills": ["React"],
            "education": ["B.Tech"],
            "responsibilities": ["write tests"],
            "keywords": ["Python", "Git"],
        },
        "noisy_llm": {
            "job_title": "Software Engineering Intern",
            "location": "Bengaluru",
            "must_have_skills": ["Python", "Git", "SQL"],
            "preferred_skills": ["React.js"],
            "education": ["currently pursuing B.Tech"],
            "responsibilities": ["write tests"],
            "keywords": ["Python", "Git"],
        },
    },
    {
        "id": "fresher_position",
        "category": "Fresher position",
        "job_description": """
Graduate Trainee — Software Development
Chennai, on-site, full-time. Open to freshers and entry-level graduates.

Must have: Java or Python, SQL, good communication
Preferred: data structures

Education: B.E. / B.Tech 2024 or 2025 batch

Learn the codebase, fix bugs, and complete training modules.
""",
        "expected": {
            "job_title": "Graduate Trainee",
            "experience_min": 0,
            "experience_max": 1,
            "location": "Chennai",
            "work_mode": "On-site",
            "employment_type": "Full-time",
            "must_have_skills": ["SQL"],
            "preferred_skills": ["data structures"],
            "education": ["B.Tech"],
            "responsibilities": ["training"],
            "keywords": ["SQL"],
        },
        "noisy_llm": {
            "job_title": "Graduate Trainee — Software Development",
            "location": "Chennai",
            "must_have_skills": ["Java or Python", "SQL", "good communication"],
            "preferred_skills": ["data structures"],
            "education": ["B.E. / B.Tech 2024 or 2025 batch"],
            "responsibilities": ["complete training modules"],
            "keywords": ["SQL"],
        },
    },
    {
        "id": "remote_job",
        "category": "Remote job",
        "job_description": """
Backend Engineer (Remote, anywhere)
Fully remote. Full-time. 4+ years.

Must have: Go, PostgreSQL, gRPC
Preferred: Kubernetes

Education: not specified

Design distributed services and on-call support.
""",
        "expected": {
            "job_title": "Backend Engineer",
            "experience_min": 4,
            "experience_max": None,
            "location": None,
            "work_mode": "Remote",
            "employment_type": "Full-time",
            "must_have_skills": ["Go", "PostgreSQL"],
            "preferred_skills": ["Kubernetes"],
            "education": [],
            "responsibilities": ["distributed services"],
            "keywords": ["Go", "PostgreSQL"],
        },
        "noisy_llm": {
            "job_title": "Backend Engineer",
            "location": "anywhere",
            "must_have_skills": ["Go", "PostgreSQL", "gRPC"],
            "preferred_skills": ["k8s"],
            "education": [],
            "responsibilities": ["Design distributed services"],
            "keywords": ["Go", "PostgreSQL"],
        },
    },
    {
        "id": "hybrid_job",
        "category": "Hybrid job",
        "job_description": """
Python Developer — Hybrid
Noida. Hybrid, 2 days from office. Full-time. 2-4 years.

Must have: Python, FastAPI, SQL
Preferred: Docker

Education: Bachelor's

Ship APIs and collaborate with product.
""",
        "expected": {
            "job_title": "Python Developer",
            "experience_min": 2,
            "experience_max": 4,
            "location": "Noida",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "FastAPI", "SQL"],
            "preferred_skills": ["Docker"],
            "education": ["Bachelor's"],
            "responsibilities": ["APIs"],
            "keywords": ["Python", "FastAPI"],
        },
        "noisy_llm": {
            "job_title": "Python Developer",
            "location": "Noida",
            "must_have_skills": ["Python", "FastAPI", "SQL"],
            "preferred_skills": ["Docker"],
            "education": ["Bachelor's"],
            "responsibilities": ["Ship APIs"],
            "keywords": ["Python"],
        },
    },
    {
        "id": "contract_position",
        "category": "Contract position",
        "job_description": """
Contract Data Engineer
6-month contractor role. Remote. 2+ years.

Required: SQL, Airflow, Snowflake
Preferred: dbt, Python

Education: equivalent experience accepted

Build pipelines and document datasets.
""",
        "expected": {
            "job_title": "Contract Data Engineer",
            "experience_min": 2,
            "experience_max": None,
            "location": None,
            "work_mode": "Remote",
            "employment_type": "Contract",
            "must_have_skills": ["SQL", "Airflow", "Snowflake"],
            "preferred_skills": ["dbt", "Python"],
            "education": ["equivalent experience"],
            "responsibilities": ["pipelines"],
            "keywords": ["SQL", "Airflow"],
        },
        "noisy_llm": {
            "job_title": "Contract Data Engineer",
            "must_have_skills": ["SQL", "Airflow", "Snowflake"],
            "preferred_skills": ["dbt", "Python"],
            "education": ["equivalent experience accepted"],
            "responsibilities": ["Build pipelines"],
            "keywords": ["SQL", "Airflow"],
        },
    },
    {
        "id": "missing_salary",
        "category": "JD with missing salary",
        "job_description": """
Python Developer
Pune, hybrid, full-time. 3-5 years.

Must have: Python, Django, REST
Preferred: Celery

Education: Bachelor's

Build web services and review code.

Compensation: not mentioned in this posting.
""",
        "expected": {
            "job_title": "Python Developer",
            "experience_min": 3,
            "experience_max": 5,
            "location": "Pune",
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["Python", "Django"],
            "preferred_skills": ["Celery"],
            "education": ["Bachelor's"],
            "responsibilities": ["web services"],
            "keywords": ["Python", "Django"],
        },
        "noisy_llm": {
            "job_title": "Python Developer",
            "location": "Pune",
            "must_have_skills": ["Python", "Django", "REST"],
            "preferred_skills": ["Celery"],
            "education": ["Bachelor's"],
            "responsibilities": ["Build web services"],
            "keywords": ["Python"],
        },
    },
    {
        "id": "missing_location",
        "category": "JD with missing location",
        "job_description": """
Product Analyst
Full-time, hybrid. 3-5 years of experience.
Salary: 12-18 LPA.

Must have: SQL, Excel, product sense
Preferred: Amplitude

Education: Bachelor's

Define metrics, analyze funnels, partner with PM.

Note: office location is not specified.
""",
        "expected": {
            "job_title": "Product Analyst",
            "experience_min": 3,
            "experience_max": 5,
            "location": None,
            "work_mode": "Hybrid",
            "employment_type": "Full-time",
            "must_have_skills": ["SQL", "Excel"],
            "preferred_skills": ["Amplitude"],
            "education": ["Bachelor's"],
            "responsibilities": ["metrics"],
            "keywords": ["SQL", "Excel"],
        },
        "noisy_llm": {
            "job_title": "Product Analyst",
            "location": "Mumbai",
            "must_have_skills": ["SQL", "Excel", "product sense"],
            "preferred_skills": ["Amplitude"],
            "education": ["Bachelor's"],
            "responsibilities": ["Define metrics"],
            "keywords": ["SQL", "Excel"],
        },
    },
    {
        "id": "freelance_writer_adjacent",
        "category": "Contract position",
        "job_description": """
Freelance Technical Writer
Remote. Freelance / contract. 2+ years writing about APIs.

Must have: technical writing, Markdown, REST APIs
Preferred: OpenAPI, Python

Education: any

Write developer docs and tutorials. No office location.
""",
        "expected": {
            "job_title": "Freelance Technical Writer",
            "experience_min": 2,
            "experience_max": None,
            "location": None,
            "work_mode": "Remote",
            "employment_type": "Freelance",
            "must_have_skills": ["technical writing", "Markdown"],
            "preferred_skills": ["OpenAPI", "Python"],
            "education": [],
            "responsibilities": ["developer docs"],
            "keywords": ["Markdown", "REST"],
        },
        "noisy_llm": {
            "job_title": "Freelance Technical Writer",
            "must_have_skills": ["technical writing", "Markdown", "REST APIs"],
            "preferred_skills": ["OpenAPI", "Python"],
            "education": [],
            "responsibilities": ["Write developer docs"],
            "keywords": ["Markdown"],
        },
    },
    {
        "id": "part_time_support",
        "category": "Hybrid job",
        "job_description": """
Customer Support Specialist
Kolkata, hybrid, part-time. 1-3 years.

Must have: communication, Zendesk, English
Preferred: SQL

Education: Any graduate

Resolve tickets, escalate bugs, update the knowledge base.
""",
        "expected": {
            "job_title": "Customer Support Specialist",
            "experience_min": 1,
            "experience_max": 3,
            "location": "Kolkata",
            "work_mode": "Hybrid",
            "employment_type": "Part-time",
            "must_have_skills": ["Zendesk", "English"],
            "preferred_skills": ["SQL"],
            "education": ["Any graduate"],
            "responsibilities": ["tickets"],
            "keywords": ["Zendesk"],
        },
        "noisy_llm": {
            "job_title": "Customer Support Specialist",
            "location": "Kolkata",
            "must_have_skills": ["communication", "Zendesk", "English"],
            "preferred_skills": ["SQL"],
            "education": ["Any graduate"],
            "responsibilities": ["Resolve tickets"],
            "keywords": ["Zendesk"],
        },
    },
]


REQUIRED_CATEGORIES = {
    "Software Developer",
    "Java Developer",
    "Python Developer",
    "Full Stack Developer",
    "React Developer",
    "AI/ML Engineer",
    "Data Analyst",
    "Data Scientist",
    "DevOps Engineer",
    "QA Engineer",
    "UI/UX Designer",
    "HR Executive",
    "Sales Executive",
    "Internship",
    "Fresher position",
    "Remote job",
    "Hybrid job",
    "Contract position",
    "JD with missing salary",
    "JD with missing location",
}
