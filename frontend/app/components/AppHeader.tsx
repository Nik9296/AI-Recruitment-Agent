"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { clearToken } from "@/lib/auth";

type AppHeaderProps = {
  username?: string;
};

export default function AppHeader({ username }: AppHeaderProps) {
  const router = useRouter();

  function logout() {
    clearToken();
    router.push("/login");
  }

  return (
    <header className="topbar">
      <Link href="/" className="brand">
        <span className="brand-mark" aria-hidden="true">
          AR
        </span>
        <span>
          AI Recruitment
          <small className="brand-subtitle">Smart hiring cockpit</small>
        </span>
      </Link>
      <div className="topbar-meta">
        <span className="role-tag">Recruiter workspace</span>
        {username ? <span className="user-chip">{username}</span> : null}
        <button type="button" className="text-btn" onClick={logout}>
          Log out
        </button>
      </div>
    </header>
  );
}
