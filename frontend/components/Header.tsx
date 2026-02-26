"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { useState } from "react";

export default function Header() {
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <header className="glass-header fixed top-0 left-0 right-0 z-50 border-b border-[var(--color-bp-gray-200)]">
      <nav className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link
          href="/"
          className="text-xl font-semibold tracking-tight text-[var(--color-bp-black)] hover:opacity-80 transition-opacity"
        >
          Bridge<span className="text-[var(--color-bp-blue)]">Point</span>
        </Link>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-8 text-sm font-medium text-[var(--color-bp-gray-700)]">
          <Link href="/jobs" className="hover:text-[var(--color-bp-black)] transition-colors">
            Find Work
          </Link>
          {user && (
            <Link href="/post-job" className="hover:text-[var(--color-bp-black)] transition-colors">
              Post Work
            </Link>
          )}
          {user ? (
            <>
              <Link href="/dashboard" className="hover:text-[var(--color-bp-black)] transition-colors">
                Dashboard
              </Link>
              {user.is_admin && (
                <Link href="/admin" className="hover:text-purple-700 transition-colors text-purple-600">
                  Admin
                </Link>
              )}

              <div className="flex items-center gap-3">
                <span className="text-[var(--color-bp-black)] font-medium">
                  {user.full_name.split(" ")[0]}
                </span>
                <button
                  onClick={logout}
                  className="text-[var(--color-bp-gray-500)] hover:text-[var(--color-bp-red)] transition-colors text-xs"
                >
                  Sign Out
                </button>
              </div>
            </>
          ) : (
            <div className="flex items-center gap-3">
              <Link
                href="/login"
                className="hover:text-[var(--color-bp-black)] transition-colors"
              >
                Sign In
              </Link>
              <Link href="/register" className="btn-primary !py-2 !px-5 !text-sm">
                Get Started
              </Link>
            </div>
          )}
        </div>

        {/* Mobile Menu Button */}
        <button
          className="md:hidden p-2 text-[var(--color-bp-gray-700)]"
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Toggle menu"
        >
          <svg width="20" height="20" viewBox="0 0 20 20" fill="currentColor">
            {menuOpen ? (
              <path d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" />
            ) : (
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" fill="none" />
            )}
          </svg>
        </button>
      </nav>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-[var(--color-bp-gray-200)] bg-white/95 backdrop-blur-xl animate-fade-in">
          <div className="px-6 py-4 flex flex-col gap-4 text-sm font-medium text-[var(--color-bp-gray-700)]">
            <Link href="/jobs" onClick={() => setMenuOpen(false)}>Find Work</Link>
            {user && (
              <Link href="/post-job" onClick={() => setMenuOpen(false)}>Post Work</Link>
            )}
            {user ? (
              <>
                <Link href="/dashboard" onClick={() => setMenuOpen(false)}>Dashboard</Link>
                {user.is_admin && (
                  <Link href="/admin" onClick={() => setMenuOpen(false)} className="text-purple-600">Admin Panel</Link>
                )}
                <button onClick={() => { logout(); setMenuOpen(false); }} className="text-left text-[var(--color-bp-red)]">
                  Sign Out
                </button>
              </>
            ) : (
              <>
                <Link href="/login" onClick={() => setMenuOpen(false)}>Sign In</Link>
                <Link href="/register" onClick={() => setMenuOpen(false)} className="btn-primary text-center !text-sm">Get Started</Link>
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
