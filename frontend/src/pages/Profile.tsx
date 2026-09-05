import { type FormEvent, useRef, useState } from "react";
import { Building2, Camera, CheckCircle2, Mail, MapPin, Pencil, Phone, User, X } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { getInitials, useUserProfile, type UserProfile } from "@/lib/userProfile";

// ── Field helpers ─────────────────────────────────────────────────────────────

interface FieldProps {
  label: string;
  value: string;
  editValue: string;
  name: keyof UserProfile;
  type?: string;
  editing: boolean;
  onChange: (name: keyof UserProfile, value: string) => void;
  icon?: React.ReactNode;
  multiline?: boolean;
  placeholder?: string;
}

function Field({ label, value, editValue, name, type = "text", editing, onChange, icon, multiline, placeholder }: FieldProps) {
  return (
    <div className="space-y-1" data-testid={`profile-field-${name}`}>
      <label className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">
        {icon}
        {label}
      </label>
      {editing ? (
        multiline ? (
          <textarea
            name={name}
            value={editValue}
            onChange={(e) => onChange(name, e.target.value)}
            rows={3}
            placeholder={placeholder}
            className="w-full resize-none rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition-colors focus:border-rose-400 focus:ring-1 focus:ring-rose-100"
            data-testid={`profile-input-${name}`}
          />
        ) : (
          <input
            type={type}
            name={name}
            value={editValue}
            onChange={(e) => onChange(name, e.target.value)}
            placeholder={placeholder}
            className="h-10 w-full rounded-md border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition-colors focus:border-rose-400 focus:ring-1 focus:ring-rose-100"
            data-testid={`profile-input-${name}`}
          />
        )
      ) : (
        <p
          className="text-sm text-slate-800"
          data-testid={`profile-value-${name}`}
        >
          {value || <span className="text-slate-400 italic">Not set</span>}
        </p>
      )}
    </div>
  );
}

// ── Avatar ────────────────────────────────────────────────────────────────────

function Avatar({ name, avatarUrl, editing, onUrlChange }: { name: string; avatarUrl: string; editing: boolean; onUrlChange: (url: string) => void }) {
  const initials = getInitials(name);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Reject non-image files
    if (!file.type.startsWith("image/")) {
      toast.error("Please select an image file (JPEG, PNG, WebP, etc.)");
      return;
    }

    // 5 MB guard — base64 in localStorage can get large
    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be under 5 MB");
      return;
    }

    const reader = new FileReader();
    reader.onload = (ev) => {
      const dataUrl = ev.target?.result as string;
      onUrlChange(dataUrl);
    };
    reader.readAsDataURL(file);

    // Reset so the same file can be re-selected if needed
    e.target.value = "";
  };

  return (
    <div className="flex flex-col items-center gap-3" data-testid="profile-avatar-section">
      <div className="relative" data-testid="profile-avatar-wrapper">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={name}
            className="h-24 w-24 rounded-full object-cover ring-4 ring-white shadow-md"
            data-testid="profile-avatar-image"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        ) : (
          <div
            className="flex h-24 w-24 items-center justify-center rounded-full bg-rose-100 text-2xl font-bold text-rose-700 ring-4 ring-white shadow-md"
            data-testid="profile-avatar-fallback"
          >
            {initials}
          </div>
        )}

        {editing && (
          <>
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="sr-only"
              aria-label="Upload profile photo"
              data-testid="profile-avatar-file-input"
              onChange={handleFileChange}
            />
            {/* Camera button triggers the file picker */}
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="absolute bottom-0 right-0 flex h-7 w-7 items-center justify-center rounded-full bg-rose-600 text-white shadow-sm transition-colors hover:bg-rose-700"
              aria-label="Upload profile photo"
              data-testid="profile-avatar-edit-button"
            >
              <Camera size={13} />
            </button>
          </>
        )}
      </div>

      {editing && (
        <p className="text-[11px] text-slate-400">
          Click the camera icon to upload a photo · Max 5 MB
        </p>
      )}
    </div>
  );
}

// ── Profile page ──────────────────────────────────────────────────────────────

export default function Profile() {
  const { profile, updateProfile } = useUserProfile();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<UserProfile>(profile);

  const startEditing = () => {
    setDraft({ ...profile });
    setEditing(true);
  };

  const cancelEditing = () => {
    setDraft({ ...profile });
    setEditing(false);
  };

  const handleChange = (name: keyof UserProfile, value: string) => {
    setDraft((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!draft.name.trim()) {
      toast.error("Name is required");
      return;
    }
    updateProfile(draft);
    setEditing(false);
    toast.success("Profile updated", { description: "Your changes have been saved." });
  };

  return (
    <div className="space-y-7" data-testid="profile-page">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 border-b border-slate-200 pb-7 lg:flex-row lg:items-end">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.18em] text-rose-600" data-testid="profile-eyebrow">
            Account
          </p>
          <h1 className="font-heading text-3xl font-bold tracking-[-0.04em] text-slate-950" data-testid="profile-title">
            Your Profile
          </h1>
          <p className="mt-2 max-w-xl text-sm text-slate-500" data-testid="profile-description">
            View and manage your personal and workspace information.
          </p>
        </div>
        {!editing && (
          <Button
            type="button"
            onClick={startEditing}
            className="self-start bg-rose-600 text-white hover:bg-rose-700"
            data-testid="profile-edit-button"
          >
            <Pencil size={14} />
            Edit profile
          </Button>
        )}
      </section>

      <form onSubmit={handleSubmit} data-testid="profile-form">
        <div className="grid gap-6 lg:grid-cols-[300px_1fr]">
          {/* Left — avatar + summary card */}
          <div className="space-y-5">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="profile-avatar-card">
              <Avatar
                name={editing ? draft.name : profile.name}
                avatarUrl={editing ? draft.avatarUrl : profile.avatarUrl}
                editing={editing}
                onUrlChange={(url) => handleChange("avatarUrl", url)}
              />
              <div className="mt-5 text-center">
                <p className="font-heading text-lg font-bold text-slate-900" data-testid="profile-display-name">
                  {profile.name}
                </p>
                <p className="mt-1 text-sm text-slate-500" data-testid="profile-display-role">
                  {profile.role}
                </p>
                <p className="mt-1 text-xs text-slate-400" data-testid="profile-display-company">
                  {profile.company}
                </p>
              </div>

              <div className="mt-5 space-y-2 border-t border-slate-100 pt-5">
                <div className="flex items-center gap-2 text-xs text-slate-500" data-testid="profile-summary-email">
                  <Mail size={13} className="shrink-0 text-slate-400" />
                  <span className="truncate">{profile.email || "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500" data-testid="profile-summary-phone">
                  <Phone size={13} className="shrink-0 text-slate-400" />
                  <span>{profile.phone || "—"}</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-slate-500" data-testid="profile-summary-location">
                  <MapPin size={13} className="shrink-0 text-slate-400" />
                  <span>{profile.location || "—"}</span>
                </div>
              </div>
            </div>

            {/* Workspace badge */}
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm" data-testid="profile-workspace-card">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em] text-slate-400">
                <Building2 size={13} />
                Workspace
              </div>
              <p className="mt-3 font-heading text-sm font-semibold text-slate-800" data-testid="profile-workspace-name">
                {profile.company}
              </p>
              <p className="mt-1 text-xs text-slate-500" data-testid="profile-workspace-dept">
                {profile.department}
              </p>
              <span className="mt-3 inline-flex items-center gap-1 rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-[10px] font-semibold text-emerald-700">
                <CheckCircle2 size={11} />
                Demo workspace
              </span>
            </div>
          </div>

          {/* Right — editable fields */}
          <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm" data-testid="profile-details-card">
            <div className="flex items-center justify-between border-b border-slate-100 pb-5 mb-6">
              <div>
                <h2 className="font-heading text-base font-bold text-slate-900">Personal information</h2>
                <p className="mt-0.5 text-xs text-slate-400">
                  {editing ? "Edit your details below, then save." : "Your contact and role details."}
                </p>
              </div>
              {editing && (
                <span className="rounded-full bg-amber-50 border border-amber-200 px-2.5 py-1 text-[10px] font-semibold text-amber-700">
                  Editing
                </span>
              )}
            </div>

            <div className="grid gap-6 sm:grid-cols-2">
              <Field
                label="Full name"
                value={profile.name}
                editValue={draft.name}
                name="name"
                editing={editing}
                onChange={handleChange}
                icon={<User size={11} />}
                placeholder="Your full name"
              />
              <Field
                label="Job title / Role"
                value={profile.role}
                editValue={draft.role}
                name="role"
                editing={editing}
                onChange={handleChange}
                icon={<User size={11} />}
                placeholder="e.g. Finance lead"
              />
              <Field
                label="Email address"
                value={profile.email}
                editValue={draft.email}
                name="email"
                type="email"
                editing={editing}
                onChange={handleChange}
                icon={<Mail size={11} />}
                placeholder="you@company.com"
              />
              <Field
                label="Phone number"
                value={profile.phone}
                editValue={draft.phone}
                name="phone"
                type="tel"
                editing={editing}
                onChange={handleChange}
                icon={<Phone size={11} />}
                placeholder="+91 …"
              />
              <Field
                label="Company"
                value={profile.company}
                editValue={draft.company}
                name="company"
                editing={editing}
                onChange={handleChange}
                icon={<Building2 size={11} />}
                placeholder="Your company name"
              />
              <Field
                label="Department"
                value={profile.department}
                editValue={draft.department}
                name="department"
                editing={editing}
                onChange={handleChange}
                icon={<Building2 size={11} />}
                placeholder="e.g. Finance & Accounts"
              />
              <Field
                label="Location"
                value={profile.location}
                editValue={draft.location}
                name="location"
                editing={editing}
                onChange={handleChange}
                icon={<MapPin size={11} />}
                placeholder="City, State"
              />
            </div>

            <div className="mt-6">
              <Field
                label="Bio"
                value={profile.bio}
                editValue={draft.bio}
                name="bio"
                editing={editing}
                onChange={handleChange}
                icon={<User size={11} />}
                multiline
                placeholder="A short description about yourself…"
              />
            </div>

            {editing && (
              <div className="mt-8 flex items-center justify-end gap-3 border-t border-slate-100 pt-5">
                <Button
                  type="button"
                  variant="outline"
                  onClick={cancelEditing}
                  data-testid="profile-cancel-button"
                >
                  <X size={14} />
                  Cancel
                </Button>
                <Button
                  type="submit"
                  className="bg-rose-600 text-white hover:bg-rose-700"
                  data-testid="profile-save-button"
                >
                  <CheckCircle2 size={14} />
                  Save changes
                </Button>
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
