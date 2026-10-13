"""Labeled Resume Agent evaluation dataset (10+ formats)."""

REQUIRED_CATEGORIES = {
    "Software engineer",
    "AI/ML engineer",
    "Data scientist",
    "Fresh graduate",
    "Senior candidate",
    "Missing email",
    "Missing phone",
    "Multiple companies",
    "Multiple projects",
    "Unclear experience dates",
}

RESUME_CASES: list[dict] = [
    {
        "id": "software_engineer",
        "category": "Software engineer",
        "resume_text": """
Priya Shah
priya.shah@example.com
+91 98111 22334
Bengaluru, India

Backend engineer with 5 years of experience.

Experience
Software Engineer, Nimbus Labs
2021 - Present
- Built Python APIs with FastAPI

Education
B.Tech in Computer Science, RV College of Engineering, 2016-2020

Certifications
AWS Certified Developer, Amazon, 2023

Projects
Order Service - order APIs in Python

Availability: Immediate
""",
        "expected": {
            "full_name": "Priya Shah",
            "location": "Bengaluru",
            "total_experience_years": 5,
            "technical_skills": ["Python", "FastAPI"],
            "job_titles": ["Software Engineer"],
            "companies": ["Nimbus Labs"],
            "education": [{"institution": "RV College of Engineering", "degree": "B.Tech"}],
            "projects": ["Order Service"],
            "certifications": ["AWS Certified Developer"],
            "availability": "Immediate",
        },
        "noisy_llm": {
            "full_name": "Priya Shah",
            "email": "priya.shah@example.com",
            "phone": "98111 22334",
            "location": "Bengaluru, India",
            "current_job_title": "Software Engineer",
            "total_experience_years": None,
            "technical_skills": ["py", "FastAPI"],
            "soft_skills": [],
            "previous_roles": [
                {"title": "Software Engineer", "company": "Nimbus Labs"}
            ],
            "education": [
                {
                    "institution": "RV College of Engineering",
                    "degree": "B.Tech",
                    "field": "Computer Science",
                }
            ],
            "projects": [{"name": "Order Service", "technologies": ["Python"]}],
            "certifications": [{"name": "AWS Certified Developer", "issuer": "Amazon"}],
            "availability": "Immediate",
        },
    },
    {
        "id": "ai_ml_engineer",
        "category": "AI/ML engineer",
        "resume_text": """
Rahul Mehta
rahul.mehta@example.com
Hyderabad

AI/ML Engineer with 4 years of experience.

Technical skills: Python, TensorFlow, PyTorch, k8s
Soft skills: Communication

Experience
ML Engineer, VectorAI
2022 - Present
- Trained ranking models

Education
M.Tech in Machine Learning, IIIT Hyderabad

Certifications
TensorFlow Developer Certificate, Google, 2022

Projects
Resume Ranker - ranking models in PyTorch

Notice period: 60 days
""",
        "expected": {
            "full_name": "Rahul Mehta",
            "location": "Hyderabad",
            "total_experience_years": 4,
            "technical_skills": ["Python", "TensorFlow", "PyTorch", "Kubernetes"],
            "job_titles": ["ML Engineer"],
            "companies": ["VectorAI"],
            "education": [{"institution": "IIIT Hyderabad", "degree": "M.Tech"}],
            "projects": ["Resume Ranker"],
            "certifications": ["TensorFlow Developer Certificate"],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Rahul Mehta",
            "email": "rahul.mehta@example.com",
            "location": "Hyderabad",
            "current_job_title": "ML Engineer",
            "total_experience_years": 4,
            "technical_skills": ["Python", "tf", "PyTorch", "k8s"],
            "soft_skills": ["Communication"],
            "previous_roles": [{"title": "ML Engineer", "company": "VectorAI"}],
            "education": [
                {
                    "institution": "IIIT Hyderabad",
                    "degree": "M.Tech",
                    "field": "Machine Learning",
                }
            ],
            "projects": [{"name": "Resume Ranker", "technologies": ["PyTorch"]}],
            "certifications": [
                {"name": "TensorFlow Developer Certificate", "issuer": "Google"}
            ],
            "availability": "next month",
            "notice_period": "60 days",
        },
    },
    {
        "id": "data_scientist",
        "category": "Data scientist",
        "resume_text": """
Ananya Rao
ananya.rao@example.com
+91 99000 11122
Pune, India

Data Scientist with 3 years of experience.

Skills: Python, SQL, pandas, scikit-learn, Power BI

Experience
Data Scientist, InsightWorks
2023 - Present

Education
M.Sc Statistics, Savitribai Phule Pune University

Projects
Churn Model - customer churn using scikit-learn

Certifications
Google Data Analytics, Google, 2021
""",
        "expected": {
            "full_name": "Ananya Rao",
            "location": "Pune",
            "total_experience_years": 3,
            "technical_skills": ["Python", "SQL", "scikit-learn", "Power BI"],
            "job_titles": ["Data Scientist"],
            "companies": ["InsightWorks"],
            "education": [{"institution": "Savitribai Phule Pune University", "degree": "M.Sc"}],
            "projects": ["Churn Model"],
            "certifications": ["Google Data Analytics"],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Ananya Rao",
            "email": "ananya.rao@example.com",
            "phone": "99000 11122",
            "location": "Pune, India",
            "current_job_title": "Data Scientist",
            "total_experience_years": 3,
            "technical_skills": ["Python", "SQL", "sklearn", "powerbi"],
            "previous_roles": [{"title": "Data Scientist", "company": "InsightWorks"}],
            "education": [
                {
                    "institution": "Savitribai Phule Pune University",
                    "degree": "M.Sc",
                    "field": "Statistics",
                }
            ],
            "projects": [{"name": "Churn Model", "technologies": ["scikit-learn"]}],
            "certifications": [{"name": "Google Data Analytics", "issuer": "Google"}],
        },
    },
    {
        "id": "fresh_graduate",
        "category": "Fresh graduate",
        "resume_text": """
Arjun Nair
arjun.nair@example.com
Chennai

Fresh graduate, B.E. Computer Science, Anna University, 2024.

Internship
Software Intern, BrightApps
Jun 2023 - Aug 2023
- Wrote unit tests in Python

Projects
Campus Portal - student dashboard in React.js

Skills: Python, React.js, SQL
""",
        "expected": {
            "full_name": "Arjun Nair",
            "location": "Chennai",
            "total_experience_years": None,
            "technical_skills": ["Python", "React", "SQL"],
            "job_titles": ["Software Intern"],
            "companies": ["BrightApps"],
            "education": [{"institution": "Anna University", "degree": "B.E."}],
            "projects": ["Campus Portal"],
            "certifications": [],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Arjun Nair",
            "email": "arjun.nair@example.com",
            "location": "Chennai",
            "current_job_title": "Software Intern",
            "total_experience_years": 1,
            "technical_skills": ["Python", "React.js", "SQL"],
            "previous_roles": [
                {"title": "Software Intern", "company": "BrightApps"}
            ],
            "education": [
                {
                    "institution": "Anna University",
                    "degree": "B.E.",
                    "field": "Computer Science",
                    "end_year": 2024,
                }
            ],
            "projects": [{"name": "Campus Portal", "technologies": ["React.js"]}],
            "availability": "Immediate",
        },
    },
    {
        "id": "senior_candidate",
        "category": "Senior candidate",
        "resume_text": """
Vikram Iyer
vikram.iyer@example.com
+91 98222 33445
Mumbai

Senior Engineering Manager with 12 years of experience.

Experience
Director of Engineering, Northstar
2019 - Present
Engineering Manager, Helio Systems
2014 - 2019

Skills: Java, Kubernetes, leadership, mentoring

Education
B.Tech, IIT Bombay

Certifications
CKA, Cloud Native Computing Foundation, 2020

Projects
Platform Rebuild - migrated monolith to microservices on k8s

Available from September
""",
        "expected": {
            "full_name": "Vikram Iyer",
            "location": "Mumbai",
            "total_experience_years": 12,
            "technical_skills": ["Java", "Kubernetes"],
            "job_titles": ["Director of Engineering", "Engineering Manager"],
            "companies": ["Northstar", "Helio Systems"],
            "education": [{"institution": "IIT Bombay", "degree": "B.Tech"}],
            "projects": ["Platform Rebuild"],
            "certifications": ["CKA"],
            "availability": "September",
        },
        "noisy_llm": {
            "full_name": "Vikram Iyer",
            "email": "vikram.iyer@example.com",
            "phone": "98222 33445",
            "location": "Mumbai",
            "current_job_title": "Director of Engineering",
            "total_experience_years": 12,
            "technical_skills": ["Java", "k8s"],
            "soft_skills": ["leadership", "mentoring"],
            "previous_roles": [
                {"title": "Director of Engineering", "company": "Northstar"},
                {"title": "Engineering Manager", "company": "Helio Systems"},
            ],
            "education": [{"institution": "IIT Bombay", "degree": "B.Tech"}],
            "projects": [{"name": "Platform Rebuild", "technologies": ["k8s"]}],
            "certifications": [
                {"name": "CKA", "issuer": "Cloud Native Computing Foundation"}
            ],
            "availability": "September",
        },
    },
    {
        "id": "missing_email",
        "category": "Missing email",
        "resume_text": """
Neha Kulkarni
+91 97654 32100
Pune

Frontend Engineer with 2 years of experience.

Experience
Frontend Engineer, Pixelhouse
2023 - Present

Skills: React, TypeScript, CSS

Education
B.Sc Computer Science, Fergusson College
""",
        "expected": {
            "full_name": "Neha Kulkarni",
            "email": None,
            "location": "Pune",
            "total_experience_years": 2,
            "technical_skills": ["React", "TypeScript", "CSS"],
            "job_titles": ["Frontend Engineer"],
            "companies": ["Pixelhouse"],
            "education": [{"institution": "Fergusson College", "degree": "B.Sc"}],
            "projects": [],
            "certifications": [],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Neha Kulkarni",
            "email": "neha.kulkarni@pixelhouse.com",
            "phone": "97654 32100",
            "location": "Pune",
            "current_job_title": "Frontend Engineer",
            "total_experience_years": 2,
            "technical_skills": ["React", "TS", "CSS"],
            "previous_roles": [
                {"title": "Frontend Engineer", "company": "Pixelhouse"}
            ],
            "education": [
                {
                    "institution": "Fergusson College",
                    "degree": "B.Sc",
                    "field": "Computer Science",
                }
            ],
        },
    },
    {
        "id": "missing_phone",
        "category": "Missing phone",
        "resume_text": """
Sanjay Pillai
sanjay.pillai@example.com
Kochi

DevOps Engineer with 6 years of experience.

Experience
DevOps Engineer, Cloudyard
2019 - Present

Skills: AWS, Docker, Kubernetes, Terraform

Education
MCA, Cochin University

Certifications
AWS Solutions Architect, Amazon, 2021
""",
        "expected": {
            "full_name": "Sanjay Pillai",
            "phone": None,
            "location": "Kochi",
            "total_experience_years": 6,
            "technical_skills": ["AWS", "Docker", "Kubernetes", "Terraform"],
            "job_titles": ["DevOps Engineer"],
            "companies": ["Cloudyard"],
            "education": [{"institution": "Cochin University", "degree": "MCA"}],
            "projects": [],
            "certifications": ["AWS Solutions Architect"],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Sanjay Pillai",
            "email": "sanjay.pillai@example.com",
            "phone": "99999 88888",
            "location": "Kochi",
            "current_job_title": "DevOps Engineer",
            "total_experience_years": 6,
            "technical_skills": ["AWS", "Docker", "k8s", "Terraform"],
            "previous_roles": [{"title": "DevOps Engineer", "company": "Cloudyard"}],
            "education": [{"institution": "Cochin University", "degree": "MCA"}],
            "certifications": [
                {"name": "AWS Solutions Architect", "issuer": "Amazon"}
            ],
        },
    },
    {
        "id": "multiple_companies",
        "category": "Multiple companies",
        "resume_text": """
Meera Joshi
meera.joshi@example.com
Delhi

Full Stack Engineer with 7 years of experience.

Experience
Staff Engineer, Orion Tech
2022 - Present
Senior Developer, BluePeak
2019 - 2022
Developer, Ampersand
2017 - 2019

Skills: JavaScript, Node.js, Java, PostgreSQL

Education
B.Tech, DTU

Projects
Billing Hub - invoicing service
""",
        "expected": {
            "full_name": "Meera Joshi",
            "location": "Delhi",
            "total_experience_years": 7,
            "technical_skills": ["JavaScript", "Node.js", "Java", "PostgreSQL"],
            "job_titles": ["Staff Engineer", "Senior Developer", "Developer"],
            "companies": ["Orion Tech", "BluePeak", "Ampersand"],
            "education": [{"institution": "DTU", "degree": "B.Tech"}],
            "projects": ["Billing Hub"],
            "certifications": [],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Meera Joshi",
            "email": "meera.joshi@example.com",
            "location": "Delhi",
            "current_job_title": "Staff Engineer",
            "total_experience_years": 7,
            "technical_skills": ["JS", "nodejs", "Java", "Postgres"],
            "previous_roles": [
                {"title": "Staff Engineer", "company": "Orion Tech"},
                {"title": "Senior Developer", "company": "BluePeak"},
                {"title": "Developer", "company": "Ampersand"},
            ],
            "education": [{"institution": "DTU", "degree": "B.Tech"}],
            "projects": [{"name": "Billing Hub"}],
            "companies": ["Orion Tech"],
        },
    },
    {
        "id": "multiple_projects",
        "category": "Multiple projects",
        "resume_text": """
Kabir Ali
kabir.ali@example.com
Noida

Software Engineer with 3 years of experience.

Experience
Software Engineer, Harbor Digital
2022 - Present

Skills: Python, React, PostgreSQL

Education
B.Tech, JSS Noida

Projects
1. Inventory Tracker - warehouse stock in Python
2. Support Desk - ticketing UI in React
3. Payroll Export - CSV export jobs

Certifications
Scrum Master, Scrum.org, 2023
""",
        "expected": {
            "full_name": "Kabir Ali",
            "location": "Noida",
            "total_experience_years": 3,
            "technical_skills": ["Python", "React", "PostgreSQL"],
            "job_titles": ["Software Engineer"],
            "companies": ["Harbor Digital"],
            "education": [{"institution": "JSS Noida", "degree": "B.Tech"}],
            "projects": ["Inventory Tracker", "Support Desk", "Payroll Export"],
            "certifications": ["Scrum Master"],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Kabir Ali",
            "email": "kabir.ali@example.com",
            "location": "Noida",
            "current_job_title": "Software Engineer",
            "total_experience_years": 3,
            "technical_skills": ["Python", "React", "Postgres"],
            "previous_roles": [
                {"title": "Software Engineer", "company": "Harbor Digital"}
            ],
            "education": [{"institution": "JSS Noida", "degree": "B.Tech"}],
            "projects": [
                {"name": "Inventory Tracker", "technologies": ["Python"]},
                {"name": "Support Desk", "technologies": ["React"]},
                {"name": "Payroll Export"},
            ],
            "certifications": [{"name": "Scrum Master", "issuer": "Scrum.org"}],
        },
    },
    {
        "id": "unclear_experience_dates",
        "category": "Unclear experience dates",
        "resume_text": """
Leela Menon
leela.menon@example.com
Gurgaon

QA Engineer

Experience
QA Engineer, Softbridge
2019 - 
Test Analyst, sometime in 2016 or 2017, dates not recorded
Freelance testing, various clients

Skills: Selenium, Cypress, JS

Education
BCA, IGNOU

Projects
Regression Pack - nightly Selenium suite
""",
        "expected": {
            "full_name": "Leela Menon",
            "location": "Gurgaon",
            "total_experience_years": None,
            "technical_skills": ["Selenium", "Cypress", "JavaScript"],
            "job_titles": ["QA Engineer", "Test Analyst"],
            "companies": ["Softbridge"],
            "education": [{"institution": "IGNOU", "degree": "BCA"}],
            "projects": ["Regression Pack"],
            "certifications": [],
            "availability": None,
        },
        "noisy_llm": {
            "full_name": "Leela Menon",
            "email": "leela.menon@example.com",
            "location": "Gurgaon",
            "current_job_title": "QA Engineer",
            "total_experience_years": 8,
            "technical_skills": ["Selenium", "Cypress", "js"],
            "previous_roles": [
                {"title": "QA Engineer", "company": "Softbridge"},
                {"title": "Test Analyst"},
            ],
            "education": [{"institution": "IGNOU", "degree": "BCA"}],
            "projects": [{"name": "Regression Pack", "technologies": ["Selenium"]}],
        },
    },
    {
        "id": "missing_phone_and_availability_stated",
        "category": "Missing phone",
        "resume_text": """
Tara Singh
tara.singh@example.com
Jaipur

Product Designer with 4 years of experience.

Experience
Product Designer, Loomline
2021 - Present

Skills: Figma, CSS, user research

Education
B.Des, NID

Availability: 15 days
""",
        "expected": {
            "full_name": "Tara Singh",
            "phone": None,
            "location": "Jaipur",
            "total_experience_years": 4,
            "technical_skills": ["Figma", "CSS"],
            "job_titles": ["Product Designer"],
            "companies": ["Loomline"],
            "education": [{"institution": "NID", "degree": "B.Des"}],
            "projects": [],
            "certifications": [],
            "availability": "15 days",
        },
        "noisy_llm": {
            "full_name": "Tara Singh",
            "email": "tara.singh@example.com",
            "phone": "88888 77777",
            "location": "Jaipur",
            "current_job_title": "Product Designer",
            "total_experience_years": 4,
            "technical_skills": ["Figma", "CSS"],
            "soft_skills": ["user research"],
            "previous_roles": [
                {"title": "Product Designer", "company": "Loomline"}
            ],
            "education": [{"institution": "NID", "degree": "B.Des"}],
            "availability": "15 days",
        },
    },
]
