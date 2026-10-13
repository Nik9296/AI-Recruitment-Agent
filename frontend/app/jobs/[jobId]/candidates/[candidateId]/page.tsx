"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import AppHeader from "@/app/components/AppHeader";
import { api, ApiError, downloadAuthorized } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { CandidateProfile, EmailSendResult, InterviewRecord, OutreachDraft } from "@/lib/types";

function asList(value: unknown[]): string {
  return value
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      if (item && typeof item === "object") {
        return Object.values(item)
          .filter((entry) => entry !== null && entry !== "")
          .join(" · ");
      }
      return "";
    })
    .filter(Boolean)
    .join("; ");
}

export default function CandidateReviewPage() {
  const params = useParams<{ jobId: string; candidateId: string }>();
  const router = useRouter();
  const { jobId, candidateId } = params;
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [draft, setDraft] = useState<OutreachDraft | null>(null);
  const [interview, setInterview] = useState<InterviewRecord | null>(null);
  const [template, setTemplate] = useState("initial");
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = useCallback(async () => {
    const body = await api<CandidateProfile>(
      `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}`
    );
    setProfile(body);
    try {
      const saved = await api<OutreachDraft>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/outreach?template=${template}`
      );
      setDraft(saved);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setDraft(null);
      } else {
        throw err;
      }
    }
    try {
      const record = await api<InterviewRecord>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/interview`
      );
      setInterview(record);
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) {
        setInterview(null);
      } else {
        throw err;
      }
    }
  }, [candidateId, jobId, template]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<{ username: string }>("/api/v1/recruiter/me")
      .then((me) => setUsername(me.username))
      .catch(() => undefined);
    load().catch((err: Error) => setError(err.message));
  }, [load, router]);

  async function decide(action: "approve" | "reject" | "hold") {
    const body = await api<{ message: string }>(
      `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/${action}`,
      { method: "POST" }
    );
    setNotice(body.message);
    await load();
  }

  async function queueOutreach() {
    try {
      const body = await api<{ message: string }>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/outreach-handoff`,
        { method: "POST" }
      );
      setNotice(body.message);
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Queue outreach failed");
    }
  }

  async function generateDraft() {
    try {
      const body = await api<OutreachDraft>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/outreach`,
        {
          method: "POST",
          body: JSON.stringify({ template }),
        }
      );
      setDraft(body);
      setNotice(body.message);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Draft generation failed");
    }
  }

  async function sendDraft() {
    try {
      const body = await api<EmailSendResult>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/outreach/send`,
        {
          method: "POST",
          body: JSON.stringify({ template }),
        }
      );
      setNotice(body.message);
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Send failed");
    }
  }

  async function inviteToInterview() {
    try {
      const body = await api<{ workflow_status: string }>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/interview/invite`,
        { method: "POST" }
      );
      setNotice(`Interview invited. Workflow: ${body.workflow_status}`);
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Invite failed");
    }
  }

  async function proposeInterview() {
    try {
      const body = await api<InterviewRecord>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/interview/proposals`,
        { method: "POST" }
      );
      setInterview(body);
      setNotice(body.message);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Propose times failed");
    }
  }

  async function confirmInterview(slot: { start_at: string; end_at: string }) {
    try {
      const body = await api<InterviewRecord>(
        `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/interview/confirm`,
        {
          method: "POST",
          body: JSON.stringify({ start_at: slot.start_at, end_at: slot.end_at }),
        }
      );
      setInterview(body);
      setNotice(body.message);
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Confirm failed");
    }
  }

  if (error) {
    return (
      <div className="shell">
        <AppHeader username={username} />
        <p className="error">{error}</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="shell">
        <AppHeader username={username} />
        <section className="page-head reveal">
          <h1>Loading candidate...</h1>
          <p className="muted">Fetching profile and recruiter tools.</p>
        </section>
        <section className="grid">
          <article className="card skeleton-block" />
          <article className="card skeleton-block" />
          <article className="card skeleton-block" />
        </section>
      </div>
    );
  }

  return (
    <div className="shell">
      <AppHeader username={username} />
      <p className="back-link">
        <Link href={`/jobs/${jobId}`}>← {profile.job_title || "Job"}</Link>
      </p>
      <section className="page-head reveal">
        <h1>{profile.name || "Unnamed candidate"}</h1>
        <p>
          {profile.current_job_title || "Role not stated"}
          {profile.location ? ` · ${profile.location}` : ""}
        </p>
      </section>
      <div className="grid reveal">
        <article className="card recruiter glow-card">
          <h2>Recruiter decision</h2>
          <p className="source">Source: recruiter · not AI</p>
          <p>Recruiter status: {profile.review_status}</p>
          <p>Workflow: {profile.workflow_status || profile.review_status}</p>
          <p>Open to work: {profile.availability_status}</p>
          {profile.open_to_work_source ? (
            <p>Availability source: {profile.open_to_work_source}</p>
          ) : (
            <p>No explicit open-to-work signal.</p>
          )}
          <p>Eligible for later outreach: {profile.eligible_for_outreach ? "yes" : "no"}</p>
          <p>Communications sent: {profile.communications_sent ? "yes" : "no"}</p>
          <div className="actions">
            <button type="button" className="approve" onClick={() => void decide("approve")}>
              Approve
            </button>
            <button type="button" className="hold" onClick={() => void decide("hold")}>
              Hold
            </button>
            <button type="button" className="reject" onClick={() => void decide("reject")}>
              Reject
            </button>
            <button type="button" className="hold" onClick={() => void queueOutreach()}>
              Queue outreach
            </button>
          </div>
        </article>
        <article className="card deterministic glow-card">
          <h2>Deterministic requirement matching</h2>
          <p className="source">Source: {profile.requirement_match_source}</p>
          <p>Match: {profile.match_percent}%</p>
          <p>Matched: {profile.matched_requirements.join("; ") || "none recorded"}</p>
          <p>Missing: {profile.missing_requirements.join("; ") || "none recorded"}</p>
        </article>
        <article className="card ai glow-card">
          <h2>Matching agent insight</h2>
          <p className="source">Source: {profile.explanation_source} · not a hiring decision</p>
          <p>{profile.explanation}</p>
          <p>Confidence: {Math.round(profile.confidence * 100)}%</p>
        </article>
      </div>
      <article className="card reveal">
        <h2>Candidate profile</h2>
        <p>Email: {profile.email || "not stated"}</p>
        <p>Phone: {profile.phone || "not stated"}</p>
        <p>
          Experience:{" "}
          {profile.total_experience_years != null
            ? `${profile.total_experience_years} years`
            : "not stated"}
        </p>
        <p>Skills: {profile.skills.join(", ") || "not stated"}</p>
        <p>Technical skills: {profile.technical_skills.join(", ") || "not stated"}</p>
        <p>Education: {asList(profile.education) || "not stated"}</p>
        <p>Previous roles: {asList(profile.previous_roles) || "not stated"}</p>
        <p>Projects: {asList(profile.projects) || "not stated"}</p>
        <p>Summary: {profile.resume_summary || "not stated"}</p>
      </article>
      <article className="card reveal">
        <h2>Resume access</h2>
        {profile.resumes.length === 0 ? (
          <p>No resume file is stored for this candidate.</p>
        ) : (
          <ul>
            {profile.resumes.map((resume) => (
              <li key={resume.resume_id}>
                {resume.file_name || "Resume"} ({resume.source || "source not stated"})
                {resume.available_on_server && resume.download_path ? (
                  <button
                    type="button"
                    className="text-btn"
                    onClick={() =>
                      void downloadAuthorized(
                        resume.download_path as string,
                        resume.file_name || "resume"
                      )
                    }
                  >
                    Download
                  </button>
                ) : (
                  <span className="muted"> — file not available on this server</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </article>
      <article className="card recruiter reveal">
        <h2>Outreach draft</h2>
        <p className="source">Source: Outreach Agent · recruiter review required · not sent</p>
        <label>
          Template
          <select value={template} onChange={(event) => setTemplate(event.target.value)}>
            <option value="initial">Initial outreach</option>
            <option value="interview_invitation">Interview invitation</option>
            <option value="follow_up">Follow-up</option>
          </select>
        </label>
        <div className="actions">
          <button type="button" className="approve" onClick={() => void generateDraft()}>
            Generate draft
          </button>
          <button
            type="button"
            className="hold"
            onClick={() => void sendDraft()}
            disabled={!draft || draft.email_sent}
          >
            Send email
          </button>
        </div>
        {draft ? (
          <>
            <p>Status: {draft.review_status}</p>
            <p>Email sent: {draft.email_sent ? "yes" : "no"}</p>
            <p>
              <strong>Subject:</strong> {draft.subject}
            </p>
            <pre className="draft-body">{draft.body}</pre>
            <p>Personalization points</p>
            <ul>
              {draft.personalization_points.length === 0 ? (
                <li>None — profile facts were limited</li>
              ) : (
                draft.personalization_points.map((point) => <li key={point}>{point}</li>)
              )}
            </ul>
          </>
        ) : (
          <p>No draft yet. Approve the candidate, then generate a message to review.</p>
        )}
      </article>
      <article className="card recruiter reveal">
        <h2>Interview scheduling</h2>
        <p className="source">
          Source: Scheduling Agent · recruiter confirmation required · calendar dry-run by default
        </p>
        <p>Workflow: {profile.workflow_status || profile.review_status}</p>
        <div className="actions">
          <button
            type="button"
            className="hold"
            onClick={() => void inviteToInterview()}
            disabled={
              profile.workflow_status !== "CONTACTED" &&
              profile.workflow_status !== "RESPONDED"
            }
          >
            Invite to interview
          </button>
          <button
            type="button"
            className="approve"
            onClick={() => void proposeInterview()}
            disabled={profile.workflow_status !== "INTERVIEW_INVITED"}
          >
            Propose times
          </button>
        </div>
        {interview ? (
          <>
            <p>Status: {interview.status}</p>
            <p>Calendar booked: {interview.calendar_booked ? "yes" : "no"}</p>
            {interview.start_at ? (
              <p>
                Confirmed: {new Date(interview.start_at).toLocaleString()} –{" "}
                {interview.end_at ? new Date(interview.end_at).toLocaleString() : ""}
              </p>
            ) : null}
            {interview.status === "proposed" && interview.proposed_slots.length > 0 ? (
              <ul>
                {interview.proposed_slots.map((slot) => (
                  <li key={slot.start_at}>
                    {new Date(slot.start_at).toLocaleString()} –{" "}
                    {new Date(slot.end_at).toLocaleString()}
                    <button
                      type="button"
                      className="approve"
                      onClick={() => void confirmInterview(slot)}
                    >
                      Confirm this slot
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
            <p>{interview.message}</p>
          </>
        ) : (
          <p>
            Invite after outreach is sent, then propose times. No calendar event is created until
            you confirm a slot.
          </p>
        )}
      </article>
      {notice ? <p className="notice">{notice}</p> : null}
    </div>
  );
}
