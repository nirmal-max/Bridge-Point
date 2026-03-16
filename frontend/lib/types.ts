/* ─── Bridge Point — TypeScript Types ─── */

export interface User {
  id: number;
  email: string;
  phone: string;
  full_name: string;
  role: string;
  roles: string[];
  is_admin: boolean;
  labor_category?: "student" | "freelancer" | "labor" | null;
  skills?: string[] | null;
  city?: string | null;
  bio?: string | null;
  phone_verified: boolean;
  email_verified: boolean;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Job {
  id: number;
  employer_id: number;
  title: string;
  category: string;
  work_description: string;
  role_description: string;
  required_skill?: string | null;
  city: string;
  location_type: string;
  address?: string | null;
  date_of_task: string;
  time_span: string;
  organization_type: string;
  status: JobStatus;
  allotted_labor_id?: number | null;
  allotted_labor_name?: string | null;
  accepted_at?: string | null;
  payment_method?: string | null;
  created_at: string;
  budget: number;
  employer_commission: number;
  employer_total: number;
  labor_commission: number;
  labor_receives: number;
  platform_commission: number;
  worker_payout: number;
  payment_status?: string | null;
  payment_sent_at?: string | null;
  payout_released_at?: string | null;
  cashfree_order_id?: string | null;
  employer_name?: string | null;
}

export type JobStatus =
  | "posted"
  | "labour_allotted"
  | "work_started"
  | "work_in_progress"
  | "work_completed"
  | "payment_in_process"
  | "verification_pending"
  | "verified"
  | "payout_released"
  | "payment_completed"
  // Legacy Cashfree statuses (may exist in old DB rows)
  | "payment_pending"
  | "payment_paid"
  | "payout_transferred";

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

export interface Application {
  id: number;
  job_id: number;
  labor_id: number;
  status: "pending" | "accepted" | "rejected";
  cover_note?: string | null;
  created_at: string;
  labor_name?: string | null;
  labor_phone?: string | null;
  labor_skills?: string[] | null;
}

export interface Review {
  id: number;
  job_id: number;
  reviewer_id: number;
  reviewee_id: number;
  rating: number;
  comment?: string | null;
  created_at: string;
  reviewer_name?: string | null;
}

export interface Favorite {
  id: number;
  employer_id: number;
  labor_id: number;
  labor_name?: string | null;
  labor_skills?: string[] | null;
  labor_phone?: string | null;
  created_at: string;
}

export interface CommissionBreakdown {
  budget: number;
  employer_commission: number;
  employer_total: number;
  labor_commission: number;
  labor_receives: number;
  platform_earning: number;
  currency: string;
}

export interface PrivateRequest {
  id: number;
  job_id: number;
  employer_id: number;
  labor_id: number;
  status: "pending" | "accepted" | "denied";
  message?: string | null;
  created_at: string;
  responded_at?: string | null;
  employer_name?: string | null;
  labor_name?: string | null;
  job_title?: string | null;
}

export type CallStatus =
  | "ringing"
  | "active"
  | "completed"
  | "missed"
  | "rejected"
  | "failed";

export interface CallLog {
  id: number;
  caller_id: number;
  callee_id: number;
  caller_name?: string | null;
  callee_name?: string | null;
  job_id?: number | null;
  job_title?: string | null;
  status: CallStatus;
  started_at?: string | null;
  ended_at?: string | null;
  duration_seconds: number;
  created_at: string;
}

export interface CallHistoryResponse {
  calls: CallLog[];
  total: number;
  page: number;
  per_page: number;
}

export const WORK_DESCRIPTIONS = [
  { value: "emergency_replacement_staff", label: "Emergency Replacement Staff" },
  { value: "four_hour_shift_helper", label: "4-Hour Shift Helper" },
  { value: "one_day_event_assistant", label: "One-Day Event Assistant" },
  { value: "peak_hour_store_staff", label: "Peak-Hour Store Staff" },
  { value: "on_demand_local_worker", label: "On-Demand Local Worker" },
  { value: "daily_wage_construction_helper", label: "Daily Wage Construction Helper" },
  { value: "temporary_delivery_rider", label: "Temporary Delivery Rider" },
  { value: "warehouse_loading_assistant", label: "Warehouse Loading Assistant" },
  { value: "acting_driver_short_term", label: "Acting Driver (Short-Term)" },
  { value: "recurring_part_time_support", label: "Recurring Part-Time Support Staff" },
  { value: "other", label: "Other (Specify)" },
] as const;

/* ─── Categorized Skills ─── */
export interface SkillCategory {
  key: string;
  label: string;
  skills: readonly { value: string; label: string }[];
}

export const SKILL_CATEGORIES: SkillCategory[] = [
  {
    key: "general_work",
    label: "General & On-Demand Work",
    skills: [
      { value: "emergency_replacement_staff", label: "Emergency Replacement Staff" },
      { value: "four_hour_shift_helper", label: "4-Hour Shift Helper" },
      { value: "one_day_event_assistant", label: "One-Day Event Assistant" },
      { value: "on_demand_local_worker", label: "On-Demand Local Worker" },
      { value: "recurring_part_time_support", label: "Recurring Part-Time Support Staff" },
      { value: "daily_wage_worker", label: "Daily Wage Worker" },
      { value: "errand_runner", label: "Errand Runner" },
      { value: "personal_assistant", label: "Personal Assistant" },
      { value: "queue_standing_helper", label: "Queue Standing Helper" },
      { value: "document_runner", label: "Document Runner" },
    ],
  },
  {
    key: "cleaning_maintenance",
    label: "Home Cleaning & Maintenance",
    skills: [
      { value: "house_cleaning", label: "House Cleaning" },
      { value: "office_cleaning", label: "Office Cleaning" },
      { value: "gardening_maintenance", label: "Gardening & Landscaping" },
      { value: "painting_helper", label: "Painting Helper" },
      { value: "general_maintenance_worker", label: "General Maintenance Worker" },
      { value: "furniture_moving", label: "Furniture Moving" },
      { value: "hotel_housekeeping", label: "Hotel Housekeeping" },
      { value: "carpet_cleaning", label: "Carpet & Upholstery Cleaning" },
      { value: "window_cleaning", label: "Window Cleaning" },
      { value: "pest_control_assistant", label: "Pest Control Assistant" },
      { value: "deep_cleaning", label: "Deep Cleaning" },
      { value: "trash_disposal_helper", label: "Trash Disposal Helper" },
    ],
  },
  {
    key: "electrical_plumbing",
    label: "Electrical & Plumbing",
    skills: [
      { value: "electrician_helper", label: "Electrician Helper" },
      { value: "plumbing_assistant", label: "Plumbing Assistant" },
      { value: "ac_repair_assistant", label: "AC Repair Assistant" },
      { value: "wiring_helper", label: "Wiring Helper" },
      { value: "inverter_battery_technician", label: "Inverter & Battery Technician" },
      { value: "water_tank_cleaning", label: "Water Tank Cleaning" },
      { value: "appliance_repair_helper", label: "Appliance Repair Helper" },
      { value: "solar_panel_installer_helper", label: "Solar Panel Installer Helper" },
    ],
  },
  {
    key: "delivery_logistics",
    label: "Delivery & Logistics",
    skills: [
      { value: "temporary_delivery_rider", label: "Temporary Delivery Rider" },
      { value: "warehouse_loading_assistant", label: "Warehouse Loading Assistant" },
      { value: "warehouse_picker", label: "Warehouse Picker" },
      { value: "delivery_packing_staff", label: "Delivery Packing Staff" },
      { value: "acting_driver_short_term", label: "Acting Driver (Short-Term)" },
      { value: "courier_pickup_delivery", label: "Courier Pickup & Delivery" },
      { value: "truck_loading_unloading", label: "Truck Loading / Unloading" },
      { value: "bike_messenger", label: "Bike Messenger" },
      { value: "parcel_sorting_staff", label: "Parcel Sorting Staff" },
      { value: "last_mile_delivery", label: "Last-Mile Delivery" },
    ],
  },
  {
    key: "retail_shop",
    label: "Retail & Shop Support",
    skills: [
      { value: "peak_hour_store_staff", label: "Peak-Hour Store Staff" },
      { value: "retail_counter_staff", label: "Retail Counter Staff" },
      { value: "field_marketing_helper", label: "Field Marketing Helper" },
      { value: "inventory_stock_helper", label: "Inventory / Stock Helper" },
      { value: "billing_cashier_temp", label: "Billing / Cashier (Temp)" },
      { value: "shop_display_arranger", label: "Shop Display Arranger" },
      { value: "flyer_distribution", label: "Flyer Distribution" },
      { value: "product_demo_staff", label: "Product Demo Staff" },
      { value: "mall_promotion_helper", label: "Mall Promotion Helper" },
    ],
  },
  {
    key: "event_catering",
    label: "Event & Catering",
    skills: [
      { value: "event_setup_crew", label: "Event Setup Crew" },
      { value: "catering_assistant", label: "Catering Assistant" },
      { value: "kitchen_helper", label: "Kitchen Helper" },
      { value: "waiter_server_temp", label: "Waiter / Server (Temp)" },
      { value: "bartender_temp", label: "Bartender (Temp)" },
      { value: "decoration_setup", label: "Decoration Setup" },
      { value: "sound_lighting_helper", label: "Sound & Lighting Helper" },
      { value: "stage_setup_crew", label: "Stage Setup Crew" },
      { value: "crowd_management", label: "Crowd Management" },
      { value: "photographer_assistant", label: "Photographer Assistant" },
      { value: "wedding_event_helper", label: "Wedding / Event Helper" },
    ],
  },
  {
    key: "construction_labour",
    label: "Construction & Agriculture",
    skills: [
      { value: "daily_wage_construction_helper", label: "Daily Wage Construction Helper" },
      { value: "construction_site_assistant", label: "Construction Site Assistant" },
      { value: "security_guard_temporary", label: "Security Guard (Temporary)" },
      { value: "mason_helper", label: "Mason Helper" },
      { value: "carpentry_helper", label: "Carpentry Helper" },
      { value: "welding_assistant", label: "Welding Assistant" },
      { value: "farm_labour", label: "Farm Labour" },
      { value: "harvesting_helper", label: "Harvesting Helper" },
      { value: "nursery_plant_care", label: "Nursery & Plant Care" },
      { value: "animal_care_helper", label: "Animal Care Helper" },
      { value: "land_clearing_worker", label: "Land Clearing Worker" },
    ],
  },
  {
    key: "digital_data",
    label: "Digital & Data Tasks",
    skills: [
      { value: "data_entry_support", label: "Data Entry Support" },
      { value: "social_media_helper", label: "Social Media Helper" },
      { value: "online_listing_updater", label: "Online Listing Updater" },
      { value: "survey_form_filling", label: "Survey / Form Filling" },
      { value: "basic_graphic_design", label: "Basic Graphic Design" },
      { value: "content_writing_temp", label: "Content Writing (Temp)" },
      { value: "video_editing_helper", label: "Video Editing Helper" },
      { value: "telecalling_staff", label: "Telecalling Staff" },
      { value: "translation_assistant", label: "Translation Assistant" },
      { value: "typing_transcription", label: "Typing / Transcription" },
    ],
  },
];

/* Flat array for backward compat — auto-built from categories */
export const SKILL_OPTIONS = SKILL_CATEGORIES.flatMap((cat) => cat.skills);

export const JOB_CATEGORIES = [
  { value: "household", label: "Household" },
  { value: "industry", label: "Industry" },
  { value: "professional", label: "Professional" },
] as const;

export const TIME_SPANS = [
  { value: "few_hours", label: "Few Hours" },
  { value: "single_day", label: "Single Day" },
  { value: "week", label: "Week" },
] as const;

export const STATUS_LABELS: Record<string, string> = {
  posted: "Posted",
  labour_allotted: "Worker Assigned",
  work_started: "Work Started",
  work_in_progress: "Work in Progress",
  work_completed: "Work Completed",
  payment_in_process: "Payment in Process",
  verification_pending: "Verification Pending",
  verified: "Payment Verified",
  payout_released: "Payout Released",
  payment_completed: "Payment Completed",
  // Legacy Cashfree labels
  payment_pending: "Payment Pending",
  payment_paid: "Payment Received",
  payout_transferred: "Payout Transferred",
};

export const STATUS_COLORS: Record<string, string> = {
  posted: "bg-blue-50 text-blue-700 border-blue-200",
  labour_allotted: "bg-violet-50 text-violet-700 border-violet-200",
  work_started: "bg-orange-50 text-orange-700 border-orange-200",
  work_in_progress: "bg-sky-50 text-sky-700 border-sky-200",
  work_completed: "bg-teal-50 text-teal-700 border-teal-200",
  payment_in_process: "bg-yellow-50 text-yellow-700 border-yellow-200",
  verification_pending: "bg-amber-50 text-amber-700 border-amber-200",
  verified: "bg-indigo-50 text-indigo-700 border-indigo-200",
  payout_released: "bg-emerald-50 text-emerald-700 border-emerald-200",
  payment_completed: "bg-emerald-50 text-emerald-800 border-emerald-300",
  // Legacy Cashfree colors
  payment_pending: "bg-yellow-50 text-yellow-700 border-yellow-200",
  payment_paid: "bg-indigo-50 text-indigo-700 border-indigo-200",
  payout_transferred: "bg-emerald-50 text-emerald-700 border-emerald-200",
};
