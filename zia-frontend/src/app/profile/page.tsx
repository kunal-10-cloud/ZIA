"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/context/ChatContext";
import { ProfileCard } from "@/components/ProfileCard";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { UpdateProfileRequest } from "@/lib/types";
import { ArrowLeft, Save } from "lucide-react";
import Link from "next/link";

export default function ProfilePage() {
  const router = useRouter();
  const { profile, updateProfile, isLoading, error, clearError } = useChat();
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [formData, setFormData] = useState<UpdateProfileRequest>({
    phone: "",
  });

  // Initialize form data
  useEffect(() => {
    if (profile) {
      setFormData({
        phone: profile.phone,
        name: profile.name,
        current_role: profile.current_role,
        yoe: profile.yoe,
        tech_stack: profile.tech_stack,
        company: profile.company,
        company_type: profile.company_type,
        location: profile.location,
        comp_current: profile.comp_current,
        comp_target: profile.comp_target,
        goals: profile.goals,
      });
    }

    if (!profile) {
      router.push("/");
    }
  }, [profile, router]);

  const handleChange = (field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value || null,
    }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    clearError();
    try {
      await updateProfile(formData);
      setIsEditing(false);
    } catch (err) {
      console.error("Failed to update profile:", err);
    } finally {
      setIsSaving(false);
    }
  };

  if (!profile) {
    return (
      <div className="flex items-center justify-center h-96">
        <LoadingSpinner text="Loading..." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <Link
          href="/chat"
          className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <h1 className="text-3xl font-bold">Your Profile</h1>
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {!isEditing ? (
        <div className="space-y-4">
          <ProfileCard profile={profile} onEdit={() => setIsEditing(true)} />
          <button
            onClick={() => setIsEditing(true)}
            className="w-full py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            Edit Profile
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm space-y-6">
          {/* Name */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Name
            </label>
            <input
              type="text"
              value={formData.name || ""}
              onChange={(e) => handleChange("name", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Current Role */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Current Job Title
            </label>
            <input
              type="text"
              value={formData.current_role || ""}
              onChange={(e) => handleChange("current_role", e.target.value)}
              placeholder="e.g., Senior Backend Engineer"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Years of Experience */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Years of Experience
            </label>
            <input
              type="number"
              step="0.5"
              value={formData.yoe || ""}
              onChange={(e) =>
                handleChange("yoe", e.target.value ? parseFloat(e.target.value) : null)
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Tech Stack */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Tech Stack
            </label>
            <textarea
              value={formData.tech_stack || ""}
              onChange={(e) => handleChange("tech_stack", e.target.value)}
              placeholder="e.g., Python, FastAPI, PostgreSQL, React"
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Company */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Current Company
            </label>
            <input
              type="text"
              value={formData.company || ""}
              onChange={(e) => handleChange("company", e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Company Type */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Company Type
            </label>
            <select
              value={formData.company_type || ""}
              onChange={(e) =>
                handleChange("company_type", e.target.value || null)
              }
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            >
              <option value="">Select...</option>
              <option value="startup">Startup</option>
              <option value="mid-market">Mid-Market</option>
              <option value="enterprise">Enterprise</option>
              <option value="multinational">Multinational</option>
            </select>
          </div>

          {/* Location */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Location
            </label>
            <input
              type="text"
              value={formData.location || ""}
              onChange={(e) => handleChange("location", e.target.value)}
              placeholder="e.g., Bangalore"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Current CTC */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Current CTC (₹)
            </label>
            <input
              type="number"
              value={formData.comp_current || ""}
              onChange={(e) =>
                handleChange(
                  "comp_current",
                  e.target.value ? parseInt(e.target.value) : null
                )
              }
              placeholder="e.g., 1800000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Target CTC */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Target CTC (₹)
            </label>
            <input
              type="number"
              value={formData.comp_target || ""}
              onChange={(e) =>
                handleChange(
                  "comp_target",
                  e.target.value ? parseInt(e.target.value) : null
                )
              }
              placeholder="e.g., 2400000"
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Goals */}
          <div>
            <label className="block text-sm font-medium text-gray-900 mb-2">
              Career Goals
            </label>
            <textarea
              value={formData.goals || ""}
              onChange={(e) => handleChange("goals", e.target.value)}
              placeholder="What do you want to achieve in your career?"
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-4">
            <button
              onClick={() => setIsEditing(false)}
              disabled={isSaving}
              className="flex-1 py-2 border border-gray-300 text-gray-900 font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex-1 py-2 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 flex items-center justify-center gap-2"
            >
              <Save className="w-4 h-4" />
              {isSaving ? "Saving..." : "Save Changes"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
