"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import api from "@/lib/api";
import { RefreshCw, CheckCircle2, AlertCircle } from "lucide-react";

export default function OAuthCallbackPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"processing" | "success" | "error">(
    "processing"
  );
  const [error, setError] = useState<string | null>(null);
  const [accountName, setAccountName] = useState<string>("");

  useEffect(() => {
    handleOAuthCallback();
  }, []);

  const handleOAuthCallback = async () => {
    try {
      // Get OAuth parameters from URL
      const code = searchParams.get("code");
      const state = searchParams.get("state"); // platform
      const errorParam = searchParams.get("error");

      if (errorParam) {
        throw new Error(
          `OAuth authorization failed: ${searchParams.get("error_description") || errorParam}`
        );
      }

      if (!code || !state) {
        throw new Error("Missing OAuth parameters");
      }

      // Exchange code for access token and bind account
      // In a real implementation, this would call the backend OAuth callback endpoint
      const response = await api.post("/ad-accounts/oauth/callback", {
        platform: state,
        code: code,
        redirect_uri: `${window.location.origin}/ad-accounts/callback`,
      });

      setAccountName(response.data.account_name || "Ad Account");
      setStatus("success");

      // Redirect to ad accounts page after 2 seconds
      setTimeout(() => {
        router.push("/ad-accounts");
      }, 2000);
    } catch (err: any) {
      console.error("OAuth callback error:", err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to connect ad account"
      );
      setStatus("error");
    }
  };

  if (status === "processing") {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
          <h2 className="text-2xl font-bold mb-2">Connecting Account...</h2>
          <p className="text-gray-600">
            Please wait while we connect your ad account.
          </p>
        </Card>
      </div>
    );
  }

  if (status === "success") {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Successfully Connected!</h2>
          <p className="text-gray-600 mb-2">
            Your ad account <strong>{accountName}</strong> has been connected.
          </p>
          <p className="text-sm text-gray-500">
            Redirecting to ad accounts page...
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-2xl">
      <Card className="p-12 text-center">
        <AlertCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
        <h2 className="text-2xl font-bold mb-2">Connection Failed</h2>
        <p className="text-gray-600 mb-6">{error}</p>
        <div className="flex gap-3 justify-center">
          <Button variant="outline" onClick={() => router.push("/ad-accounts")}>
            Back to Ad Accounts
          </Button>
          <Button onClick={() => router.push("/ad-accounts/bind")}>
            Try Again
          </Button>
        </div>
      </Card>
    </div>
  );
}
