"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import AppHeader from "@/app/components/AppHeader";
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { JobSummary } from "@/lib/types";

export default function JobsPage() {
  const router = useRouter();
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({
    job_title: "",
    location: "",
    must_have_skills: "",
    raw_job_description: "",
  });

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    Promise.all([
      api<{ username: string }>("/api/v1/recruiter/me"),
      api<JobSummary[]>("/api/v1/recruiter/jobs"),
    ])
      .then(([me, list]) => {
        setUsername(me.username);
        setJobs(list);
      })
      .catch((err: Error) => setError(err.message));
  }, [router]);

  async function createJob(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreating(true);
    setNotice(null);
    setError(null);
    try {
      await api("/api/v1/jobs", {
        method: "POST",
        body: JSON.stringify({
          job_title: form.job_title.trim() || null,
          experience_min: null,
          experience_max: null,
          location: form.location.trim() || null,
          work_mode: null,
          employment_type: null,
          must_have_skills: form.must_have_skills
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          preferred_skills: [],
          education: [],
          responsibilities: [],
          keywords: [],
          raw_job_description: form.raw_job_description.trim(),
        }),
      });
      const list = await api<JobSummary[]>("/api/v1/recruiter/jobs");
      setJobs(list);
      setNotice("Job added successfully.");
      setForm({
        job_title: "",
        location: "",
        must_have_skills: "",
        raw_job_description: "",
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add job");
    } finally {
      setCreating(false);
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

  if (!jobs) {
    return (
      <div className="shell">
        <AppHeader />
        <section className="page-head reveal">
          <h1>Jobs</h1>
          <p className="muted">Loading your workspace...</p>
        </section>
        <section className="kpi-grid">
          <article className="kpi-card skeleton-block" />
          <article className="kpi-card skeleton-block" />
          <article className="kpi-card skeleton-block" />
        </section>
        <section className="card job-create skeleton-block" />
      </div>
    );
  }

  const totalPending = jobs.reduce((sum, job) => sum + job.pending_review_count, 0);
  const totalMatched = jobs.reduce((sum, job) => sum + job.matched_count, 0);

  return (
    <div className="shell">
      <AppHeader username={username} />
      <section className="home-hero reveal">
        <div>
          <p className="hero-kicker">Recruitment command center</p>
          <h1>Manage jobs, shortlist talent, and move faster.</h1>
          <p className="muted">
            Add a role, receive applications, run sourcing + ranking, and review every
            candidate in one place.
          </p>
        </div>
        <div className="hero-badge">
          <p className="kpi-label">Active workspace</p>
          <p className="kpi-value">{username || "Recruiter"}</p>
        </div>
      </section>
      <section className="kpi-grid reveal">
        <article className="kpi-card glow-card">
          <p className="kpi-label">Total jobs</p>
          <p className="kpi-value">{jobs.length}</p>
        </article>
        <article className="kpi-card glow-card">
          <p className="kpi-label">Matched candidates</p>
          <p className="kpi-value">{totalMatched}</p>
        </article>
        <article className="kpi-card glow-card">
          <p className="kpi-label">Pending review</p>
          <p className="kpi-value">{totalPending}</p>
        </article>
      </section>
      <section className="home-layout reveal">
        <section className="card job-create glow-card">
          <h2>Add job</h2>
          <p className="muted">Create a role in under a minute.</p>
          <form className="job-create-form" onSubmit={(event) => void createJob(event)}>
            <input
              placeholder="Job title (example: Backend Python Engineer)"
              value={form.job_title}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, job_title: event.target.value }))
              }
            />
            <input
              placeholder="Location (example: Bengaluru)"
              value={form.location}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, location: event.target.value }))
              }
            />
            <input
              placeholder="Must-have skills (comma separated)"
              value={form.must_have_skills}
              onChange={(event) =>
                setForm((prev) => ({ ...prev, must_have_skills: event.target.value }))
              }
            />
            <textarea
              placeholder="Paste job description"
              value={form.raw_job_description}
              onChange={(event) =>
                setForm((prev) => ({
                  ...prev,
                  raw_job_description: event.target.value,
                }))
              }
              required
              rows={4}
            />
            <button type="submit" className="approve cta-btn" disabled={creating}>
              {creating ? "Adding..." : "Add Job"}
            </button>
          </form>
        </section>
        <aside className="card quick-guide glow-card">
          <h2>Quick flow</h2>
          <ol>
            <li>Add a job with title + description.</li>
            <li>Share the apply link with candidates.</li>
            <li>Open job shortlist and review matches.</li>
          </ol>
          <p className="muted">Tip: Use candidate page to trigger outreach and interviews.</p>
        </aside>
      </section>
      {notice ? <p className="notice">{notice}</p> : null}
      {jobs.length === 0 ? (
        <article className="card empty-state reveal">
          <h2>No jobs yet</h2>
          <p>Start by adding your first job above. It will appear here instantly.</p>
        </article>
      ) : (
        <ul className="job-list reveal">
          {jobs.map((job) => (
            <li key={job.job_id}>
              <Link href={`/jobs/${job.job_id}`} className="job-card glow-card">
                <h2>{job.job_title || "Untitled role"}</h2>
                <div className="meta-pills">
                  {job.location ? <span>{job.location}</span> : null}
                  {job.work_mode ? <span>{job.work_mode}</span> : null}
                  {job.employment_type ? <span>{job.employment_type}</span> : null}
                </div>
                <p>
                  {job.matched_count} matched · {job.open_to_work_count} open to
                  work · {job.pending_review_count} pending review
                </p>
                <p className="muted">Apply link: /apply/{job.job_id}</p>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
