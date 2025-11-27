"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Edit,
  Pause,
  Play,
  Trash2,
  RefreshCw,
  ExternalLink,
} from "lucide-react";

interface Campaign {
  id: number;
  name: string;
  platform: string;
  platformCampaignId?: string;
  status: "draft" | "active" | "paused" | "deleted";
  budget: number;
  budgetType: "daily" | "lifetime";
  objective: string;
  targeting: Record<string, unknown>;
  creativeIds: number[];
  landingPageId?: number;
  createdAt: string;
  updatedAt?: string;
}

interface Creative {
  id: number;
  fileUrl: string;
  cdnUrl: string;
  fileType: "image" | "video";
  score?: number;
  tags: string[];
}

interface LandingPage {
  id: number;
  name: string;
  url: string;
  status: string;
}

interface PerformanceMetrics {
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  revenue: number;
  ctr: number;
  cpc: number;
  cpa: number;
  roas: number;
}

export default function CampaignDetailPage() {
  const router = useRouter();
  const params = useParams();
  const campaignId = params.id as string;

  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [landingPage, setLandingPage] = useState<LandingPage | null>(null);
  const [metrics, setMetrics] = useState<PerformanceMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    fetchCampaignDetails();
  }, [campaignId]);

  const fetchCampaignDetails = async () => {
    setLoading(true);
    try {
      // Fetch campaign details
      const campaignResponse = await fetch(`/api/v1/campaigns/${campaignId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!campaignResponse.ok) throw new Error("Failed to fetch campaign");

      const campaignData: Campaign = await campaignResponse.json();
      setCampaign(campaignData);

      // Fetch associated creatives
      if (campaignData.creativeIds.length > 0) {
        const creativesResponse = await fetch(
          `/api/v1/creatives?ids=${campaignData.creativeIds.join(",")}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );
        if (creativesResponse.ok) {
          const creativesData = await creativesResponse.json();
          setCreatives(creativesData.creatives || []);
        }
      }

      // Fetch landing page
      if (campaignData.landingPageId) {
        const lpResponse = await fetch(
          `/api/v1/landing-pages/${campaignData.landingPageId}`,
          {
            headers: {
              Authorization: `Bearer ${localStorage.getItem("token")}`,
            },
          }
        );
        if (lpResponse.ok) {
          const lpData = await lpResponse.json();
          setLandingPage(lpData);
        }
      }

      // Fetch performance metrics
      const metricsResponse = await fetch(
        `/api/v1/reports/metrics?entity_type=campaign&entity_id=${campaignData.platformCampaignId || campaignId}`,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
        }
      );
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setMetrics(metricsData);
      }
    } catch (error) {
      console.error("Error fetching campaign details:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleStatusChange = async (newStatus: "active" | "paused") => {
    if (!campaign) return;

    try {
      const response = await fetch(`/api/v1/campaigns/${campaignId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({ status: newStatus }),
      });

      if (!response.ok) throw new Error("Failed to update campaign status");

      await fetchCampaignDetails();
    } catch (error) {
      console.error("Error updating campaign status:", error);
      alert("Failed to update campaign status");
    }
  };

  const handleDelete = async () => {
    if (!confirm("Are you sure you want to delete this campaign?")) return;

    try {
      const response = await fetch(`/api/v1/campaigns/${campaignId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) throw new Error("Failed to delete campaign");

      router.push("/campaigns");
    } catch (error) {
      console.error("Error deleting campaign:", error);
      alert("Failed to delete campaign");
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await fetch(`/api/v1/campaigns/${campaignId}/sync`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) throw new Error("Failed to sync campaign");

      const result = await response.json();
      if (result.success) {
        alert("Campaign synced successfully!");
        await fetchCampaignDetails();
      } else {
        alert(`Sync failed: ${result.error_message}`);
      }
    } catch (error) {
      console.error("Error syncing campaign:", error);
      alert("Failed to sync campaign");
    } finally {
      setSyncing(false);
    }
  };

  const getStatusBadge = (status: Campaign["status"]) => {
    const variants: Record<Campaign["status"], string> = {
      draft: "bg-gray-200 text-gray-800",
      active: "bg-green-100 text-green-800",
      paused: "bg-yellow-100 text-yellow-800",
      deleted: "bg-red-100 text-red-800",
    };

    return (
      <Badge className={variants[status]}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </Badge>
    );
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(amount);
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat("en-US").format(num);
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    );
  }

  if (!campaign) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-12 text-center">
          <p className="text-gray-500">Campaign not found</p>
          <Button
            onClick={() => router.push("/campaigns")}
            className="mt-4"
            variant="outline"
          >
            Back to Campaigns
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6">
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => router.push("/campaigns")}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Campaigns
        </Button>

        <div className="flex justify-between items-start">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{campaign.name}</h1>
              {getStatusBadge(campaign.status)}
            </div>
            <p className="text-gray-600">
              {campaign.objective} • {campaign.platform.toUpperCase()}
            </p>
          </div>

          <div className="flex gap-2">
            {campaign.status === "active" && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("paused")}
              >
                <Pause className="w-4 h-4 mr-2" />
                Pause
              </Button>
            )}
            {campaign.status === "paused" && (
              <Button
                variant="outline"
                onClick={() => handleStatusChange("active")}
              >
                <Play className="w-4 h-4 mr-2" />
                Resume
              </Button>
            )}
            <Button
              variant="outline"
              onClick={handleSync}
              disabled={syncing}
            >
              <RefreshCw
                className={`w-4 h-4 mr-2 ${syncing ? "animate-spin" : ""}`}
              />
              Sync to Platform
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push(`/campaigns/${campaignId}/edit`)}
            >
              <Edit className="w-4 h-4 mr-2" />
              Edit
            </Button>
            <Button variant="outline" onClick={handleDelete}>
              <Trash2 className="w-4 h-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      {/* Performance Metrics */}
      {metrics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <Card className="p-4">
            <div className="text-sm text-gray-600 mb-1">Spend</div>
            <div className="text-2xl font-bold">
              {formatCurrency(metrics.spend)}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-600 mb-1">Impressions</div>
            <div className="text-2xl font-bold">
              {formatNumber(metrics.impressions)}
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-600 mb-1">Clicks</div>
            <div className="text-2xl font-bold">
              {formatNumber(metrics.clicks)}
            </div>
            <div className="text-sm text-gray-500">
              CTR: {(metrics.ctr * 100).toFixed(2)}%
            </div>
          </Card>
          <Card className="p-4">
            <div className="text-sm text-gray-600 mb-1">ROAS</div>
            <div
              className={`text-2xl font-bold ${
                metrics.roas >= 2
                  ? "text-green-600"
                  : metrics.roas >= 1
                  ? "text-yellow-600"
                  : "text-red-600"
              }`}
            >
              {metrics.roas.toFixed(2)}x
            </div>
            <div className="text-sm text-gray-500">
              Revenue: {formatCurrency(metrics.revenue)}
            </div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Campaign Configuration */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Configuration</h2>
          <div className="space-y-4">
            <div>
              <div className="text-sm text-gray-600">Budget</div>
              <div className="font-medium">
                {formatCurrency(campaign.budget)} /{" "}
                {campaign.budgetType}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Objective</div>
              <div className="font-medium">{campaign.objective}</div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Platform Campaign ID</div>
              <div className="font-medium">
                {campaign.platformCampaignId || "Not synced"}
              </div>
            </div>
            <div>
              <div className="text-sm text-gray-600">Created</div>
              <div className="font-medium">
                {new Date(campaign.createdAt).toLocaleString()}
              </div>
            </div>
            {campaign.updatedAt && (
              <div>
                <div className="text-sm text-gray-600">Last Updated</div>
                <div className="font-medium">
                  {new Date(campaign.updatedAt).toLocaleString()}
                </div>
              </div>
            )}
          </div>
        </Card>

        {/* Targeting */}
        <Card className="p-6">
          <h2 className="text-xl font-semibold mb-4">Targeting</h2>
          {Object.keys(campaign.targeting).length > 0 ? (
            <div className="space-y-2">
              {Object.entries(campaign.targeting).map(([key, value]) => (
                <div key={key}>
                  <div className="text-sm text-gray-600">
                    {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                  </div>
                  <div className="font-medium">
                    {typeof value === "object"
                      ? JSON.stringify(value)
                      : String(value)}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500">No targeting configured</p>
          )}
        </Card>
      </div>

      {/* Associated Creatives */}
      <Card className="p-6 mt-6">
        <h2 className="text-xl font-semibold mb-4">
          Associated Creatives ({creatives.length})
        </h2>
        {creatives.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {creatives.map((creative) => (
              <div
                key={creative.id}
                className="border rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                onClick={() => router.push(`/creatives/${creative.id}`)}
              >
                {creative.fileType === "image" ? (
                  <img
                    src={creative.cdnUrl}
                    alt="Creative"
                    className="w-full h-48 object-cover"
                  />
                ) : (
                  <video
                    src={creative.cdnUrl}
                    className="w-full h-48 object-cover"
                    controls
                  />
                )}
                <div className="p-2">
                  {creative.score && (
                    <div className="text-sm text-gray-600">
                      Score: {creative.score.toFixed(1)}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-gray-500">No creatives associated</p>
        )}
      </Card>

      {/* Landing Page */}
      {landingPage && (
        <Card className="p-6 mt-6">
          <h2 className="text-xl font-semibold mb-4">Landing Page</h2>
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">{landingPage.name}</div>
              <div className="text-sm text-gray-600">
                Status: {landingPage.status}
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => window.open(landingPage.url, "_blank")}
            >
              <ExternalLink className="w-4 h-4 mr-2" />
              View Page
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}
