# Resume Agent evaluation report

Mode: `offline_noisy_llm_plus_normalization`
Cases: 11
Cases fully passing: 11/11
Overall field accuracy: 100.0%

Live LLM was not used. Each case feeds a noisy structured payload through ResumeAgent validation and grounding, then scores against human labels.

## Field accuracy

| Field | Accuracy |
| --- | --- |
| name | 100.0% |
| skills | 100.0% |
| experience | 100.0% |
| education | 100.0% |
| job_titles | 100.0% |
| companies | 100.0% |
| projects | 100.0% |
| certifications | 100.0% |
| location | 100.0% |
| availability | 100.0% |
| email | 100.0% |
| phone | 100.0% |

## Case results

- `software_engineer` (Software engineer): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `ai_ml_engineer` (AI/ML engineer): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `data_scientist` (Data scientist): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `fresh_graduate` (Fresh graduate): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `senior_candidate` (Senior candidate): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `missing_email` (Missing email): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability, email
  - failed fields: none
  - missing fields: none
- `missing_phone` (Missing phone): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability, phone
  - failed fields: none
  - missing fields: none
- `multiple_companies` (Multiple companies): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `multiple_projects` (Multiple projects): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `unclear_experience_dates` (Unclear experience dates): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability
  - failed fields: none
  - missing fields: none
- `missing_phone_and_availability_stated` (Missing phone): PASS 100%
  - passed fields: name, skills, experience, education, job_titles, companies, projects, certifications, location, availability, phone
  - failed fields: none
  - missing fields: none

## Notes

- Resume Agent production code was not changed for this evaluation.
- Invented contact details, availability, and unsupported experience totals are dropped by grounding.
- Re-run live Gemini evaluation by setting GOOGLE_API_KEY and calling ResumeAgent.parse without a mock.
