"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Job, STATUS_LABELS, WORK_DESCRIPTIONS } from "@/lib/types";
import CallButton from "@/components/CallButton";

interface Transition {
  id: number;
  from_status: string;
  to_status: string;
  created_at: string;
}

export default function TaskConnectedPage() {
  const { job_id } = useParams();
  const { user } = useAuth();
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [transitions, setTransitions] = useState<Transition[]>([]);
  const [loading, setLoading] = useState(true);

  const jobId = Number(job_id);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [j, t] = await Promise.all([
          api.getJob(jobId),
          api.getJobTransitions(jobId),
        ]);
        setJob(j);
        setTransitions(t);

        // Security: only the assigned labor can view this page
        if (user && j.allotted_labor_id !== user.id) {
          router.replace(`/jobs/${jobId}`);
        }
      } catch {
        router.replace("/jobs");
      } finally {
        setLoading(false);
      }
    };
    if (jobId && user) fetchData();
  }, [jobId, user, router]);

  const wdLabel = (val: string) =>
    WORK_DESCRIPTIONS.find((w) => w.value === val)?.label || val;

  if (loading) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-[var(--color-bp-gray-500)]">Loading...</div>
      </div>
    );
  }

  if (!job) return null;

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-3xl mx-auto px-6 py-12">
        {/* Success Banner */}
        <div className="card !p-8 mb-6 text-center relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-br from-emerald-50 to-green-50 opacity-80" />
          <div className="relative z-10">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-emerald-100 flex items-center justify-center">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#059669" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" />
                <polyline points="22 4 12 14.01 9 11.01" />
              </svg>
            </div>
            <h1 className="text-2xl font-semibold text-emerald-800 mb-1">
              Task Accepted!
            </h1>
            <p className="text-emerald-600 text-sm">
              You've been connected with the employer. Get ready to start working.
            </p>
          </div>
        </div>

        {/* Employer Details */}
        <div className="card !p-6 mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-4">
            Employer
          </h3>
          <div className="flex items-center justify-between">
            <div>
              <div className="text-lg font-semibold text-[var(--color-bp-black)]">
                {job.employer_name || "Employer"}
              </div>
              <div className="text-sm text-[var(--color-bp-gray-500)] mt-0.5">
                Posted this task
              </div>
            </div>
            <CallButton
              userId={job.employer_id}
              userName={job.employer_name || "Employer"}
              jobId={job.id}
              variant="full"
            />
          </div>
        </div>

        {/* Job Summary */}
        <div className="card !p-6 mb-4">
          <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-4">
            Task Summary
          </h3>
          <div className="space-y-3">
            <div>
              <h2 className="text-xl font-semibold text-[var(--color-bp-black)]">
                {job.title}
              </h2>
              <p className="text-sm text-[var(--color-bp-gray-500)] mt-1">
                {job.role_description}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 pt-3 border-t border-[var(--color-bp-gray-200)]">
              <div>
                <div className="text-xs text-[var(--color-bp-gray-500)]">Work Type</div>
                <div className="font-medium text-sm">{wdLabel(job.work_description)}</div>
              </div>
              <div>
                <div className="text-xs text-[var(--color-bp-gray-500)]">Budget</div>
                <div className="font-semibold text-sm text-emerald-600">
                  ₹{job.labor_receives.toFixed(0)} (you receive)
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--color-bp-gray-500)]">Date</div>
                <div className="font-medium text-sm">
                  {new Date(job.date_of_task).toLocaleDateString("en-IN", {
                    day: "numeric",
                    month: "long",
                    year: "numeric",
                  })}
                </div>
              </div>
              <div>
                <div className="text-xs text-[var(--color-bp-gray-500)]">Location</div>
                <div className="font-medium text-sm">
                  {job.city} · {job.location_type === "online" ? "Online" : "Offline"}
                </div>
              </div>
              {job.address && (
                <div className="col-span-2">
                  <div className="text-xs text-[var(--color-bp-gray-500)]">Address</div>
                  <div className="font-medium text-sm">{job.address}</div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Status Timeline */}
        <div className="card !p-6 mb-6">
          <h3 className="text-sm font-semibold text-[var(--color-bp-gray-500)] uppercase tracking-wider mb-4">
            Status Timeline
          </h3>
          <div className="space-y-0">
            {transitions.map((t, i) => (
              <div key={t.id} className="flex items-start gap-3">
                <div className="flex flex-col items-center">
                  <div
                    className={`w-3 h-3 rounded-full mt-1 ${
                      i === transitions.length - 1
                        ? "bg-emerald-500"
                        : "bg-[var(--color-bp-gray-300)]"
                    }`}
                  />
                  {i < transitions.length - 1 && (
                    <div className="w-0.5 h-8 bg-[var(--color-bp-gray-200)]" />
                  )}
                </div>
                <div className="pb-4">
                  <div className="text-sm font-medium text-[var(--color-bp-black)]">
                    {STATUS_LABELS[t.to_status as keyof typeof STATUS_LABELS] || t.to_status}
                  </div>
                  <div className="text-xs text-[var(--color-bp-gray-500)]">
                    {new Date(t.created_at).toLocaleString("en-IN")}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3">
          <Link
            href={`/jobs/${job.id}`}
            className="btn-primary flex-1 text-center !py-3"
          >
            View Full Job Details
          </Link>
          <Link
            href="/dashboard"
            className="btn-secondary flex-1 text-center !py-3"
          >
            Go to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
