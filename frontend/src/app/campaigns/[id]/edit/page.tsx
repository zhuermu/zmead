"use client";

import { useState, useEffect } from "react";
import { useRouter, useParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, Save } from "lucide-react";

interface Campaign {
  id: number;
  name: string;
  platform: string;
  status: "draft" | "active" | "paused" | "deleted";
  budget: number;
  budgetType: "daily" | "lifetime";
  objective: string;
  targeting: Record<string, unknown>;
  creativeIds: number[];
  landingPageId?: number;
}

interface Creative {
  id: number;
  cdnUrl: string;
  fileType: string;
  score?: number;
}

const OBJECTIVES = [
  { value: "awareness", label: "Brand Awareness" },
  { value: "traffic", label: "Traffic" },
  { value: "engagement", label: "Engagement" },
  { value: "leads", label: "Lead Generation" },
  { value: "conversions", label: "Conversions" },
  { value: "sales", label: "Sales" },
];

export default function EditCampaignPage() {
  const router = useRouter();
  const params = useParams();
  const campaignId = params.id as string;

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [creatives, setCreatives] = useState<Creative[]>([]);

  const [formData, setFormData] = useState({
    name: "",
    objective: "",
    status: "draft" as Campaign["status"],
    budget: "",
    budgetType: "daily" as "daily" | "lifetime",
    targeting: {} as Record<string, unknown>,
    creativeIds: [] as number[],
    landingPageId: null as number | null,
  });

  useEffect(() => {
    fetchCampaign();
    fetchCreatives();
  }, [campaignId]);

  const fetchCampaign = async () => {
    try {
      const response = await fetch(`/api/v1/campaigns/${campaignId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      if (!response.ok) throw new Error("Failed to fetch campaign");

      const data: Campaign = await response.json();
      setCampaign(data);
      setFormData({
        name: data.name,
        objective: data.objective,
        status: data.status,
        budget: data.budget.toString(),
        budgetType: data.budgetType,
        targeting: data.targeting,
        creativeIds: data.creativeIds,
        landingPageId: data.landingPageId || null,
      });
    } catch (error) {
      console.error("Error fetching campaign:", error);
      alert("Failed to load campaign");
      router.push("/campaigns");
    } finally {
      setLoading(false);
    }
  };

  const fetchCreatives = async () => {
    try {
      const response = await fetch("/api/v1/creatives?status=active", {
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });
      if (response.ok) {
        const data = await response.json();
        setCreatives(data.creatives || []);
      }
    } catch (error) {
      console.error("Error fetching creatives:", error);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);

    try {
      const response = await fetch(`/api/v1/campaigns/${campaignId}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          name: formData.name,
          objective: formData.objective,
          status: formData.status,
          budget: parseFloat(formData.budget),
          budget_type: formData.budgetType,
          targeting: formData.targeting,
          creative_ids: formData.creativeIds,
          landing_page_id: formData.landingPageId,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to update campaign");
      }

      router.push(`/campaigns/${campaignId}`);
    } catch (error) {
      console.error("Error updating campaign:", error);
      alert(error instanceof Error ? error.message : "Failed to update campaign");
    } finally {
      setSaving(false);
    }
  };

  const toggleCreative = (creativeId: number) => {
    setFormData((prev) => ({
      ...prev,
      creativeIds: prev.creativeIds.includes(creativeId)
        ? prev.creativeIds.filter((id) => id !== creativeId)
        : [...prev.creativeIds, creativeId],
    }));
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
    <div className="container mx-auto p-6 max-w-4xl">
      {/* Header */}
      <div className="mb-6">
        <Button
          variant="outline"
          onClick={() => router.push(`/campaigns/${campaignId}`)}
          className="mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Back to Campaign
        </Button>
        <h1 className="text-3xl font-bold">Edit Campaign</h1>
        <p className="text-gray-600 mt-1">Update your campaign settings</p>
      </div>

      <form onSubmit={handleSubmit}>
        {/* Basic Information */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Basic Information</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Campaign Name *
              </label>
              <Input
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                placeholder="e.g., Summer Sale 2024"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Objective *
              </label>
              <select
                value={formData.objective}
                onChange={(e) =>
                  setFormData({ ...formData, objective: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                {OBJECTIVES.map((obj) => (
                  <option key={obj.value} value={obj.value}>
                    {obj.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Status *</label>
              <select
                value={formData.status}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    status: e.target.value as Campaign["status"],
                  })
                }
                className="w-full px-3 py-2 border rounded-md"
                required
              >
                <option value="draft">Draft</option>
                <option value="active">Active</option>
                <option value="paused">Paused</option>
              </select>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Budget *
                </label>
                <Input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.budget}
                  onChange={(e) =>
                    setFormData({ ...formData, budget: e.target.value })
                  }
                  placeholder="100.00"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Budget Type *
                </label>
                <select
                  value={formData.budgetType}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      budgetType: e.target.value as "daily" | "lifetime",
                    })
                  }
                  className="w-full px-3 py-2 border rounded-md"
                  required
                >
                  <option value="daily">Daily</option>
                  <option value="lifetime">Lifetime</option>
                </select>
              </div>
            </div>
          </div>
        </Card>

        {/* Targeting */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Targeting</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-2">
                  Minimum Age
                </label>
                <Input
                  type="number"
                  min="13"
                  max="65"
                  value={
                    (formData.targeting.ageMin as number | undefined) || ""
                  }
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      targeting: {
                        ...formData.targeting,
                        ageMin: parseInt(e.target.value) || undefined,
                      },
                    })
                  }
                  placeholder="18"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">
                  Maximum Age
                </label>
                <Input
                  type="number"
                  min="13"
                  max="65"
                  value={
                    (formData.targeting.ageMax as number | undefined) || ""
                  }
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      targeting: {
                        ...formData.targeting,
                        ageMax: parseInt(e.target.value) || undefined,
                      },
                    })
                  }
                  placeholder="65"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Locations (comma-separated)
              </label>
              <Input
                value={
                  ((formData.targeting.locations as string[]) || []).join(", ")
                }
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    targeting: {
                      ...formData.targeting,
                      locations: e.target.value
                        .split(",")
                        .map((l) => l.trim())
                        .filter(Boolean),
                    },
                  })
                }
                placeholder="United States, Canada, United Kingdom"
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">
                Interests (comma-separated)
              </label>
              <Input
                value={
                  ((formData.targeting.interests as string[]) || []).join(", ")
                }
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    targeting: {
                      ...formData.targeting,
                      interests: e.target.value
                        .split(",")
                        .map((i) => i.trim())
                        .filter(Boolean),
                    },
                  })
                }
                placeholder="Fashion, Shopping, Technology"
              />
            </div>
          </div>
        </Card>

        {/* Creatives */}
        <Card className="p-6 mb-6">
          <h2 className="text-xl font-semibold mb-4">Creatives</h2>
          <p className="text-gray-600 mb-4">
            Select creatives for this campaign
          </p>
          {creatives.length === 0 ? (
            <p className="text-gray-500">No creatives available</p>
          ) : (
            <div className="grid grid-cols-3 gap-4">
              {creatives.map((creative) => (
                <div
                  key={creative.id}
                  onClick={() => toggleCreative(creative.id)}
                  className={`relative border rounded-lg overflow-hidden cursor-pointer transition-all ${
                    formData.creativeIds.includes(creative.id)
                      ? "border-blue-600 ring-2 ring-blue-600"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
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
                    />
                  )}
                  {formData.creativeIds.includes(creative.id) && (
                    <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full p-1">
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Action Buttons */}
        <div className="flex justify-between">
          <Button
            type="button"
            variant="outline"
            onClick={() => router.push(`/campaigns/${campaignId}`)}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            <Save className="w-4 h-4 mr-2" />
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </form>
    </div>
  );
}
