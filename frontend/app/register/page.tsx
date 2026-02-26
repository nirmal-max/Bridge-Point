"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { SKILL_CATEGORIES } from "@/lib/types";
import { Suspense } from "react";
import SkillPicker from "@/components/SkillPicker";

function RegisterForm() {
  const { register } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    phone: "",
    password: "",
    labor_category: "student",
    skills: [] as string[],
    city: "Chennai",
    bio: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [showCustomSkillInput, setShowCustomSkillInput] = useState(false);
  const [customSkillText, setCustomSkillText] = useState("");
  const [showSkills, setShowSkills] = useState(false);

  const update = (key: string, value: string | string[]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const toggleSkill = (skill: string) => {
    setForm((f) => ({
      ...f,
      skills: f.skills.includes(skill)
        ? f.skills.filter((s) => s !== skill)
        : [...f.skills, skill],
    }));
  };

  const predefinedValues = SKILL_CATEGORIES.flatMap((c) => c.skills.map((s: { value: string }) => s.value));

  const addCustomSkills = () => {
    const raw = customSkillText
      .replace(/<[^>]*>/g, "") // strip HTML
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s.length > 0 && s.length <= 50);

    const existing = form.skills.map((s) => s.toLowerCase());
    const unique = raw.filter((s) => !existing.includes(s.toLowerCase()));

    if (unique.length > 0) {
      setForm((f) => ({ ...f, skills: [...f.skills, ...unique] }));
    }
    setCustomSkillText("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({
        ...form,
        labor_category: form.labor_category || undefined,
        skills: form.skills.length > 0 ? form.skills : undefined,
        bio: form.bio || undefined,
      });
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)]">
      <div className="max-w-lg mx-auto px-6 py-16">
        <div className="text-center mb-10">
          <h1 className="text-4xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            Create your account
          </h1>
          <p className="text-[var(--color-bp-gray-500)] mt-3">
            Post jobs, find work — all from one account.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
              Full Name
            </label>
            <input
              type="text"
              className="input-field"
              placeholder="Enter your full name"
              value={form.full_name}
              onChange={(e) => update("full_name", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
              Email
            </label>
            <input
              type="email"
              className="input-field"
              placeholder="you@example.com"
              value={form.email}
              onChange={(e) => update("email", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
              Phone Number
            </label>
            <input
              type="tel"
              className="input-field"
              placeholder="+919876543210"
              value={form.phone}
              onChange={(e) => update("phone", e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
              Password
            </label>
            <input
              type="password"
              className="input-field"
              placeholder="Minimum 8 characters"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              required
              minLength={8}
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
              City
            </label>
            <input
              type="text"
              className="input-field"
              value={form.city}
              onChange={(e) => update("city", e.target.value)}
            />
          </div>

          {/* Profile enrichment — optional skills & category */}
          <div className="pt-2">
            <button
              type="button"
              onClick={() => setShowSkills(!showSkills)}
              className="text-sm font-medium text-[var(--color-bp-blue)] hover:underline flex items-center gap-1"
            >
              {showSkills ? "▾ Hide" : "▸ Add"} Skills & Profile Details
              <span className="text-[var(--color-bp-gray-400)] text-xs">(optional)</span>
            </button>
          </div>

          {showSkills && (
            <>
              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Category
                </label>
                <select
                  className="select-field"
                  value={form.labor_category}
                  onChange={(e) => update("labor_category", e.target.value)}
                >
                  <option value="student">Student</option>
                  <option value="freelancer">Freelancer</option>
                  <option value="labor">Labor</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-2">
                  Skills (select all that apply)
                </label>
                <SkillPicker
                  selected={form.skills}
                  onToggle={toggleSkill}
                  showCustomInput={showCustomSkillInput}
                  onToggleCustom={() => setShowCustomSkillInput((v) => !v)}
                  customText={customSkillText}
                  onCustomTextChange={setCustomSkillText}
                  onAddCustom={addCustomSkills}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[var(--color-bp-gray-700)] mb-1.5">
                  Bio (optional)
                </label>
                <textarea
                  className="input-field"
                  rows={3}
                  placeholder="Tell others about yourself..."
                  value={form.bio}
                  onChange={(e) => update("bio", e.target.value)}
                />
              </div>
            </>
          )}

          {error && (
            <div className="p-4 rounded-xl bg-red-50 text-red-700 text-sm border border-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full !py-4 !text-base mt-4"
          >
            {loading ? "Creating Account..." : "Create Account"}
          </button>
        </form>

        <p className="text-center text-sm text-[var(--color-bp-gray-500)] mt-6">
          Already have an account?{" "}
          <Link href="/login" className="text-[var(--color-bp-blue)] font-medium">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<div className="pt-14 min-h-screen bg-[var(--color-bp-gray-100)] flex items-center justify-center"><div className="text-[var(--color-bp-gray-500)]">Loading...</div></div>}>
      <RegisterForm />
    </Suspense>
  );
}
