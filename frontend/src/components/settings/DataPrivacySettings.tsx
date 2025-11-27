"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";

export function DataPrivacySettings() {
  const router = useRouter();
  const [exportStatus, setExportStatus] = useState<{
    status: "idle" | "processing" | "ready" | "error";
    downloadUrl?: string;
    expiresAt?: string;
    message?: string;
  }>({ status: "idle" });
  const [deleteConfirmation, setDeleteConfirmation] = useState("");
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleExportData = async () => {
    try {
      setExportStatus({ status: "processing" });
      setMessage(null);

      const response = await api.post("/users/me/export");
      const { job_id } = response.data;

      // Poll for export status
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await api.get(`/users/me/export/${job_id}`);
          const { status, download_url, expires_at, error } = statusResponse.data;

          if (status === "completed") {
            clearInterval(pollInterval);
            setExportStatus({
              status: "ready",
              downloadUrl: download_url,
              expiresAt: expires_at,
            });
            setMessage({
              type: "success",
              text: "Data export ready! Download link will expire in 24 hours.",
            });
          } else if (status === "failed") {
            clearInterval(pollInterval);
            setExportStatus({
              status: "error",
              message: error || "Export failed",
            });
            setMessage({
              type: "error",
              text: error || "Failed to export data",
            });
          }
        } catch (error) {
          clearInterval(pollInterval);
          setExportStatus({ status: "error" });
          setMessage({ type: "error", text: "Failed to check export status" });
        }
      }, 3000); // Poll every 3 seconds

      // Stop polling after 5 minutes
      setTimeout(() => {
        clearInterval(pollInterval);
        if (exportStatus.status === "processing") {
          setExportStatus({
            status: "error",
            message: "Export is taking longer than expected. Please try again later.",
          });
        }
      }, 5 * 60 * 1000);
    } catch (error: any) {
      console.error("Failed to request data export:", error);
      setExportStatus({ status: "error" });
      setMessage({
        type: "error",
        text: error.response?.data?.detail || "Failed to request data export",
      });
    }
  };

  const handleDeleteAccount = async () => {
    if (deleteConfirmation !== "DELETE") {
      setMessage({
        type: "error",
        text: 'Please type "DELETE" to confirm account deletion',
      });
      return;
    }

    try {
      setIsDeleting(true);
      setMessage(null);

      await api.delete("/users/me", {
        data: { confirmation: "DELETE" },
      });

      // Clear local storage and redirect to home
      localStorage.clear();
      sessionStorage.clear();
      
      setMessage({
        type: "success",
        text: "Account deleted successfully. Redirecting...",
      });

      setTimeout(() => {
        router.push("/");
      }, 2000);
    } catch (error: any) {
      console.error("Failed to delete account:", error);
      setMessage({
        type: "error",
        text: error.response?.data?.detail || "Failed to delete account",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  const formatExpiryDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleString();
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Data & Privacy</h2>
        <p className="text-gray-600 mt-1">
          Manage your data and privacy settings
        </p>
      </div>

      {message && (
        <div
          className={`p-4 rounded-lg ${
            message.type === "success"
              ? "bg-green-50 text-green-800 border border-green-200"
              : "bg-red-50 text-red-800 border border-red-200"
          }`}
        >
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        {/* Data Export Section */}
        <div className="border border-gray-200 rounded-lg p-6">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900">Export Your Data</h3>
              <p className="text-gray-600 mt-2">
                Download a copy of all your data including:
              </p>
              <ul className="list-disc list-inside text-gray-600 mt-2 space-y-1">
                <li>Profile information</li>
                <li>Ad account connections</li>
                <li>Credit transaction history</li>
                <li>Creative files and metadata</li>
                <li>Landing pages</li>
                <li>Campaign configurations</li>
                <li>Report data</li>
              </ul>
              <p className="text-sm text-gray-500 mt-3">
                Your data will be exported as a ZIP file. The download link will expire after 24 hours.
              </p>
            </div>
          </div>

          <div className="mt-4">
            {exportStatus.status === "idle" && (
              <Button onClick={handleExportData} variant="outline">
                📥 Request Data Export
              </Button>
            )}

            {exportStatus.status === "processing" && (
              <div className="flex items-center gap-3 text-blue-600">
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-500"></div>
                <span>Preparing your data export... This may take a few minutes.</span>
              </div>
            )}

            {exportStatus.status === "ready" && exportStatus.downloadUrl && (
              <div className="space-y-3">
                <div className="flex items-center gap-3 text-green-600">
                  <span className="text-2xl">✅</span>
                  <span>Your data export is ready!</span>
                </div>
                <Button asChild>
                  <a href={exportStatus.downloadUrl} download>
                    📥 Download Data (ZIP)
                  </a>
                </Button>
                {exportStatus.expiresAt && (
                  <p className="text-sm text-gray-500">
                    Link expires: {formatExpiryDate(exportStatus.expiresAt)}
                  </p>
                )}
              </div>
            )}

            {exportStatus.status === "error" && (
              <div className="text-red-600">
                <p>❌ {exportStatus.message || "Failed to export data"}</p>
                <Button onClick={handleExportData} variant="outline" className="mt-2">
                  Try Again
                </Button>
              </div>
            )}
          </div>
        </div>

        {/* Account Deletion Section */}
        <div className="border border-red-200 rounded-lg p-6 bg-red-50">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-red-900">Delete Account</h3>
              <p className="text-red-700 mt-2">
                Permanently delete your account and all associated data.
              </p>
              <div className="mt-4 space-y-2">
                <p className="text-sm font-medium text-red-900">
                  ⚠️ This action cannot be undone. The following data will be permanently deleted:
                </p>
                <ul className="list-disc list-inside text-sm text-red-700 space-y-1">
                  <li>Your profile and account information</li>
                  <li>All ad account connections (ads on platforms will not be affected)</li>
                  <li>All creative files stored in our system</li>
                  <li>All landing pages and their files</li>
                  <li>All campaign configurations and history</li>
                  <li>All report data and analytics</li>
                  <li>All conversation history with AI Agent</li>
                  <li>All notification records</li>
                  <li>Remaining credit balance (no refunds)</li>
                </ul>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <Button
              onClick={() => setShowDeleteModal(true)}
              variant="outline"
              className="border-red-300 text-red-700 hover:bg-red-100"
            >
              🗑️ Delete My Account
            </Button>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              Confirm Account Deletion
            </h3>
            
            <div className="space-y-4">
              <p className="text-gray-700">
                This action is permanent and cannot be undone. All your data will be deleted within 30 days.
              </p>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Type <span className="font-bold text-red-600">DELETE</span> to confirm:
                </label>
                <Input
                  type="text"
                  value={deleteConfirmation}
                  onChange={(e) => setDeleteConfirmation(e.target.value)}
                  placeholder="Type DELETE"
                  className="font-mono"
                />
              </div>

              <div className="flex gap-3 justify-end pt-4">
                <Button
                  variant="outline"
                  onClick={() => {
                    setShowDeleteModal(false);
                    setDeleteConfirmation("");
                  }}
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleDeleteAccount}
                  disabled={deleteConfirmation !== "DELETE" || isDeleting}
                  className="bg-red-600 hover:bg-red-700 text-white"
                >
                  {isDeleting ? (
                    <>
                      <span className="animate-spin mr-2">⏳</span>
                      Deleting...
                    </>
                  ) : (
                    "Delete Account"
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
