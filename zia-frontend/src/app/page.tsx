"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useChat } from "@/context/ChatContext";
import { LoadingSpinner } from "@/components/LoadingSpinner";
import { Phone, ArrowRight } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();
  const { profile, createOrGetProfile, isLoading, error, clearError } =
    useChat();
  const [phone, setPhone] = useState("");
  const [name, setName] = useState("");
  const [validationError, setValidationError] = useState("");

  // If already logged in, redirect to chat
  useEffect(() => {
    if (profile) {
      router.push("/chat");
    }
  }, [profile, router]);

  const validatePhone = (phoneNumber: string) => {
    // E.164 format validation
    const phoneRegex = /^\+?[1-9]\d{1,14}$/;
    return phoneRegex.test(phoneNumber.replace(/\s/g, ""));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setValidationError("");

    if (!phone.trim()) {
      setValidationError("Phone number is required");
      return;
    }

    if (!name.trim()) {
      setValidationError("Your name is required");
      return;
    }

    if (!validatePhone(phone)) {
      setValidationError(
        "Please enter a valid phone number (e.g., +919876543210)"
      );
      return;
    }

    try {
      await createOrGetProfile(
        phone.startsWith("+") ? phone : `+91${phone}`,
        name
      );
      router.push("/chat");
    } catch (err) {
      // Error is already set in context, but we might need to extract it here
      if (err instanceof Error) {
        setValidationError(err.message);
      } else {
        console.error("Failed to create profile:", err);
      }
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-slate-50 flex flex-col items-center justify-center px-4 py-8">
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="text-center space-y-4">
          <div className="w-20 h-20 bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 rounded-2xl mx-auto flex items-center justify-center shadow-lg">
            <span className="text-white font-bold text-5xl">Z</span>
          </div>
          <div className="space-y-2">
            <h1 className="text-5xl font-bold bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
              Zia
            </h1>
            <p className="text-lg text-slate-700 font-medium">Your AI Career Companion</p>
          </div>
          <p className="text-slate-600 text-base leading-relaxed max-w-sm mx-auto">
            Get personalized career guidance from an AI that deeply understands the Indian tech industry. Navigate salaries, opportunities, and growth with confidence.
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6 bg-white rounded-2xl p-8 border border-slate-200 shadow-lg">
          {/* Phone Input */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-900">
              Phone Number
            </label>
            <div className="relative">
              <Phone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+91 98765 43210"
                disabled={isLoading}
                className="w-full pl-12 pr-4 py-3.5 text-base text-slate-900 placeholder-slate-400 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-50 disabled:cursor-not-allowed transition-all"
              />
            </div>
            <p className="text-xs text-slate-500 mt-1.5">
              We'll use this to identify you and remember your career journey.
            </p>
          </div>

          {/* Name Input */}
          <div className="space-y-2">
            <label className="block text-sm font-semibold text-slate-900">
              Your Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="John Doe"
              disabled={isLoading}
              className="w-full px-4 py-3.5 text-base text-slate-900 placeholder-slate-400 bg-white border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:bg-slate-50 disabled:cursor-not-allowed transition-all"
            />
          </div>

          {/* Errors */}
          {(validationError || error) && (
            <div className="p-4 bg-red-50 border-l-4 border-red-600 text-red-800 text-sm rounded-lg">
              <p className="font-medium">{validationError || error}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 disabled:from-slate-400 disabled:to-slate-500 text-white font-semibold rounded-lg disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center gap-2 shadow-md hover:shadow-lg disabled:shadow-none"
          >
            {isLoading ? (
              <>
                <LoadingSpinner />
                Creating your profile...
              </>
            ) : (
              <>
                Start Chatting
                <ArrowRight className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        {/* Features */}
        <div className="space-y-4 text-center">
          <p className="text-xs font-semibold text-slate-600 uppercase tracking-wide">What you can do with Zia:</p>
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-gradient-to-br from-blue-50 to-indigo-50 border border-blue-200 rounded-lg hover:shadow-md transition-shadow">
              <p className="text-xs font-medium text-slate-900">Salary Guidance</p>
            </div>
            <div className="p-3 bg-gradient-to-br from-purple-50 to-pink-50 border border-purple-200 rounded-lg hover:shadow-md transition-shadow">
              <p className="text-xs font-medium text-slate-900">Career Growth</p>
            </div>
            <div className="p-3 bg-gradient-to-br from-green-50 to-emerald-50 border border-green-200 rounded-lg hover:shadow-md transition-shadow">
              <p className="text-xs font-medium text-slate-900">Job Matching</p>
            </div>
            <div className="p-3 bg-gradient-to-br from-orange-50 to-red-50 border border-orange-200 rounded-lg hover:shadow-md transition-shadow">
              <p className="text-xs font-medium text-slate-900">Offer Support</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
