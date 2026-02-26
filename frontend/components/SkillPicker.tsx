"use client";

import { useState } from "react";
import { SKILL_CATEGORIES } from "@/lib/types";

interface SkillPickerProps {
  selected: string[];
  onToggle: (skill: string) => void;
  showCustomInput: boolean;
  onToggleCustom: () => void;
  customText: string;
  onCustomTextChange: (text: string) => void;
  onAddCustom: () => void;
}

export default function SkillPicker({
  selected,
  onToggle,
  showCustomInput,
  onToggleCustom,
  customText,
  onCustomTextChange,
  onAddCustom,
}: SkillPickerProps) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  const toggle = (key: string) =>
    setExpanded((p) => ({ ...p, [key]: !p[key] }));

  /* Count selected skills per category */
  const countSelected = (catKey: string) => {
    const cat = SKILL_CATEGORIES.find((c) => c.key === catKey);
    if (!cat) return 0;
    return cat.skills.filter((s) => selected.includes(s.value)).length;
  };

  /* All predefined values for detecting custom chips */
  const predefinedValues = SKILL_CATEGORIES.flatMap((c) =>
    c.skills.map((s) => s.value)
  );

  return (
    <div className="space-y-2">
      {SKILL_CATEGORIES.map((cat) => {
        const isOpen = expanded[cat.key] ?? false;
        const selCount = countSelected(cat.key);

        return (
          <div
            key={cat.key}
            className="rounded-2xl border border-[var(--color-bp-gray-200)] bg-white overflow-hidden transition-all"
          >
            {/* Category header — always visible */}
            <button
              type="button"
              onClick={() => toggle(cat.key)}
              className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-[var(--color-bp-gray-50)] transition-colors"
            >
              <span className="text-sm font-semibold text-[var(--color-bp-gray-700)]">
                {cat.label}
              </span>
              <div className="flex items-center gap-2">
                {selCount > 0 && (
                  <span className="text-[10px] font-bold bg-[var(--color-bp-blue)] text-white px-2 py-0.5 rounded-full">
                    {selCount}
                  </span>
                )}
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 16 16"
                  fill="none"
                  className={`text-[var(--color-bp-gray-400)] transition-transform duration-200 ${
                    isOpen ? "rotate-180" : ""
                  }`}
                >
                  <path
                    d="M4 6l4 4 4-4"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            </button>

            {/* Skill chips — collapsible */}
            <div
              style={{
                maxHeight: isOpen ? `${cat.skills.length * 48 + 24}px` : "0",
                opacity: isOpen ? 1 : 0,
                overflow: "hidden",
                transition:
                  "max-height 0.3s ease, opacity 0.2s ease, padding 0.3s ease",
                padding: isOpen ? "0 12px 12px 12px" : "0 12px",
              }}
            >
              <div className="grid grid-cols-2 gap-2">
                {cat.skills.map((sk) => (
                  <button
                    key={sk.value}
                    type="button"
                    onClick={() => onToggle(sk.value)}
                    className={`px-3 py-2.5 rounded-2xl text-[13px] font-medium transition-all border text-left ${
                      selected.includes(sk.value)
                        ? "bg-[var(--color-bp-blue)] text-white border-[var(--color-bp-blue)]"
                        : "bg-[var(--color-bp-gray-50)] text-[var(--color-bp-gray-700)] border-[var(--color-bp-gray-200)] hover:border-[var(--color-bp-blue)] hover:bg-white"
                    }`}
                  >
                    {sk.label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        );
      })}

      {/* Other (Specify) */}
      <div className="rounded-2xl border border-[var(--color-bp-gray-200)] bg-white overflow-hidden">
        <button
          type="button"
          onClick={onToggleCustom}
          className={`w-full flex items-center justify-between px-4 py-3 text-left transition-colors ${
            showCustomInput
              ? "bg-[var(--color-bp-blue)] text-white"
              : "hover:bg-[var(--color-bp-gray-50)]"
          }`}
        >
          <span
            className={`text-sm font-semibold ${
              showCustomInput
                ? "text-white"
                : "text-[var(--color-bp-gray-700)]"
            }`}
          >
            Other (Specify)
          </span>
          <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            className={showCustomInput ? "text-white" : "text-[var(--color-bp-gray-400)]"}
          >
            <path
              d="M8 4v8M4 8h8"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
            />
          </svg>
        </button>

        <div
          style={{
            maxHeight: showCustomInput ? "80px" : "0",
            opacity: showCustomInput ? 1 : 0,
            overflow: "hidden",
            transition:
              "max-height 0.25s ease, opacity 0.2s ease, padding 0.25s ease",
            padding: showCustomInput ? "0 12px 12px 12px" : "0 12px",
          }}
        >
          <input
            type="text"
            className="input-field"
            placeholder="Type skills separated by commas, then press Enter"
            value={customText}
            onChange={(e) => onCustomTextChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                onAddCustom();
              }
            }}
            maxLength={200}
          />
        </div>
      </div>

      {/* Custom skill chips */}
      {selected.filter((s) => !predefinedValues.includes(s)).length > 0 && (
        <div className="flex flex-wrap gap-2 pt-1">
          {selected
            .filter((s) => !predefinedValues.includes(s))
            .map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-2xl text-sm font-medium bg-[var(--color-bp-blue)] text-white border border-[var(--color-bp-blue)] transition-all"
              >
                {skill}
                <button
                  type="button"
                  onClick={() => onToggle(skill)}
                  className="ml-0.5 text-white/70 hover:text-white text-base leading-none"
                >
                  ×
                </button>
              </span>
            ))}
        </div>
      )}

      {/* Selected summary */}
      {selected.length > 0 && (
        <div className="text-xs text-[var(--color-bp-gray-500)] pt-1">
          {selected.length} skill{selected.length !== 1 ? "s" : ""} selected
        </div>
      )}
    </div>
  );
}
