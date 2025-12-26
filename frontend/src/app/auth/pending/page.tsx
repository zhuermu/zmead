"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

export default function PendingApprovalPage() {
  const searchParams = useSearchParams();
  const [userEmail, setUserEmail] = useState<string>("");

  useEffect(() => {
    const email = searchParams?.get("email");
    if (email) {
      setUserEmail(email);
    }
  }, [searchParams]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="w-20 h-20 bg-yellow-100 rounded-full flex items-center justify-center">
            <svg
              className="w-10 h-10 text-yellow-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-gray-900 text-center mb-4">
          Account Pending Approval
        </h1>

        {/* Message */}
        <div className="text-gray-600 text-center space-y-4 mb-6">
          <p>
            Hello{userEmail && (
              <span className="font-semibold text-gray-800"> {userEmail}</span>
            )}
            !
          </p>
          <p>
            The platform is currently in beta testing. Your account is awaiting administrator approval.
          </p>
          <p className="text-sm">
            Once approved, you will receive a notification email and can access all platform features.
          </p>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-semibold text-blue-900 mb-2">
            How long does approval take?
          </h3>
          <p className="text-sm text-blue-800">
            We typically complete the review within 1-2 business days. For urgent needs, please contact the administrator.
          </p>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <button
            onClick={() => (window.location.href = "/")}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors"
          >
            Back to Home
          </button>

          <button
            onClick={() => {
              localStorage.removeItem("access_token");
              localStorage.removeItem("refresh_token");
              window.location.href = "/login";
            }}
            className="w-full py-3 px-4 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium rounded-lg transition-colors"
          >
            Sign In Again
          </button>
        </div>

        {/* Contact Info */}
        <div className="mt-6 pt-6 border-t border-gray-200 text-center">
          <p className="text-sm text-gray-500">
            Questions?{" "}
            <a
              href="mailto:support@example.com"
              className="text-blue-600 hover:text-blue-700 font-medium"
            >
              Contact Support
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
