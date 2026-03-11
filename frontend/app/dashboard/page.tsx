"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import {
  Job,
  Application,
  Favorite,
  STATUS_LABELS,
  STATUS_COLORS,
  WORK_DESCRIPTIONS,
} from "@/lib/types";

type TabType = "posted" | "active_tasks" | "applications" | "history" | "favorites";

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-[var(--color-bp-black)] mb-2">
            Sign in required
          </h2>
          <p className="text-[var(--color-bp-gray-500)] mb-4">
            Please sign in to access your dashboard.
          </p>
          <Link href="/login" className="btn-primary">
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return <UnifiedDashboard />;
}

function UnifiedDashboard() {
  const { user } = useAuth();
  const [tab, setTab] = useState<TabType>("posted");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [activeTasks, setActiveTasks] = useState<Job[]>([]);
  const [historyJobs, setHistoryJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [favorites, setFavorites] = useState<Favorite[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch data for each tab
  const fetchPostedJobs = async () => {
    setLoading(true);
    try {
      const res = await api.getMyJobs();
      setJobs(res.jobs);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  const fetchApplications = async () => {
    setLoading(true);
    try {
      const apps = await api.getMyApplications();
      setApplications(apps);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  const fetchHistory = async () => {
    setLoading(true);
    try {
      const res = await api.getLaborJobHistory();
      setHistoryJobs(res.jobs);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  const fetchFavorites = async () => {
    setLoading(true);
    try {
      const favs = await api.getFavorites();
      setFavorites(favs);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  const fetchActiveTasks = async () => {
    setLoading(true);
    try {
      const res = await api.getActiveTasksAsLabor();
      setActiveTasks(res.jobs);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial load — fetch posted jobs + summary counts
    const fetchInitial = async () => {
      try {
        const [jobsRes, appsRes, favsRes] = await Promise.all([
          api.getMyJobs(),
          api.getMyApplications().catch(() => []),
          api.getFavorites().catch(() => []),
        ]);
        setJobs(jobsRes.jobs);
        setApplications(appsRes);
        setFavorites(favsRes);
      } catch {
        /* */
      } finally {
        setLoading(false);
      }
    };
    fetchInitial();
  }, []);

  const handleTabChange = (t: TabType) => {
    setTab(t);
    if (t === "posted") fetchPostedJobs();
    else if (t === "active_tasks") fetchActiveTasks();
    else if (t === "applications") fetchApplications();
    else if (t === "history") fetchHistory();
    else if (t === "favorites") fetchFavorites();
  };

  const wdLabel = (val: string) =>
    WORK_DESCRIPTIONS.find((w) => w.value === val)?.label || val;

  const activeJobs = jobs.filter(
    (j) => !["payout_transferred", "payment_completed"].includes(j.status)
  );
  const completedJobs = jobs.filter((j) =>
    ["payout_transferred", "payment_completed"].includes(j.status)
  );

  const handleRemoveFavorite = async (favId: number) => {
    try {
      await api.removeFavorite(favId);
      setFavorites((f) => f.filter((fav) => fav.id !== favId));
    } catch {
      /* */
    }
  };

  const TAB_CONFIG: { key: TabType; label: string }[] = [
    { key: "posted", label: "My Posted Jobs" },
    { key: "active_tasks", label: "Active Tasks" },
    { key: "applications", label: "My Applications" },
    { key: "history", label: "Work History" },
    { key: "favorites", label: "Favorites" },
  ];

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-bp-black)]">
              Welcome, {user?.full_name.split(" ")[0]}
            </h1>
            <p className="text-[var(--color-bp-gray-500)] mt-1">
              Manage your jobs, applications, and history.
            </p>
          </div>
          <div className="flex gap-3">
            <Link href="/jobs" className="btn-secondary !py-2.5 !px-5">
              Find Work
            </Link>
            <Link href="/post-job" className="btn-primary !py-2.5 !px-5">
              + Post Work
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-4 gap-4 mb-8">
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-[var(--color-bp-black)]">
              {jobs.length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">Posted Jobs</div>
          </div>
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-[var(--color-bp-blue)]">
              {activeJobs.length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">Active</div>
          </div>
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-[var(--color-bp-green)]">
              {applications.filter((a) => a.status === "pending").length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">Pending Apps</div>
          </div>
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-emerald-600">
              {favorites.length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">Favorites</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex rounded-2xl bg-white p-1 mb-6 border border-[var(--color-bp-gray-200)]">
          {TAB_CONFIG.map((t) => (
            <button
              key={t.key}
              onClick={() => handleTabChange(t.key)}
              className={`flex-1 py-2.5 rounded-xl text-sm font-medium transition-all ${
                tab === t.key
                  ? "bg-[var(--color-bp-blue)] text-white shadow-sm"
                  : "text-[var(--color-bp-gray-500)]"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {loading ? (
          <div className="text-center py-12 text-[var(--color-bp-gray-500)]">Loading...</div>
        ) : (
          <>
            {/* ─── My Posted Jobs ─── */}
            {tab === "posted" && (
              <div className="space-y-3">
                {jobs.length === 0 ? (
                  <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
                    No posted jobs. <Link href="/post-job" className="text-[var(--color-bp-blue)]">Post one now</Link>
                  </div>
                ) : (
                  jobs.map((job) => (
                    <Link key={job.id} href={`/jobs/${job.id}`}>
                      <div className="card !p-5 flex items-center justify-between cursor-pointer mb-3">
                        <div>
                          <h3 className="font-semibold text-[var(--color-bp-black)]">{job.title}</h3>
                          <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                            {wdLabel(job.work_description)} · ₹{job.budget.toFixed(0)}
                          </div>
                        </div>
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${STATUS_COLORS[job.status]}`}>
                          {STATUS_LABELS[job.status]}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            )}

            {/* ─── Active Tasks (accepted via instant system) ─── */}
            {tab === "active_tasks" && (
              <div className="space-y-3">
                {activeTasks.length === 0 ? (
                  <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
                    No active tasks. <Link href="/jobs" className="text-[var(--color-bp-blue)]">Browse available work</Link>
                  </div>
                ) : (
                  activeTasks.map((job) => (
                    <Link key={job.id} href={`/jobs/${job.id}`}>
                      <div className="card !p-5 flex items-center justify-between cursor-pointer mb-3">
                        <div>
                          <h3 className="font-semibold text-[var(--color-bp-black)]">{job.title}</h3>
                          <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                            {wdLabel(job.work_description)} · ₹{job.labor_receives.toFixed(0)}
                          </div>
                        </div>
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${STATUS_COLORS[job.status]}`}>
                          {STATUS_LABELS[job.status]}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            )}

            {/* ─── My Applications ─── */}
            {tab === "applications" && (
              <div className="space-y-3">
                {applications.length === 0 ? (
                  <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
                    No applications yet. <Link href="/jobs" className="text-[var(--color-bp-blue)]">Find work</Link>
                  </div>
                ) : (
                  applications.map((app) => (
                    <Link key={app.id} href={`/jobs/${app.job_id}`}>
                      <div className="card !p-5 flex items-center justify-between cursor-pointer mb-3">
                        <div>
                          <div className="font-semibold text-[var(--color-bp-black)]">
                            Job #{app.job_id}
                          </div>
                          <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                            Applied {new Date(app.created_at).toLocaleDateString("en-IN")}
                          </div>
                        </div>
                        <span
                          className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${
                            app.status === "accepted"
                              ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                              : app.status === "rejected"
                              ? "bg-red-50 text-red-700 border-red-200"
                              : "bg-amber-50 text-amber-700 border-amber-200"
                          }`}
                        >
                          {app.status}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            )}

            {/* ─── Work History ─── */}
            {tab === "history" && (
              <div className="space-y-3">
                {historyJobs.length === 0 ? (
                  <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
                    No completed work yet.
                  </div>
                ) : (
                  historyJobs.map((job) => (
                    <Link key={job.id} href={`/jobs/${job.id}`}>
                      <div className="card !p-5 flex items-center justify-between cursor-pointer mb-3">
                        <div>
                          <div className="font-semibold text-[var(--color-bp-black)]">
                            {job.title}
                          </div>
                          <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                            {wdLabel(job.work_description)} · You received ₹{job.worker_payout.toFixed(0)}
                          </div>
                        </div>
                        <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${STATUS_COLORS[job.status]}`}>
                          {STATUS_LABELS[job.status]}
                        </span>
                      </div>
                    </Link>
                  ))
                )}
              </div>
            )}

            {/* ─── Favorites ─── */}
            {tab === "favorites" && (
              <div className="space-y-3">
                {favorites.length === 0 ? (
                  <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
                    No favorites saved yet.
                  </div>
                ) : (
                  favorites.map((fav) => (
                    <div key={fav.id} className="card !p-5 flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-[var(--color-bp-black)]">
                          {fav.labor_name || "Worker"}
                        </div>
                        {fav.labor_skills && (
                          <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                            {fav.labor_skills.join(", ")}
                          </div>
                        )}
                        {fav.labor_phone && (
                          <div className="text-sm text-[var(--color-bp-blue)] mt-0.5">
                            📞 {fav.labor_phone}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={() => handleRemoveFavorite(fav.id)}
                        className="text-xs text-[var(--color-bp-red)] hover:underline"
                      >
                        Remove
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
