"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { AlertTriangle, X, RefreshCw } from "lucide-react";
import api from "@/lib/api";
import { AdAccount } from "@/types";
import { useRouter } from "next/navigation";

interface TokenExpiryBannerProps {
  onDismiss?: () => void;
}

export function TokenExpiryBanner({ onDismiss }: TokenExpiryBannerProps) {
  const router = useRouter();
  const [expiringAccounts, setExpiringAccounts] = useState<AdAccount[]>([]);
  const [dismissed, setDismissed] = useState(false);
  const [refreshing, setRefreshing] = useState<number | null>(null);

  useEffect(() => {
    checkExpiringTokens();
  }, []);

  const checkExpiringTokens = async () => {
    try {
      const response = await api.get("/ad-accounts");
      const accounts: AdAccount[] = response.data.items || [];

      // Filter accounts with expired or soon-to-expire tokens
      const now = new Date();
      const twentyFourHoursFromNow = new Date(
        now.getTime() + 24 * 60 * 60 * 1000
      );

      const expiring = accounts.filter((account) => {
        if (account.status === "expired") return true;
        if (account.tokenExpiresAt) {
          const expiryDate = new Date(account.tokenExpiresAt);
          return expiryDate <= twentyFourHoursFromNow;
        }
        return false;
      });

      setExpiringAccounts(expiring);
    } catch (err) {
      console.error("Failed to check token expiry:", err);
    }
  };

  const handleReauthorize = (accountId: number, platform: string) => {
    // Redirect to OAuth flow for re-authorization
    router.push(`/ad-accounts/bind?reauth=${accountId}&platform=${platform}`);
  };

  const handleRefresh = async (accountId: number) => {
    try {
      setRefreshing(accountId);
      await api.post(`/ad-accounts/${accountId}/refresh`);
      // Remove from expiring list after successful refresh
      setExpiringAccounts(
        expiringAccounts.filter((acc) => acc.id !== accountId)
      );
    } catch (err: any) {
      alert(
        err.response?.data?.detail || "Failed to refresh token. Please re-authorize."
      );
    } finally {
      setRefreshing(null);
    }
  };

  const handleDismiss = () => {
    setDismissed(true);
    onDismiss?.();
  };

  if (dismissed || expiringAccounts.length === 0) {
    return null;
  }

  return (
    <Card className="border-orange-300 bg-orange-50 p-4 mb-6">
      <div className="flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" />
        <div className="flex-1">
          <h3 className="font-semibold text-orange-900 mb-2">
            Ad Account Authorization Required
          </h3>
          <p className="text-sm text-orange-800 mb-3">
            {expiringAccounts.length === 1
              ? "One of your ad accounts needs re-authorization:"
              : `${expiringAccounts.length} of your ad accounts need re-authorization:`}
          </p>
          <div className="space-y-2">
            {expiringAccounts.map((account) => (
              <div
                key={account.id}
                className="flex items-center justify-between bg-white rounded p-3 border border-orange-200"
              >
                <div className="flex items-center gap-3">
                  <span className="text-2xl">
                    {account.platform === "meta"
                      ? "🔵"
                      : account.platform === "tiktok"
                      ? "⚫"
                      : "🔴"}
                  </span>
                  <div>
                    <p className="font-medium text-gray-900">
                      {account.accountName}
                    </p>
                    <p className="text-xs text-gray-600">
                      {account.platform.toUpperCase()} •{" "}
                      {account.status === "expired"
                        ? "Token expired"
                        : "Token expiring soon"}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleRefresh(account.id)}
                    disabled={refreshing === account.id}
                  >
                    {refreshing === account.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <RefreshCw className="w-4 h-4 mr-1" />
                        Try Refresh
                      </>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    onClick={() =>
                      handleReauthorize(account.id, account.platform)
                    }
                  >
                    Re-authorize
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDismiss}
          className="flex-shrink-0"
        >
          <X className="w-4 h-4" />
        </Button>
      </div>
    </Card>
  );
}
