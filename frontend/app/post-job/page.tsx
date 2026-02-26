"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { WORK_DESCRIPTIONS, JOB_CATEGORIES, TIME_SPANS } from "@/lib/types";

export default function PostJobPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [customWorkType, setCustomWorkType] = useState("");
  const [workTypeError, setWorkTypeError] = useState("");
  const [form, setForm] = useState({
    title: "",
    category: "household",
    work_description: "",
    role_description: "",
    required_skill: "",
    city: "Chennai",
    location_type: "offline",
    address: "",
    date_of_task: "",
    time_span: "single_day",
    organization_type: "individual",
    budget: "",
  });

  const update = (key: string, value: string) =>
    setForm((f) => ({ ...f, [key]: value }));

  if (!user) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-semibold text-[var(--color-bp-black)]">
            Sign In Required
          </h2>
          <p className="text-[var(--color-bp-gray-500)] mt-2">
            Please sign in to post a job.
          </p>
        </div>
      </div>
    );
  }

  const budget = parseFloat(form.budget) || 0;
  const employerTotal = budget + budget * 0.03;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setWorkTypeError("");

    // Resolve final work_description
    let resolvedWorkDesc = form.work_description;
    if (form.work_description === "other") {
      const trimmed = customWorkType.trim().replace(/<[^>]*>/g, "");
      if (!trimmed) {
        setWorkTypeError("Please specify the work type.");
        return;
      }
      if (trimmed.length > 100) {
        setWorkTypeError("Work type must be 100 characters or fewer.");
        return;
      }
      resolvedWorkDesc = trimmed;
    }

    setLoading(true);
    try {
      const job = await api.createJob({
        ...form,
        work_description: resolvedWorkDesc,
        budget: parseFloat(form.budget),
        date_of_task: new Date(form.date_of_task).toISOString(),
      });
      router.push(`/jobs/${job.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to post job");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-2xl mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            Post a Job
          </h1>
          <p className="text-[var(--color-bp-gray-500)] mt-3">
            Describe what you need and find the right worker.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="card !p-6 space-y-5">
            <h3 className="text-lg font-semibold text-[var(--color-bp-black)]">Job Details</h3>

            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Job Title *
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g., Gardening for 3 hours"
                value={form.title}
                onChange={(e) => update("title", e.target.value)}
                required
                minLength={3}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Category *
                </label>
                <select
                  className="select-field"
                  value={form.category}
                  onChange={(e) => update("category", e.target.value)}
                  required
                >
                  {JOB_CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Work Type *
                </label>
                <select
                  className="select-field"
                  value={form.work_description}
                  onChange={(e) => {
                    update("work_description", e.target.value);
                    if (e.target.value !== "other") {
                      setCustomWorkType("");
                      setWorkTypeError("");
                    }
                  }}
                  required
                >
                  <option value="">Select type</option>
                  {WORK_DESCRIPTIONS.map((w) => (
                    <option key={w.value} value={w.value}>{w.label}</option>
                  ))}
                </select>

                {/* Custom work type input — appears when "Other" is selected */}
                <div
                  style={{
                    maxHeight: form.work_description === "other" ? "80px" : "0",
                    opacity: form.work_description === "other" ? 1 : 0,
                    overflow: "hidden",
                    transition: "max-height 0.25s ease, opacity 0.2s ease, margin 0.25s ease",
                    marginTop: form.work_description === "other" ? "8px" : "0",
                  }}
                >
                  <input
                    type="text"
                    className="input-field"
                    placeholder="Describe the work type"
                    value={customWorkType}
                    onChange={(e) => {
                      setCustomWorkType(e.target.value);
                      if (workTypeError) setWorkTypeError("");
                    }}
                    maxLength={100}
                  />
                </div>
                {workTypeError && (
                  <p className="text-xs text-red-600 mt-1">{workTypeError}</p>
                )}
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Job Role Description *
              </label>
              <textarea
                className="input-field"
                rows={4}
                placeholder="Describe what the worker needs to do in detail..."
                value={form.role_description}
                onChange={(e) => update("role_description", e.target.value)}
                required
                minLength={10}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Required Skill (optional)
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g., Lawn mower experience"
                value={form.required_skill}
                onChange={(e) => update("required_skill", e.target.value)}
              />
            </div>
          </div>

          <div className="card !p-6 space-y-5">
            <h3 className="text-lg font-semibold text-[var(--color-bp-black)]">Location & Timing</h3>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  City *
                </label>
                <input
                  type="text"
                  className="input-field"
                  value={form.city}
                  onChange={(e) => update("city", e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Location Type *
                </label>
                <select
                  className="select-field"
                  value={form.location_type}
                  onChange={(e) => update("location_type", e.target.value)}
                  required
                >
                  <option value="offline">Offline (In-person)</option>
                  <option value="online">Online (Remote)</option>
                </select>
              </div>
            </div>

            {form.location_type === "offline" && (
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Address * (required for offline jobs)
                </label>
                <textarea
                  className="input-field"
                  rows={2}
                  placeholder="Full address for the job location"
                  value={form.address}
                  onChange={(e) => update("address", e.target.value)}
                  required
                />
              </div>
            )}

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Date of Task *
                </label>
                <input
                  type="date"
                  className="input-field"
                  value={form.date_of_task}
                  onChange={(e) => update("date_of_task", e.target.value)}
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Time Span *
                </label>
                <select
                  className="select-field"
                  value={form.time_span}
                  onChange={(e) => update("time_span", e.target.value)}
                  required
                >
                  {TIME_SPANS.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="card !p-6 space-y-5">
            <h3 className="text-lg font-semibold text-[var(--color-bp-black)]">Organization & Budget</h3>

            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Organization Type * (compulsory)
              </label>
              <select
                className="select-field"
                value={form.organization_type}
                onChange={(e) => update("organization_type", e.target.value)}
                required
              >
                <option value="individual">Individual</option>
                <option value="organization">Organization</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                Budget (₹) *
              </label>
              <input
                type="number"
                className="input-field"
                placeholder="e.g., 500"
                min="1"
                step="1"
                value={form.budget}
                onChange={(e) => update("budget", e.target.value)}
                required
              />
            </div>

            {budget > 0 && (
              <div className="mt-4 p-4 rounded-2xl bg-[var(--color-bp-gray-100)] border border-[var(--color-bp-gray-200)]">
                <div className="text-sm font-medium text-[var(--color-bp-gray-700)] mb-3">
                  Payment Breakdown
                </div>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-[var(--color-bp-gray-500)]">Job Budget</span>
                    <span className="font-medium">₹{budget.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-[var(--color-bp-gray-500)]">Platform Fee (3%)</span>
                    <span className="font-medium">₹{(budget * 0.03).toFixed(2)}</span>
                  </div>
                  <div className="border-t border-[var(--color-bp-gray-300)] pt-2 flex justify-between">
                    <span className="font-semibold text-[var(--color-bp-black)]">You Pay</span>
                    <span className="font-bold text-[var(--color-bp-black)]">₹{employerTotal.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-xs text-[var(--color-bp-gray-500)]">
                    <span>Worker Receives</span>
                    <span>₹{(budget - budget * 0.03).toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {error && (
            <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm border border-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full !py-4 !text-base"
          >
            {loading ? "Posting..." : "Post Job"}
          </button>
        </form>
      </div>
    </div>
  );
}
