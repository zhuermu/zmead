"use client";

import { useEffect, useState, useRef, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Badge } from "@/components/ui/badge";
import api from "@/lib/api";
import { RefreshCw, CheckCircle2, AlertCircle, Building2, Shield } from "lucide-react";

interface AvailableAccount {
  id: string;
  name: string;
  currency?: string;
  timezone?: string;
  isManager: boolean;
  managerId?: string;
}

function OAuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [step, setStep] = useState<"loading" | "selecting" | "binding" | "success" | "error">("loading");
  const [error, setError] = useState<string | null>(null);
  const [availableAccounts, setAvailableAccounts] = useState<AvailableAccount[]>([]);
  const [selectedAccountIds, setSelectedAccountIds] = useState<Set<string>>(new Set());
  const [boundAccountsCount, setBoundAccountsCount] = useState(0);
  const [sessionToken, setSessionToken] = useState<string>("");
  const [platform, setPlatform] = useState<string>("");

  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double execution in React StrictMode (development only)
    if (hasProcessed.current) {
      return;
    }
    hasProcessed.current = true;
    fetchAvailableAccounts();
  }, []);

  const fetchAvailableAccounts = async () => {
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

      setPlatform(state);

      // Fetch available accounts from backend
      const response = await api.post("/ad-accounts/oauth/available-accounts", {
        platform: state,
        code: code,
        redirect_uri: `${window.location.origin}/ad-accounts/callback`,
      });

      const accounts: AvailableAccount[] = response.data.accounts || [];
      const token: string = response.data.session_token || "";

      setAvailableAccounts(accounts);
      setSessionToken(token);

      // Auto-select non-manager accounts by default
      const autoSelectedIds = new Set(
        accounts.filter(acc => !acc.isManager).map(acc => acc.id)
      );
      setSelectedAccountIds(autoSelectedIds);

      setStep("selecting");
    } catch (err: any) {
      console.error("Failed to fetch available accounts:", err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to fetch available accounts"
      );
      setStep("error");
    }
  };

  const handleAccountToggle = (accountId: string) => {
    setSelectedAccountIds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(accountId)) {
        newSet.delete(accountId);
      } else {
        newSet.add(accountId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedAccountIds.size === availableAccounts.length) {
      setSelectedAccountIds(new Set());
    } else {
      setSelectedAccountIds(new Set(availableAccounts.map(acc => acc.id)));
    }
  };

  const handleBindSelectedAccounts = async () => {
    if (selectedAccountIds.size === 0) {
      setError("Please select at least one account");
      return;
    }

    setStep("binding");
    setError(null);

    try {
      const response = await api.post("/ad-accounts/oauth/bind-selected", {
        platform: platform,
        session_token: sessionToken,
        selected_account_ids: Array.from(selectedAccountIds),
      });

      setBoundAccountsCount(response.data.total || selectedAccountIds.size);
      setStep("success");

      // Redirect to ad accounts page after 2 seconds
      setTimeout(() => {
        router.push("/ad-accounts");
      }, 2000);
    } catch (err: any) {
      console.error("Failed to bind accounts:", err);
      setError(
        err.response?.data?.detail ||
          err.message ||
          "Failed to bind selected accounts"
      );
      setStep("error");
    }
  };

  // Loading state
  if (step === "loading") {
    return (
      <div className="container mx-auto py-8 max-w-3xl">
        <Card className="p-12 text-center">
          <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
          <h2 className="text-2xl font-bold mb-2">Loading Accounts...</h2>
          <p className="text-gray-600">
            Please wait while we fetch your available ad accounts.
          </p>
        </Card>
      </div>
    );
  }

  // Account selection state
  if (step === "selecting") {
    return (
      <div className="container mx-auto py-8 max-w-3xl">
        <Card className="p-8">
          <div className="mb-6">
            <h2 className="text-2xl font-bold mb-2">Select Ad Accounts</h2>
            <p className="text-gray-600">
              Choose which Google Ads accounts you want to connect. You can select multiple accounts.
            </p>
          </div>

          {/* Select All Checkbox */}
          <div className="flex items-center space-x-2 mb-4 pb-4 border-b">
            <Checkbox
              id="select-all"
              checked={selectedAccountIds.size === availableAccounts.length && availableAccounts.length > 0}
              onCheckedChange={handleSelectAll}
            />
            <label
              htmlFor="select-all"
              className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
            >
              Select All ({availableAccounts.length} accounts)
            </label>
          </div>

          {/* Account List */}
          <div className="space-y-3 mb-6">
            {availableAccounts.map((account) => (
              <div
                key={account.id}
                className={`border rounded-lg p-4 transition-all cursor-pointer hover:border-blue-400 ${
                  selectedAccountIds.has(account.id) ? "border-blue-500 bg-blue-50" : "border-gray-200"
                }`}
                onClick={() => handleAccountToggle(account.id)}
              >
                <div className="flex items-start space-x-3">
                  <Checkbox
                    id={`account-${account.id}`}
                    checked={selectedAccountIds.has(account.id)}
                    onCheckedChange={() => handleAccountToggle(account.id)}
                    onClick={(e: React.MouseEvent) => e.stopPropagation()}
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <Building2 className="w-4 h-4 text-gray-500" />
                      <label
                        htmlFor={`account-${account.id}`}
                        className="font-medium cursor-pointer"
                      >
                        {account.name}
                      </label>
                      {account.isManager && (
                        <Badge variant="secondary" className="text-xs">
                          <Shield className="w-3 h-3 mr-1" />
                          Manager Account
                        </Badge>
                      )}
                    </div>
                    <div className="text-sm text-gray-600 space-y-1">
                      <div>ID: {account.id}</div>
                      {account.currency && account.timezone && (
                        <div>
                          {account.currency} • {account.timezone}
                        </div>
                      )}
                      {account.managerId && (
                        <div className="text-xs text-gray-500">
                          Managed by: {account.managerId}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 justify-end pt-4 border-t">
            <Button variant="outline" onClick={() => router.push("/ad-accounts")}>
              Cancel
            </Button>
            <Button
              onClick={handleBindSelectedAccounts}
              disabled={selectedAccountIds.size === 0}
            >
              Connect {selectedAccountIds.size > 0 ? `${selectedAccountIds.size} ` : ""}
              Account{selectedAccountIds.size !== 1 ? "s" : ""}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // Binding state
  if (step === "binding") {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
          <h2 className="text-2xl font-bold mb-2">Connecting Accounts...</h2>
          <p className="text-gray-600">
            Binding {selectedAccountIds.size} account{selectedAccountIds.size !== 1 ? "s" : ""}...
          </p>
        </Card>
      </div>
    );
  }

  // Success state
  if (step === "success") {
    return (
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <CheckCircle2 className="w-16 h-16 text-green-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold mb-2">Successfully Connected!</h2>
          <p className="text-gray-600 mb-2">
            {boundAccountsCount} account{boundAccountsCount !== 1 ? "s have" : " has"} been connected successfully.
          </p>
          <p className="text-sm text-gray-500">
            Redirecting to ad accounts page...
          </p>
        </Card>
      </div>
    );
  }

  // Error state
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
          <Button onClick={() => window.location.reload()}>
            Try Again
          </Button>
        </div>
      </Card>
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <Suspense fallback={
      <div className="container mx-auto py-8 max-w-2xl">
        <Card className="p-12 text-center">
          <RefreshCw className="w-16 h-16 text-blue-500 mx-auto mb-4 animate-spin" />
          <h2 className="text-2xl font-bold mb-2">Loading...</h2>
        </Card>
      </div>
    }>
      <OAuthCallbackContent />
    </Suspense>
  );
}
