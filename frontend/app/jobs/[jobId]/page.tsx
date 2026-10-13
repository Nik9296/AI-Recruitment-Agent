"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import AppHeader from "@/app/components/AppHeader";
import { api } from "@/lib/api";
import { getToken } from "@/lib/auth";
import type { Dashboard, PipelineRun } from "@/lib/types";

function statusLabel(row: {
  review_status: string;
}): string {
  if (row.review_status === "approved") return "Approved";
  if (row.review_status === "rejected") return "Rejected";
  if (row.review_status === "on_hold") return "On hold";
  return "Pending review";
}

export default function JobShortlistPage() {
  const params = useParams<{ jobId: string }>();
  const router = useRouter();
  const jobId = params.jobId;
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [username, setUsername] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [availability, setAvailability] = useState("all");
  const [reviewStatus, setReviewStatus] = useState("all");
  const [sort, setSort] = useState("match_score");
  const [sortDir, setSortDir] = useState("desc");

  const load = useCallback(async () => {
    const params = new URLSearchParams({
      query,
      availability,
      review_status: reviewStatus,
      sort,
      sort_dir: sortDir,
    });
    const detail = await api<Dashboard>(
      `/api/v1/recruiter/jobs/${jobId}?${params.toString()}`
    );
    setDashboard(detail);
  }, [availability, jobId, query, reviewStatus, sort, sortDir]);

  useEffect(() => {
    if (!getToken()) {
      router.replace("/login");
      return;
    }
    api<{ username: string }>("/api/v1/recruiter/me")
      .then((me) => setUsername(me.username))
      .catch(() => undefined);
  }, [router]);

  useEffect(() => {
    if (!getToken()) {
      return;
    }
    load().catch((err: Error) => setError(err.message));
  }, [load]);

  async function decide(candidateId: string, action: "approve" | "reject" | "hold") {
    const body = await api<{ message: string }>(
      `/api/v1/recruiter/jobs/${jobId}/candidates/${candidateId}/${action}`,
      { method: "POST" }
    );
    await load();
    return body.message;
  }

  const [notice, setNotice] = useState<string | null>(null);
  const [pipelineBusy, setPipelineBusy] = useState(false);

  async function runPipeline() {
    setPipelineBusy(true);
    try {
      const body = await api<PipelineRun>(
        `/api/v1/recruiter/jobs/${jobId}/pipeline/run`,
        { method: "POST" }
      );
      setNotice(
        `${body.message} Sourced ${body.sourced_count}, ranked ${body.ranked_count}. Email sent: ${body.outreach_sent ? "yes" : "no"}. Hired: ${body.hired ? "yes" : "no"}.`
      );
      await load();
    } catch (err) {
      setNotice(err instanceof Error ? err.message : "Pipeline failed");
    } finally {
      setPipelineBusy(false);
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

  if (!dashboard) {
    return (
      <div className="shell">
        <AppHeader username={username} />
        <section className="page-head reveal">
          <h1>Loading shortlist...</h1>
          <p className="muted">Preparing candidate insights.</p>
        </section>
        <section className="card skeleton-block" />
        <section className="card skeleton-block" />
      </div>
    );
  }

  return (
    <div className="shell">
      <AppHeader username={username} />
      <p className="back-link">
        <Link href="/">← Jobs</Link>
      </p>
      <section className="page-head reveal">
        <div>
          <h1>{dashboard.job_title || "Untitled role"}</h1>
          <div className="meta-pills">
            {dashboard.location ? <span>{dashboard.location}</span> : null}
            {dashboard.work_mode ? <span>{dashboard.work_mode}</span> : null}
            {dashboard.employment_type ? <span>{dashboard.employment_type}</span> : null}
          </div>
          <p>
            {dashboard.matched_count} candidates matched ·{" "}
            {dashboard.open_to_work_count} open to work ·{" "}
            {dashboard.pending_review_count} pending review
          </p>
        </div>
        <div className="actions actions-stack">
          <button
            type="button"
            className="approve cta-btn"
            onClick={() => void runPipeline()}
            disabled={pipelineBusy}
          >
            {pipelineBusy ? "Running pipeline…" : "Run sourcing + ranking"}
          </button>
          <p className="muted">
            Public apply form: <Link href={`/apply/${jobId}`}>Open</Link>
          </p>
        </div>
      </section>
      <section className="job-details reveal">
        <h2>Job details</h2>
        <p>
          Experience:{" "}
          {dashboard.experience_min != null && dashboard.experience_max != null
            ? `${dashboard.experience_min}–${dashboard.experience_max} years`
            : dashboard.experience_min != null
              ? `${dashboard.experience_min}+ years`
              : dashboard.experience_max != null
                ? `up to ${dashboard.experience_max} years`
                : "not stated"}
        </p>
        <p>Must-have: {dashboard.must_have_skills.join(", ") || "none listed"}</p>
        <p>Preferred: {dashboard.preferred_skills.join(", ") || "none listed"}</p>
      </section>
      <form
        className="filters reveal"
        onSubmit={(event) => {
          event.preventDefault();
          load().catch((err: Error) => setError(err.message));
        }}
      >
        <input
          placeholder="Search name, title, location, skills"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
        <select
          value={availability}
          onChange={(event) => setAvailability(event.target.value)}
          aria-label="Filter by availability"
        >
          <option value="all">All availability</option>
          <option value="open_to_work">Open to work</option>
          <option value="not_open_to_work">Not open to work</option>
          <option value="unknown">Unknown</option>
        </select>
        <select
          value={reviewStatus}
          onChange={(event) => setReviewStatus(event.target.value)}
          aria-label="Filter by recruiter status"
        >
          <option value="all">All recruiter statuses</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
          <option value="on_hold">On hold</option>
        </select>
        <select
          value={`${sort}:${sortDir}`}
          onChange={(event) => {
            const [nextSort, nextDir] = event.target.value.split(":");
            setSort(nextSort);
            setSortDir(nextDir);
          }}
          aria-label="Sort shortlist"
        >
          <option value="match_score:desc">Match score (high–low)</option>
          <option value="match_score:asc">Match score (low–high)</option>
          <option value="name:asc">Name (A–Z)</option>
          <option value="name:desc">Name (Z–A)</option>
        </select>
      </form>
      <table className="shortlist wide reveal">
        <thead>
          <tr>
            <th>Candidate</th>
            <th>Match</th>
            <th>Open to work</th>
            <th>Recruiter status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {dashboard.candidates.map((row) => (
            <tr key={row.candidate_id}>
              <td>
                <Link href={`/jobs/${jobId}/candidates/${row.candidate_id}`}>
                  {row.name || "Unnamed"}
                </Link>
                <div className="muted">{row.current_job_title || "Role not stated"}</div>
              </td>
              <td>{row.match_percent}%</td>
              <td>
                <span className="status-pill">{row.availability_status}</span>
              </td>
              <td>
                <span className="status-pill">{statusLabel(row)}</span>
              </td>
              <td className="row-actions">
                <Link href={`/jobs/${jobId}/candidates/${row.candidate_id}`}>View</Link>
                <button
                  type="button"
                  className="approve"
                  onClick={() =>
                    void decide(row.candidate_id, "approve").then(setNotice)
                  }
                >
                  Approve
                </button>
                <button
                  type="button"
                  className="hold"
                  onClick={() =>
                    void decide(row.candidate_id, "hold").then(setNotice)
                  }
                >
                  Hold
                </button>
                <button
                  type="button"
                  className="reject"
                  onClick={() =>
                    void decide(row.candidate_id, "reject").then(setNotice)
                  }
                >
                  Reject
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {dashboard.candidates.length === 0 ? (
        <p>No candidates match these filters.</p>
      ) : null}
      {notice ? <p className="notice">{notice}</p> : null}
    </div>
  );
}
