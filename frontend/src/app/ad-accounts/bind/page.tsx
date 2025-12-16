"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useRouter } from "next/navigation";
import { CheckCircle2, AlertCircle } from "lucide-react";

type Platform = "meta" | "tiktok" | "google";

interface PlatformOption {
  id: Platform;
  name: string;
  icon: string;
  description: string;
  color: string;
}

const platforms: PlatformOption[] = [
  {
    id: "meta",
    name: "Meta",
    icon: "🔵",
    description: "Connect Facebook & Instagram Ads",
    color: "border-blue-500 hover:bg-blue-50",
  },
  {
    id: "tiktok",
    name: "TikTok",
    icon: "⚫",
    description: "Connect TikTok Ads Manager",
    color: "border-gray-800 hover:bg-gray-50",
  },
  {
    id: "google",
    name: "Google Ads",
    icon: "🔴",
    description: "Connect Google Ads Account",
    color: "border-red-500 hover:bg-red-50",
  },
];

export default function BindAdAccountPage() {
  const router = useRouter();
  const [selectedPlatform, setSelectedPlatform] = useState<Platform | null>(
    null
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handlePlatformSelect = (platform: Platform) => {
    setSelectedPlatform(platform);
    setError(null);
  };

  const handleOAuthRedirect = async () => {
    if (!selectedPlatform) return;

    setLoading(true);
    setError(null);

    try {
      // In a real implementation, this would redirect to the OAuth provider
      // For now, we'll simulate the OAuth flow
      const redirectUri = `${window.location.origin}/ad-accounts/callback`;
      
      // Different OAuth URLs for each platform
      const oauthUrls: Record<Platform, string> = {
        meta: `https://www.facebook.com/v18.0/dialog/oauth?client_id=${process.env.NEXT_PUBLIC_META_APP_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${selectedPlatform}&scope=ads_management,ads_read`,
        tiktok: `https://business-api.tiktok.com/portal/auth?app_id=${process.env.NEXT_PUBLIC_TIKTOK_APP_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${selectedPlatform}`,
        google: `https://accounts.google.com/o/oauth2/v2/auth?client_id=${process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID}&redirect_uri=${encodeURIComponent(redirectUri)}&state=${selectedPlatform}&scope=https://www.googleapis.com/auth/adwords&response_type=code&access_type=offline&prompt=consent`,
      };

      // Redirect to OAuth provider
      window.location.href = oauthUrls[selectedPlatform];
    } catch (err: any) {
      setError(err.message || "Failed to initiate OAuth flow");
      setLoading(false);
    }
  };

  const handleCancel = () => {
    router.push("/ad-accounts");
  };

  if (success) {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Account Connected!</h2>
          <p className="text-gray-600 mb-6">
            Your ad account has been successfully connected.
          </p>
          <Button onClick={() => router.push("/ad-accounts")}>
            View Ad Accounts
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold mb-2">Connect Ad Account</h1>
        <p className="text-gray-600">
          Select a platform to connect your advertising account
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6 flex items-start gap-2">
          <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Connection Failed</p>
            <p className="text-sm">{error}</p>
          </div>
        </div>
      )}

      {/* Platform Selection */}
      <div className="grid md:grid-cols-3 gap-4 mb-8">
        {platforms.map((platform) => (
          <Card
            key={platform.id}
            className={`p-6 cursor-pointer transition-all ${
              selectedPlatform === platform.id
                ? `border-2 ${platform.color} bg-opacity-10`
                : "border-2 border-transparent hover:border-gray-300"
            }`}
            onClick={() => handlePlatformSelect(platform.id)}
          >
            <div className="text-center">
              <div className="text-5xl mb-3">{platform.icon}</div>
              <h3 className="text-lg font-semibold mb-1">{platform.name}</h3>
              <p className="text-sm text-gray-600">{platform.description}</p>
            </div>
          </Card>
        ))}
      </div>

      {/* Instructions */}
      {selectedPlatform && (
        <Card className="p-6 mb-6 bg-blue-50 border-blue-200">
          <h3 className="font-semibold mb-3 flex items-center gap-2">
            <span className="text-2xl">
              {platforms.find((p) => p.id === selectedPlatform)?.icon}
            </span>
            What happens next?
          </h3>
          <ol className="list-decimal list-inside space-y-2 text-sm text-gray-700">
            <li>You'll be redirected to {selectedPlatform.toUpperCase()} to authorize access</li>
            <li>Log in to your {selectedPlatform.toUpperCase()} account if needed</li>
            <li>Grant AAE permission to manage your ads</li>
            <li>You'll be redirected back to complete the setup</li>
          </ol>
          <div className="mt-4 p-3 bg-white rounded border border-blue-300">
            <p className="text-xs text-gray-600">
              <strong>Note:</strong> AAE will only access your advertising data
              and will never post on your behalf or access personal information.
            </p>
          </div>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 justify-end">
        <Button variant="outline" onClick={handleCancel} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleOAuthRedirect}
          disabled={!selectedPlatform || loading}
        >
          {loading ? "Connecting..." : "Continue to Authorization"}
        </Button>
      </div>
    </div>
  );
}
