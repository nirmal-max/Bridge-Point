"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { WORK_DESCRIPTIONS } from "@/lib/types";

export default function HomePage() {
  const { user } = useAuth();

  return (
    <div className="pt-14">
      {/* ─── Hero Section ─── */}
      <section className="relative overflow-hidden bg-gradient-to-b from-[#f5f5f7] to-white">
        <div className="max-w-5xl mx-auto px-6 py-24 md:py-36 text-center">
          <h1
            className="text-5xl md:text-7xl font-semibold tracking-tight text-[var(--color-bp-black)] leading-[1.05] animate-fade-in-up"
            style={{ letterSpacing: "-0.03em" }}
          >
            Work that matters.
            <br />
            <span className="bg-gradient-to-r from-[#0071e3] to-[#af52de] bg-clip-text text-transparent">
              People who care.
            </span>
          </h1>
          <p className="mt-6 text-xl md:text-2xl text-[var(--color-bp-gray-500)] max-w-2xl mx-auto leading-relaxed animate-fade-in-up stagger-1">
            Bridge Point connects you with trusted micro-workers in your city.
            Post a task, find skilled help, and get things done — instantly.
          </p>
          <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center animate-fade-in-up stagger-2">
            {user ? (
              <>
                <Link href="/post-job" className="btn-primary text-lg px-8 py-4">
                  Post a Job
                </Link>
                <Link href="/jobs" className="btn-secondary text-lg px-8 py-4">
                  Find Work
                </Link>
                <Link href="/dashboard" className="btn-secondary text-lg px-8 py-4">
                  My Dashboard
                </Link>
              </>
            ) : (
              <>
                <Link href="/register" className="btn-primary text-lg px-8 py-4">
                  Get Started — It&apos;s Free
                </Link>
                <Link href="/jobs" className="btn-secondary text-lg px-8 py-4">
                  Browse Jobs
                </Link>
              </>
            )}
          </div>
        </div>
      </section>

      {/* ─── How It Works ─── */}
      <section className="py-24 bg-white">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-4xl md:text-5xl font-semibold text-center tracking-tight text-[var(--color-bp-black)]">
            How it works.
          </h2>
          <p className="text-center text-[var(--color-bp-gray-500)] text-lg mt-4 max-w-xl mx-auto">
            Three simple steps to get things done.
          </p>
          <div className="mt-16 grid md:grid-cols-3 gap-8">
            {[
              {
                step: "01",
                title: "Post a Task",
                desc: "Describe what you need — from gardening to tutoring. Set your budget and timeline.",
                icon: "📋",
              },
              {
                step: "02",
                title: "Get Matched",
                desc: "Skilled workers in your area apply instantly. Review profiles and pick the best fit.",
                icon: "🤝",
              },
              {
                step: "03",
                title: "Get It Done",
                desc: "Track progress in real-time. Pay securely. Leave a review for the community.",
                icon: "✅",
              },
            ].map((item, i) => (
              <div
                key={item.step}
                className="card text-center group"
              >
                <div className="text-5xl mb-6">{item.icon}</div>
                <div className="text-xs font-semibold text-[var(--color-bp-blue)] tracking-widest uppercase mb-3">
                  Step {item.step}
                </div>
                <h3 className="text-xl font-semibold text-[var(--color-bp-black)] mb-3">
                  {item.title}
                </h3>
                <p className="text-[var(--color-bp-gray-500)] leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Categories ─── */}
      <section className="py-24 bg-[var(--color-bp-gray-100)]">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-4xl md:text-5xl font-semibold text-center tracking-tight text-[var(--color-bp-black)]">
            Every skill. One platform.
          </h2>
          <p className="text-center text-[var(--color-bp-gray-500)] text-lg mt-4 max-w-xl mx-auto">
            From household chores to professional services.
          </p>
          <div className="mt-16 grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {WORK_DESCRIPTIONS.map((wd) => (
              <Link
                key={wd.value}
                href={`/jobs?work_description=${wd.value}`}
                className="bg-white rounded-2xl px-4 py-5 text-center hover:shadow-md transition-all hover:-translate-y-1 border border-transparent hover:border-[var(--color-bp-gray-200)]"
              >
                <div className="text-sm font-medium text-[var(--color-bp-black)]">
                  {wd.label}
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Trust Section ─── */}
      <section className="py-24 bg-white">
        <div className="max-w-5xl mx-auto px-6 text-center">
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            Built on trust.
          </h2>
          <div className="mt-16 grid md:grid-cols-3 gap-12">
            {[
              {
                title: "Verified Workers",
                desc: "Every worker's contact is verified. Phone and email verification ensures accountability.",
                icon: "🛡️",
              },
              {
                title: "Transparent Pricing",
                desc: "See exact costs upfront. Just 3% platform fee on each side. No hidden charges.",
                icon: "💎",
              },
              {
                title: "Real-time Tracking",
                desc: "Follow your job through 9 clear stages. Know exactly where things stand, always.",
                icon: "📡",
              },
            ].map((item) => (
              <div key={item.title}>
                <div className="text-4xl mb-4">{item.icon}</div>
                <h3 className="text-lg font-semibold text-[var(--color-bp-black)] mb-2">
                  {item.title}
                </h3>
                <p className="text-[var(--color-bp-gray-500)] leading-relaxed">
                  {item.desc}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ─── CTA ─── */}
      <section className="py-24 bg-gradient-to-b from-white to-[var(--color-bp-gray-100)]">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <h2 className="text-4xl md:text-5xl font-semibold tracking-tight text-[var(--color-bp-black)]">
            Ready to begin?
          </h2>
          <p className="text-[var(--color-bp-gray-500)] text-lg mt-4">
            Join Bridge Point today. Whether you need help or want to earn, we&apos;ve got you covered.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/register?role=employer" className="btn-primary text-lg px-8 py-4">
              I Need Help
            </Link>
            <Link href="/register?role=labor" className="btn-secondary text-lg px-8 py-4">
              I Want to Work
            </Link>
          </div>
        </div>
      </section>

      {/* ─── Footer ─── */}
      <footer className="py-8 border-t border-[var(--color-bp-gray-200)] bg-[var(--color-bp-gray-100)]">
        <div className="max-w-5xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-[var(--color-bp-gray-500)]">
          <div>
            © 2026 Bridge Point. Micro-Employment for India.
          </div>
          <div className="flex gap-6">
            <span>Chennai, Tamil Nadu</span>
            <span>·</span>
            <span>Built with ❤️</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
