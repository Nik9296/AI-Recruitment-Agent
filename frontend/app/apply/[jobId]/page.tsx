"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";

type JobDetails = {
  id: string;
  job_title: string | null;
  location: string | null;
};

type ApplicationResponse = {
  candidate_id: string;
  message: string;
};

export default function JobApplyPage() {
  const params = useParams<{ jobId: string }>();
  const jobId = params.jobId;
  const [job, setJob] = useState<JobDetails | null>(null);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    location: "",
    current_job_title: "",
    skills: "",
    resume_summary: "",
    open_to_work: true,
  });

  useEffect(() => {
    api<JobDetails>(`/api/v1/jobs/${jobId}`)
      .then((data) => setJob(data))
      .catch((err: Error) => setError(err.message));
  }, [jobId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const body = await api<ApplicationResponse>(`/api/v1/jobs/${jobId}/apply`, {
        method: "POST",
        body: JSON.stringify({
          full_name: form.full_name,
          email: form.email,
          phone: form.phone || null,
          location: form.location || null,
          current_job_title: form.current_job_title || null,
          skills: form.skills
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          resume_summary: form.resume_summary || null,
          open_to_work: form.open_to_work,
        }),
      });
      setNotice(body.message);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Application failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="panel reveal">
      <header>Candidate Application</header>
      <form className="login-form" onSubmit={(event) => void submit(event)}>
        <h1>{job?.job_title || "Apply for this job"}</h1>
        {job?.location ? <p className="muted">Location: {job.location}</p> : null}
        <label>
          Full name
          <input
            value={form.full_name}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, full_name: event.target.value }))
            }
            required
          />
        </label>
        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, email: event.target.value }))
            }
            required
          />
        </label>
        <label>
          Phone
          <input
            value={form.phone}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, phone: event.target.value }))
            }
          />
        </label>
        <label>
          Current job title
          <input
            value={form.current_job_title}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                current_job_title: event.target.value,
              }))
            }
          />
        </label>
        <label>
          Current location
          <input
            value={form.location}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, location: event.target.value }))
            }
          />
        </label>
        <label>
          Skills (comma separated)
          <input
            value={form.skills}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, skills: event.target.value }))
            }
          />
        </label>
        <label>
          Short profile summary
          <textarea
            rows={4}
            value={form.resume_summary}
            onChange={(event) =>
              setForm((prev) => ({
                ...prev,
                resume_summary: event.target.value,
              }))
            }
          />
        </label>
        <label className="check-line">
          <input
            type="checkbox"
            checked={form.open_to_work}
            onChange={(event) =>
              setForm((prev) => ({ ...prev, open_to_work: event.target.checked }))
            }
          />
          I am open to work
        </label>
        {error ? <p className="error">{error}</p> : null}
        {notice ? <p className="notice">{notice}</p> : null}
        <button type="submit" disabled={busy || done}>
          {done ? "Applied" : busy ? "Submitting..." : "Submit application"}
        </button>
        <p className="muted">
          Recruiter can review your profile after application submission.
        </p>
        <p>
          <Link href="/login">Recruiter login</Link>
        </p>
      </form>
    </main>
  );
}
