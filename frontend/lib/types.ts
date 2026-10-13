export type JobSummary = {
  job_id: string;
  job_title: string | null;
  location: string | null;
  work_mode: string | null;
  employment_type: string | null;
  matched_count: number;
  open_to_work_count: number;
  pending_review_count: number;
  approved_count: number;
  rejected_count: number;
  on_hold_count: number;
};

export type CandidateRow = {
  candidate_id: string;
  name: string | null;
  match_percent: number;
  availability_status: string;
  eligible_for_outreach: boolean;
  review_status: string;
  workflow_status?: string;
  explanation: string;
  matched_requirements: string[];
  missing_requirements: string[];
  confidence: number;
  current_job_title: string | null;
  location: string | null;
  has_resume: boolean;
  requirement_match_source: string;
  explanation_source: string;
  review_source: string;
};

export type Dashboard = JobSummary & {
  experience_min: number | null;
  experience_max: number | null;
  must_have_skills: string[];
  preferred_skills: string[];
  education: string[];
  responsibilities: string[];
  candidates: CandidateRow[];
};

export type ResumeAccess = {
  resume_id: string;
  file_name: string | null;
  source: string | null;
  content_type: string | null;
  byte_size: number | null;
  available_on_server: boolean;
  download_path: string | null;
};

export type CandidateProfile = {
  job_id: string;
  job_title: string | null;
  candidate_id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  current_job_title: string | null;
  total_experience_years: number | null;
  technical_skills: string[];
  skills: string[];
  soft_skills: string[];
  education: unknown[];
  certifications: unknown[];
  previous_roles: unknown[];
  projects: unknown[];
  companies: string[];
  achievements: string[];
  industries: string[];
  resume_summary: string | null;
  resumes: ResumeAccess[];
  availability_status: string;
  open_to_work_source: string | null;
  eligible_for_outreach: boolean;
  match_percent: number;
  requirement_match_source: string;
  matched_requirements: string[];
  missing_requirements: string[];
  explanation_source: string;
  explanation: string;
  confidence: number;
  review_source: string;
  review_status: string;
  workflow_status?: string;
  communications_sent: boolean;
};

export type DecisionResponse = {
  review_status: string;
  message: string;
  communications_sent: boolean;
};

export type OutreachDraft = {
  candidate_id: string;
  job_id: string;
  subject: string;
  body: string;
  personalization_points: string[];
  generated_at: string;
  template: string;
  review_status: string;
  email_sent: boolean;
  recruiter_id?: string | null;
  message: string;
};

export type EmailSendResult = {
  message_id: string;
  candidate_id: string;
  job_id: string;
  recipient: string;
  sent_at: string;
  delivery_status: string;
  template: string;
  provider: string;
  dry_run: boolean;
  email_sent: boolean;
  recruiter_id?: string | null;
  message: string;
};

export type PipelineRun = {
  job_id: string;
  sourced_count: number;
  matched_count: number;
  ranked_count: number;
  shortlist_recorded: boolean;
  outreach_sent: boolean;
  hired: boolean;
  errors: string[];
  message: string;
};

export type InterviewSlot = {
  start_at: string;
  end_at: string;
  timezone?: string;
};

export type InterviewRecord = {
  job_id: string;
  candidate_id: string;
  status: string;
  timezone: string;
  duration_minutes: number;
  proposed_slots: InterviewSlot[];
  start_at: string | null;
  end_at: string | null;
  calendar_event_id: string | null;
  calendar_booked: boolean;
  recruiter_id?: string | null;
  message: string;
};
