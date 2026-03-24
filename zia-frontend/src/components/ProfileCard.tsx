"use client";

import { CompanionProfile } from "@/lib/types";
import {
  Briefcase,
  MapPin,
  DollarSign,
  Target,
  Settings,
} from "lucide-react";

interface ProfileCardProps {
  profile: CompanionProfile | null;
  onEdit?: () => void;
}

export function ProfileCard({ profile, onEdit }: ProfileCardProps) {
  if (!profile) {
    return null;
  }

  const fields = [
    {
      icon: Briefcase,
      label: "Current Role",
      value: profile.current_role || "Not specified",
    },
    {
      icon: Briefcase,
      label: "Years of Experience",
      value: profile.yoe ? `${profile.yoe} years` : "Not specified",
    },
    {
      icon: MapPin,
      label: "Location",
      value: profile.location || "Not specified",
    },
    {
      icon: DollarSign,
      label: "Current CTC",
      value: profile.comp_current
        ? `₹${profile.comp_current.toLocaleString("en-IN")}`
        : "Not specified",
    },
    {
      icon: Target,
      label: "Target CTC",
      value: profile.comp_target
        ? `₹${profile.comp_target.toLocaleString("en-IN")}`
        : "Not specified",
    },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">{profile.name}</h2>
          <p className="text-sm text-gray-600 mt-1">
            {profile.company || "Job seeker"}
          </p>
        </div>
        {onEdit && (
          <button
            onClick={onEdit}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Edit profile"
          >
            <Settings className="w-5 h-5 text-gray-600" />
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {fields.map((field) => {
          const Icon = field.icon;
          return (
            <div key={field.label} className="flex items-start gap-3">
              <Icon className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-xs text-gray-500 font-medium">
                  {field.label}
                </p>
                <p className="text-sm text-gray-900">{field.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      {profile.tech_stack && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <p className="text-xs text-gray-500 font-medium mb-2">Tech Stack</p>
          <p className="text-sm text-gray-900 leading-relaxed">
            {profile.tech_stack}
          </p>
        </div>
      )}
    </div>
  );
}
