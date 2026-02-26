"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import { Job, STATUS_LABELS, STATUS_COLORS, WORK_DESCRIPTIONS, JOB_CATEGORIES } from "@/lib/types";
import { Suspense } from "react";

function JobsContent() {
  const searchParams = useSearchParams();
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    category: searchParams.get("category") || "",
    work_description: searchParams.get("work_description") || "",
    city: searchParams.get("city") || "",
  });

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const params: Record<string, string> = {};
      if (filters.category) params.category = filters.category;
      if (filters.work_description) params.work_description = filters.work_description;
      if (filters.city) params.city = filters.city;
      const res = await api.listJobs(params);
      setJobs(res.jobs);
    } catch {
      // Silently fail
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFilter = (e: React.FormEvent) => {
    e.preventDefault();
    fetchJobs();
  };

  const wdLabel = (val: string) =>
    WORK_DESCRIPTIONS.find((w) => w.value === val)?.label || val;

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <h1 className="text-4xl font-semibold tracking-tight text-[var(--color-bp-black)] mb-2">
          Find Work
        </h1>
        <p className="text-[var(--color-bp-gray-500)] mb-8">
          Browse available micro-jobs in your area.
        </p>

        {/* Filters */}
        <form onSubmit={handleFilter} className="flex flex-wrap gap-3 mb-8">
          <select
            className="select-field !w-auto min-w-[160px]"
            value={filters.category}
            onChange={(e) => setFilters((f) => ({ ...f, category: e.target.value }))}
          >
            <option value="">All Categories</option>
            {JOB_CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
          <select
            className="select-field !w-auto min-w-[180px]"
            value={filters.work_description}
            onChange={(e) => setFilters((f) => ({ ...f, work_description: e.target.value }))}
          >
            <option value="">All Work Types</option>
            {WORK_DESCRIPTIONS.map((w) => (
              <option key={w.value} value={w.value}>{w.label}</option>
            ))}
          </select>
          <input
            type="text"
            className="input-field !w-auto min-w-[140px]"
            placeholder="City"
            value={filters.city}
            onChange={(e) => setFilters((f) => ({ ...f, city: e.target.value }))}
          />
          <button type="submit" className="btn-primary !py-3 !px-6">
            Search
          </button>
        </form>

        {/* Job Grid */}
        {loading ? (
          <div className="text-center py-20 text-[var(--color-bp-gray-500)]">
            Loading jobs...
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-20">
            <div className="text-5xl mb-4">📭</div>
            <h3 className="text-xl font-semibold text-[var(--color-bp-black)] mb-2">
              No jobs found
            </h3>
            <p className="text-[var(--color-bp-gray-500)]">
              Try adjusting your filters or check back later.
            </p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {jobs.map((job) => (
              <Link key={job.id} href={`/jobs/${job.id}`}>
                <div className="card cursor-pointer">
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <h3 className="text-lg font-semibold text-[var(--color-bp-black)] leading-tight">
                      {job.title}
                    </h3>
                    <span
                      className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border whitespace-nowrap ${
                        job.status === "labour_allotted"
                          ? "bg-rose-50 text-rose-700 border-rose-200"
                          : STATUS_COLORS[job.status]
                      }`}
                    >
                      {job.status === "labour_allotted" ? "Taken" : STATUS_LABELS[job.status]}
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-2 mb-3">
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-[var(--color-bp-gray-100)] text-[var(--color-bp-gray-700)]">
                      {wdLabel(job.work_description)}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-[var(--color-bp-gray-100)] text-[var(--color-bp-gray-700)]">
                      📍 {job.city}
                    </span>
                    <span className="inline-flex items-center px-2.5 py-0.5 rounded-lg text-xs font-medium bg-[var(--color-bp-gray-100)] text-[var(--color-bp-gray-700)]">
                      {job.location_type === "online" ? "🌐 Online" : "📌 Offline"}
                    </span>
                  </div>
                  <p className="text-sm text-[var(--color-bp-gray-500)] line-clamp-2 mb-3">
                    {job.role_description}
                  </p>
                  <div className="flex items-center justify-between pt-3 border-t border-[var(--color-bp-gray-200)]">
                    <span className="text-lg font-semibold text-[var(--color-bp-black)]">
                      ₹{job.budget.toFixed(0)}
                    </span>
                    <span className="text-xs text-[var(--color-bp-gray-500)]">
                      {new Date(job.date_of_task).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default function JobsPage() {
  return (
    <Suspense fallback={<div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center"><div className="text-[var(--color-bp-gray-500)]">Loading...</div></div>}>
      <JobsContent />
    </Suspense>
  );
}
