"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import Link from "next/link";

interface PendingJob {
  id: number;
  title: string;
  status: string;
  employer_name: string | null;
  worker_name: string | null;
  budget: number;
  platform_commission: number;
  worker_payout: number;
  payment_method: string | null;
  payment_sent_at: string | null;
  created_at: string | null;
}

export default function AdminPage() {
  const { user } = useAuth();
  const [jobs, setJobs] = useState<PendingJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [toast, setToast] = useState("");

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(""), 4000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  const fetchPending = async () => {
    try {
      const res = await api.getAdminPending();
      setJobs(res.jobs);
    } catch {
      /* */
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPending();
  }, []);

  const handleVerify = async (jobId: number) => {
    setActionLoading(jobId);
    try {
      await api.adminVerifyPayment(jobId);
      setToast("Payment verified!");
      fetchPending();
    } catch {
      setToast("Verification failed");
    } finally {
      setActionLoading(null);
    }
  };

  const handleRelease = async (jobId: number) => {
    setActionLoading(jobId);
    try {
      await api.adminReleasePayout(jobId);
      setToast("Payout released!");
      fetchPending();
    } catch {
      setToast("Payout failed");
    } finally {
      setActionLoading(null);
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4">🔒</div>
          <h2 className="text-2xl font-semibold text-[var(--color-bp-black)]">
            Admin Access Required
          </h2>
          <p className="text-[var(--color-bp-gray-500)] mt-2">
            You do not have admin privileges.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-5xl mx-auto px-6 py-12">
        {/* Toast */}
        {toast && (
          <div className="fixed top-20 left-1/2 -translate-x-1/2 z-50">
            <div className="px-6 py-3 rounded-2xl bg-[var(--color-bp-black)] text-white text-sm font-medium shadow-lg">
              {toast}
            </div>
          </div>
        )}

        <div className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            🔐 Admin Panel
          </h1>
          <p className="text-[var(--color-bp-gray-500)] mt-1">
            Verify payments and release worker payouts.
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-yellow-600">
              {jobs.filter((j) => j.status === "verification_pending").length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">
              Awaiting Verification
            </div>
          </div>
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-green-600">
              {jobs.filter((j) => j.status === "verified").length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">
              Ready for Payout
            </div>
          </div>
          <div className="card text-center !py-5">
            <div className="text-3xl font-semibold text-[var(--color-bp-blue)]">
              {jobs.length}
            </div>
            <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">
              Total Pending
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12 text-[var(--color-bp-gray-500)]">
            Loading...
          </div>
        ) : jobs.length === 0 ? (
          <div className="card !p-12 text-center">
            <div className="text-5xl mb-4">✅</div>
            <h3 className="text-xl font-semibold text-[var(--color-bp-black)]">
              All Clear
            </h3>
            <p className="text-[var(--color-bp-gray-500)] mt-2">
              No payments are awaiting verification or payout.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div key={job.id} className="card !p-6">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <Link
                      href={`/jobs/${job.id}`}
                      className="text-lg font-semibold text-[var(--color-bp-black)] hover:text-[var(--color-bp-blue)] transition-colors"
                    >
                      {job.title}
                    </Link>
                    <div className="text-sm text-[var(--color-bp-gray-500)] mt-1">
                      Job #{job.id}
                    </div>
                  </div>
                  <span
                    className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-medium border ${
                      job.status === "verification_pending"
                        ? "bg-yellow-50 text-yellow-700 border-yellow-200"
                        : "bg-green-50 text-green-700 border-green-200"
                    }`}
                  >
                    {job.status === "verification_pending"
                      ? "Awaiting Verification"
                      : "Ready for Payout"}
                  </span>
                </div>

                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4 text-sm">
                  <div>
                    <div className="text-[var(--color-bp-gray-500)]">Employer</div>
                    <div className="font-medium">{job.employer_name || "—"}</div>
                  </div>
                  <div>
                    <div className="text-[var(--color-bp-gray-500)]">Worker</div>
                    <div className="font-medium">{job.worker_name || "—"}</div>
                  </div>
                  <div>
                    <div className="text-[var(--color-bp-gray-500)]">Budget</div>
                    <div className="font-semibold">₹{job.budget.toFixed(2)}</div>
                  </div>
                  <div>
                    <div className="text-[var(--color-bp-gray-500)]">Method</div>
                    <div className="font-medium uppercase">
                      {job.payment_method || "—"}
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--color-bp-gray-100)] mb-4 text-sm">
                  <div>
                    <span className="text-[var(--color-bp-gray-500)]">Commission: </span>
                    <span className="font-semibold text-purple-700">
                      ₹{job.platform_commission.toFixed(2)}
                    </span>
                  </div>
                  <div>
                    <span className="text-[var(--color-bp-gray-500)]">Worker Payout: </span>
                    <span className="font-semibold text-emerald-700">
                      ₹{job.worker_payout.toFixed(2)}
                    </span>
                  </div>
                  {job.payment_sent_at && (
                    <div className="text-xs text-[var(--color-bp-gray-500)]">
                      Sent: {new Date(job.payment_sent_at).toLocaleString("en-IN")}
                    </div>
                  )}
                </div>

                {job.status === "verification_pending" && (
                  <button
                    onClick={() => handleVerify(job.id)}
                    disabled={actionLoading === job.id}
                    className="btn-primary w-full !py-3 !bg-purple-600"
                  >
                    {actionLoading === job.id
                      ? "Verifying..."
                      : "✓ Confirm Payment Received"}
                  </button>
                )}

                {job.status === "verified" && (
                  <button
                    onClick={() => handleRelease(job.id)}
                    disabled={actionLoading === job.id}
                    className="btn-primary w-full !py-3 !bg-emerald-600"
                  >
                    {actionLoading === job.id
                      ? "Releasing..."
                      : `Release ₹${job.worker_payout.toFixed(2)} to Worker`}
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
