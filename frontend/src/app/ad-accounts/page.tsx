"use client";

import { useEffect, useState } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { AdAccount } from "@/types";
import { Plus, RefreshCw, Trash2, CheckCircle2 } from "lucide-react";
import { useRouter } from "next/navigation";

// Platform icons mapping
const platformIcons: Record<string, string> = {
  meta: "🔵",
  tiktok: "⚫",
  google: "🔴",
};

const platformNames: Record<string, string> = {
  meta: "Meta (Facebook/Instagram)",
  tiktok: "TikTok",
  google: "Google Ads",
};

export default function AdAccountsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<AdAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [activatingId, setActivatingId] = useState<number | null>(null);

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await api.get("/ad-accounts");
      setAccounts(response.data.accounts || []);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load ad accounts");
    } finally {
      setLoading(false);
    }
  };

  const handleUnbind = async (accountId: number) => {
    if (!confirm("Are you sure you want to unbind this ad account?")) {
      return;
    }

    try {
      setDeletingId(accountId);
      await api.delete(`/ad-accounts/${accountId}`);
      setAccounts(accounts.filter((acc) => acc.id !== accountId));
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to unbind ad account");
    } finally {
      setDeletingId(null);
    }
  };

  const handleActivate = async (accountId: number) => {
    try {
      setActivatingId(accountId);
      const response = await api.post(`/ad-accounts/${accountId}/activate`);
      // Update the accounts list to reflect the new active account
      setAccounts(
        accounts.map((acc) => ({
          ...acc,
          isActive: acc.id === accountId,
        }))
      );
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to activate ad account");
    } finally {
      setActivatingId(null);
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive"> = {
      active: "default",
      expired: "destructive",
      revoked: "secondary",
    };
    return (
      <Badge variant={variants[status] || "secondary"}>
        {status.toUpperCase()}
      </Badge>
    );
  };

  const formatDate = (dateString?: string) => {
    if (!dateString) return "Never";
    return new Date(dateString).toLocaleString();
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-3xl font-bold">Ad Accounts</h1>
          <p className="text-gray-600 mt-1">
            Manage your connected advertising accounts
          </p>
        </div>
        <Button onClick={() => router.push("/ad-accounts/bind")}>
          <Plus className="w-4 h-4 mr-2" />
          Bind New Account
        </Button>
      </div>

      {/* Error Message */}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
          {error}
        </div>
      )}

      {/* Accounts List */}
      {accounts.length === 0 ? (
        <Card className="p-12 text-center">
          <div className="text-gray-400 mb-4">
            <Plus className="w-16 h-16 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              No Ad Accounts Connected
            </h3>
            <p className="text-gray-500 mb-6">
              Connect your advertising accounts to start managing campaigns
            </p>
            <Button onClick={() => router.push("/ad-accounts/bind")}>
              <Plus className="w-4 h-4 mr-2" />
              Bind Your First Account
            </Button>
          </div>
        </Card>
      ) : (
        <div className="grid gap-4">
          {accounts.map((account) => (
            <Card key={account.id} className="p-6">
              <div className="flex items-start justify-between">
                <div className="flex items-start gap-4 flex-1">
                  {/* Platform Icon */}
                  <div className="text-4xl">
                    {platformIcons[account.platform] || "📱"}
                  </div>

                  {/* Account Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-semibold">
                        {account.accountName}
                      </h3>
                      {account.isActive && (
                        <Badge variant="default" className="bg-green-500">
                          <CheckCircle2 className="w-3 h-3 mr-1" />
                          Active
                        </Badge>
                      )}
                      {getStatusBadge(account.status)}
                    </div>

                    <div className="text-sm text-gray-600 space-y-1">
                      <p>
                        <span className="font-medium">Platform:</span>{" "}
                        {platformNames[account.platform] || account.platform}
                      </p>
                      <p>
                        <span className="font-medium">Account ID:</span>{" "}
                        {account.platformAccountId}
                      </p>
                      <p>
                        <span className="font-medium">Last Synced:</span>{" "}
                        {formatDate(account.lastSyncedAt)}
                      </p>
                      <p>
                        <span className="font-medium">Connected:</span>{" "}
                        {formatDate(account.createdAt)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex gap-2">
                  {!account.isActive && account.status === "active" && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleActivate(account.id)}
                      disabled={activatingId === account.id}
                    >
                      {activatingId === account.id ? (
                        <RefreshCw className="w-4 h-4 animate-spin" />
                      ) : (
                        "Set Active"
                      )}
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleUnbind(account.id)}
                    disabled={deletingId === account.id}
                  >
                    {deletingId === account.id ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <>
                        <Trash2 className="w-4 h-4 mr-1" />
                        Unbind
                      </>
                    )}
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
