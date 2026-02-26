/* ─── Bridge Point — API Client ─── */

let API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

// Ensure API_BASE is an absolute URL
if (API_BASE && !API_BASE.startsWith('http')) {
  API_BASE = `https://${API_BASE}`;
}
// Remove trailing slash to prevent double-slashes in requests
API_BASE = API_BASE.replace(/\/$/, '');

class ApiClient {
  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("bp_token");
  }

  private headers(withAuth = true): HeadersInit {
    const h: HeadersInit = { "Content-Type": "application/json" };
    if (withAuth) {
      const token = this.getToken();
      if (token) h["Authorization"] = `Bearer ${token}`;
    }
    return h;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...this.headers(), ...(options.headers || {}) },
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || `API Error: ${res.status}`);
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  }

  /* ─── Auth ─── */
  register(data: {
    email: string;
    phone: string;
    password: string;
    full_name: string;
    role: string;
    labor_category?: string;
    skills?: string[];
    city?: string;
    bio?: string;
  }) {
    return this.request<{
      access_token: string;
      token_type: string;
      user: import("./types").User;
    }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  login(email: string, password: string) {
    return this.request<{
      access_token: string;
      token_type: string;
      user: import("./types").User;
    }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  getMe() {
    return this.request<import("./types").User>("/api/auth/me");
  }

  activateRole(role: string) {
    return this.request<import("./types").User>(`/api/auth/activate-role?role=${role}`, {
      method: "POST",
    });
  }

  /* ─── Jobs ─── */
  createJob(data: Record<string, unknown>) {
    return this.request<import("./types").Job>("/api/jobs", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  listJobs(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<import("./types").JobListResponse>(`/api/jobs${qs}`);
  }

  getJob(id: number) {
    return this.request<import("./types").Job>(`/api/jobs/${id}`);
  }

  updateJobStatus(jobId: number, status: string) {
    return this.request<import("./types").Job>(`/api/jobs/${jobId}/status`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    });
  }

  getMyJobs(page = 1) {
    return this.request<import("./types").JobListResponse>(
      `/api/jobs/employer/my-jobs?page=${page}`
    );
  }

  getActiveTasksAsLabor(page = 1) {
    return this.request<import("./types").JobListResponse>(
      `/api/jobs/labor/active-tasks?page=${page}`
    );
  }

  getLaborJobHistory(page = 1) {
    return this.request<import("./types").JobListResponse>(
      `/api/jobs/labor/history?page=${page}`
    );
  }

  repostJob(jobId: number, dateOfTask: string) {
    return this.request<import("./types").Job>(
      `/api/jobs/${jobId}/repost?date_of_task=${encodeURIComponent(dateOfTask)}`,
      { method: "POST" }
    );
  }

  acceptTask(jobId: number) {
    return this.request<import("./types").Job>(
      `/api/jobs/${jobId}/accept-task`,
      { method: "POST" }
    );
  }

  getJobTransitions(jobId: number) {
    return this.request<
      { id: number; from_status: string; to_status: string; created_at: string }[]
    >(`/api/jobs/${jobId}/transitions`);
  }

  /* ─── Applications ─── */
  applyToJob(jobId: number, coverNote?: string) {
    return this.request<import("./types").Application>("/api/applications", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, cover_note: coverNote }),
    });
  }

  getJobApplications(jobId: number) {
    return this.request<import("./types").Application[]>(
      `/api/applications/job/${jobId}`
    );
  }

  acceptApplication(applicationId: number) {
    return this.request<import("./types").Application>(
      `/api/applications/${applicationId}/accept`,
      { method: "POST" }
    );
  }

  getMyApplications() {
    return this.request<import("./types").Application[]>(
      "/api/applications/labor/my-applications"
    );
  }

  getLaborHistory() {
    return this.request<import("./types").Application[]>(
      "/api/applications/labor/history"
    );
  }

  /* ─── Reviews ─── */
  createReview(data: {
    job_id: number;
    reviewee_id: number;
    rating: number;
    comment?: string;
  }) {
    return this.request<import("./types").Review>("/api/reviews", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getUserReviews(userId: number) {
    return this.request<import("./types").Review[]>(
      `/api/reviews/user/${userId}`
    );
  }

  /* ─── Favorites ─── */
  addFavorite(laborId: number) {
    return this.request<import("./types").Favorite>("/api/favorites", {
      method: "POST",
      body: JSON.stringify({ labor_id: laborId }),
    });
  }

  getFavorites() {
    return this.request<import("./types").Favorite[]>("/api/favorites");
  }

  removeFavorite(favoriteId: number) {
    return this.request<void>(`/api/favorites/${favoriteId}`, {
      method: "DELETE",
    });
  }

  /* ─── Payments — see Platform Custody section below ─── */

  /* ─── Calls ─── */
  getCallHistory(page = 1) {
    return this.request<import("./types").CallHistoryResponse>(
      `/api/calls/history?page=${page}`
    );
  }

  getCallDetail(callId: number) {
    return this.request<import("./types").CallLog>(
      `/api/calls/${callId}`
    );
  }

  /* ─── Messages (Chat) ─── */
  sendMessage(jobId: number, content: string) {
    return this.request<{
      id: number;
      job_id: number;
      sender_id: number;
      sender_name: string | null;
      content: string;
      created_at: string;
    }>("/api/messages", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, content }),
    });
  }

  getJobMessages(jobId: number, page = 1) {
    return this.request<
      {
        id: number;
        job_id: number;
        sender_id: number;
        sender_name: string | null;
        content: string;
        created_at: string;
      }[]
    >(`/api/messages/job/${jobId}?page=${page}`);
  }

  /* ─── Private Requests (Direct Rehire) ─── */
  sendPrivateRequest(data: { job_id: number; labor_id: number; message?: string }) {
    return this.request<import("./types").PrivateRequest>("/api/private-requests", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  getMyPrivateRequests() {
    return this.request<import("./types").PrivateRequest[]>(
      "/api/private-requests/my"
    );
  }

  respondPrivateRequest(
    requestId: number,
    action: "accept" | "deny",
    updatedDescription?: string
  ) {
    return this.request<import("./types").PrivateRequest>(
      `/api/private-requests/${requestId}/respond`,
      {
        method: "POST",
        body: JSON.stringify({ action, updated_description: updatedDescription }),
      }
    );
  }

  /* ─── Platform Custody Payments ─── */
  initiatePayment(jobId: number, paymentMethod: string) {
    return this.request<{
      message: string; status: string;
      platform_upi_id: string; platform_upi_name: string;
      amount: number; platform_commission: number; worker_payout: number;
    }>("/api/payments/initiate", {
      method: "POST",
      body: JSON.stringify({ job_id: jobId, payment_method: paymentMethod }),
    });
  }

  markPaymentSent(jobId: number) {
    return this.request<{ message: string; status: string; payment_sent_at: string }>(
      `/api/payments/${jobId}/mark-sent`,
      { method: "POST" }
    );
  }

  adminVerifyPayment(jobId: number) {
    return this.request<{ message: string; status: string }>(
      `/api/payments/${jobId}/verify`,
      { method: "POST" }
    );
  }

  adminReleasePayout(jobId: number) {
    return this.request<{
      message: string; status: string;
      worker_payout: number; platform_commission: number;
    }>(
      `/api/payments/${jobId}/release-payout`,
      { method: "POST" }
    );
  }

  getAdminPending() {
    return this.request<{
      jobs: {
        id: number; title: string; status: string;
        employer_name: string | null; worker_name: string | null;
        budget: number; platform_commission: number; worker_payout: number;
        payment_method: string | null; payment_sent_at: string | null;
        created_at: string | null;
      }[];
      total: number;
    }>("/api/payments/admin/pending");
  }

  getPlatformInfo() {
    return this.request<{ upi_id: string; upi_name: string }>(
      "/api/payments/platform-info"
    );
  }
}

export const api = new ApiClient();
