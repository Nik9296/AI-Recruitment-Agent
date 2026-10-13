# JD Agent evaluation report

Mode: `offline_noisy_llm_plus_normalization`
Cases: 22
Cases fully passing: 22/22
Overall field accuracy: 100.0%

Live Gemini was not used. Each case feeds a noisy structured LLM payload through JDAgent validation and normalization, then scores against human labels.

## Field accuracy

| Field | Accuracy |
| --- | --- |
| title | 100.0% |
| experience_min | 100.0% |
| experience_max | 100.0% |
| location | 100.0% |
| work_mode | 100.0% |
| employment_type | 100.0% |
| must_have_skills | 100.0% |
| preferred_skills | 100.0% |
| education | 100.0% |
| responsibilities | 100.0% |
| keywords | 100.0% |

## Case results

- `software_developer` (Software Developer): PASS 100%
- `java_developer` (Java Developer): PASS 100%
- `python_developer` (Python Developer): PASS 100%
- `full_stack_developer` (Full Stack Developer): PASS 100%
- `react_developer` (React Developer): PASS 100%
- `ai_ml_engineer` (AI/ML Engineer): PASS 100%
- `data_analyst` (Data Analyst): PASS 100%
- `data_scientist` (Data Scientist): PASS 100%
- `devops_engineer` (DevOps Engineer): PASS 100%
- `qa_engineer` (QA Engineer): PASS 100%
- `ui_ux_designer` (UI/UX Designer): PASS 100%
- `hr_executive` (HR Executive): PASS 100%
- `sales_executive` (Sales Executive): PASS 100%
- `internship` (Internship): PASS 100%
- `fresher_position` (Fresher position): PASS 100%
- `remote_job` (Remote job): PASS 100%
- `hybrid_job` (Hybrid job): PASS 100%
- `contract_position` (Contract position): PASS 100%
- `missing_salary` (JD with missing salary): PASS 100%
- `missing_location` (JD with missing location): PASS 100%
- `freelance_writer_adjacent` (Contract position): PASS 100%
- `part_time_support` (Hybrid job): PASS 100%

## Notes

- Architecture was not changed.
- Prompt, schema aliases, and normalization were tightened for experience phrases, work mode, employment type, skill aliases, and invented locations.
- Re-run live Gemini evaluation by setting GOOGLE_API_KEY and calling JDAgent without a mock.
