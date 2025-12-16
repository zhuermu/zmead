"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import api from "@/lib/api";

interface AdAccount {
  id: number;
  platform: string;
  platformAccountId: string;
  accountName: string;
  status: string;
  isManager?: boolean;
  managerAccountId?: string;
}

interface Creative {
  id: number;
  cdn_url: string;
  signed_url?: string;
  file_type: string;
  score?: number;
}

interface LandingPage {
  id: number;
  name: string;
  url: string;
  status: string;
}

interface CampaignFormData {
  adAccountId: number | null;
  name: string;
  objective: string;
  budget: string;
  budgetType: "daily" | "lifetime";
  targeting: {
    ageMin?: number;
    ageMax?: number;
    genders?: string[];
    locations?: string[];
    interests?: string[];
  };
  creativeIds: number[];
  landingPageId: number | null;
}

const OBJECTIVES = [
  { value: "awareness", label: "Brand Awareness" },
  { value: "traffic", label: "Traffic" },
  { value: "engagement", label: "Engagement" },
  { value: "leads", label: "Lead Generation" },
  { value: "conversions", label: "Conversions" },
  { value: "sales", label: "Sales" },
];

export default function NewCampaignPage() {
  const router = useRouter();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [adAccounts, setAdAccounts] = useState<AdAccount[]>([]);
  const [creatives, setCreatives] = useState<Creative[]>([]);
  const [landingPages, setLandingPages] = useState<LandingPage[]>([]);

  const [formData, setFormData] = useState<CampaignFormData>({
    adAccountId: null,
    name: "",
    objective: "conversions",
    budget: "",
    budgetType: "daily",
    targeting: {},
    creativeIds: [],
    landingPageId: null,
  });

  // Separate state for text inputs to allow spaces while typing
  const [locationsInput, setLocationsInput] = useState("");
  const [interestsInput, setInterestsInput] = useState("");

  useEffect(() => {
    fetchAdAccounts();
    fetchCreatives();
    fetchLandingPages();
  }, []);

  const fetchAdAccounts = async () => {
    try {
      const response = await api.get("/ad-accounts");
      const data = response.data;
      // Handle both array and paginated response formats
      const accounts = Array.isArray(data) ? data : (data.items || []);
      setAdAccounts(accounts.filter((acc: AdAccount) => acc.status === "active"));
    } catch (error) {
      console.error("Error fetching ad accounts:", error);
    }
  };

  const fetchCreatives = async () => {
    try {
      const response = await api.get("/creatives", {
        params: { status: "active", page_size: 100 }
      });
      const data = response.data;
      setCreatives(data.creatives || data.items || []);
    } catch (error) {
      console.error("Error fetching creatives:", error);
    }
  };

  const fetchLandingPages = async () => {
    try {
      const response = await api.get("/landing-pages", { params: { status: "published" } });
      const data = response.data;
      setLandingPages(data.landing_pages || data.items || []);
    } catch (error) {
      console.error("Error fetching landing pages:", error);
    }
  };

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const response = await api.post("/campaigns", {
        ad_account_id: formData.adAccountId,
        name: formData.name,
        objective: formData.objective,
        budget: parseFloat(formData.budget),
        budget_type: formData.budgetType,
        targeting: formData.targeting,
        creative_ids: formData.creativeIds,
        landing_page_id: formData.landingPageId,
      });

      const campaign = response.data;
      router.push(`/campaigns/${campaign.id}`);
    } catch (error: any) {
      console.error("Error creating campaign:", error);
      const message = error.response?.data?.detail || error.message || "Failed to create campaign";
      alert(message);
    } finally {
      setLoading(false);
    }
  };

  const canProceed = () => {
    switch (step) {
      case 1:
        return formData.adAccountId !== null;
      case 2:
        return formData.name.trim() !== "" && formData.budget !== "" && parseFloat(formData.budget) > 0;
      case 3:
        return true; // Targeting is optional
      case 4:
        return formData.creativeIds.length > 0;
      case 5:
        return true; // Review step - all validations passed in previous steps
      default:
        return false;
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

  return (
    <div className="container mx-auto p-6 max-w-4xl">
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
        <h1 className="text-3xl font-bold">Create New Campaign</h1>
        <p className="text-gray-600 mt-1">
          Follow the steps to set up your advertising campaign
        </p>
      </div>

      {/* Progress Steps */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          {[
            { num: 1, label: "Ad Account" },
            { num: 2, label: "Basic Info" },
            { num: 3, label: "Targeting" },
            { num: 4, label: "Creatives" },
            { num: 5, label: "Review" },
          ].map((s, idx) => (
            <div key={s.num} className="flex items-center flex-1">
              <div className="flex flex-col items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-semibold ${
                    step > s.num
                      ? "bg-green-500 text-white"
                      : step === s.num
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {step > s.num ? <Check className="w-5 h-5" /> : s.num}
                </div>
                <div className="text-sm mt-2 text-center">{s.label}</div>
              </div>
              {idx < 4 && (
                <div
                  className={`flex-1 h-1 mx-2 ${
                    step > s.num ? "bg-green-500" : "bg-gray-200"
                  }`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <Card className="p-6 mb-6">
        {/* Step 1: Ad Account Selection */}
        {step === 1 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Select Ad Account</h2>
            <p className="text-gray-600 mb-4">
              Choose which ad account to use for this campaign
            </p>
            {adAccounts.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">
                  No active ad accounts found. Please connect an ad account first.
                </p>
                <Button onClick={() => router.push("/settings/ad-accounts")}>
                  Connect Ad Account
                </Button>
              </div>
            ) : (
              <div className="space-y-3">
                {adAccounts.map((account) => (
                  <div
                    key={account.id}
                    onClick={() =>
                      setFormData({ ...formData, adAccountId: account.id })
                    }
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      formData.adAccountId === account.id
                        ? "border-blue-600 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium">{account.accountName}</div>
                        <div className="text-sm text-gray-600">
                          {account.platform.toUpperCase()} • ID: {account.platformAccountId}
                        </div>
                      </div>
                      {formData.adAccountId === account.id && (
                        <Check className="w-5 h-5 text-blue-600" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Step 2: Basic Information */}
        {step === 2 && (
          <div>
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
                >
                  {OBJECTIVES.map((obj) => (
                    <option key={obj.value} value={obj.value}>
                      {obj.label}
                    </option>
                  ))}
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
                  >
                    <option value="daily">Daily</option>
                    <option value="lifetime">Lifetime</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Step 3: Targeting */}
        {step === 3 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Targeting (Optional)</h2>
            <p className="text-gray-600 mb-4">
              Configure audience targeting for your campaign
            </p>
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
                    value={formData.targeting.ageMin || ""}
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
                    value={formData.targeting.ageMax || ""}
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
                  value={locationsInput}
                  onChange={(e) => setLocationsInput(e.target.value)}
                  onBlur={(e) => {
                    const locations = e.target.value
                      .split(",")
                      .map((l) => l.trim())
                      .filter(Boolean);
                    setFormData({
                      ...formData,
                      targeting: { ...formData.targeting, locations },
                    });
                    setLocationsInput(locations.join(", "));
                  }}
                  placeholder="United States, Canada, United Kingdom"
                />
              </div>

              <div>
                <label className="block text-sm font-medium mb-2">
                  Interests (comma-separated)
                </label>
                <Input
                  value={interestsInput}
                  onChange={(e) => setInterestsInput(e.target.value)}
                  onBlur={(e) => {
                    const interests = e.target.value
                      .split(",")
                      .map((i) => i.trim())
                      .filter(Boolean);
                    setFormData({
                      ...formData,
                      targeting: { ...formData.targeting, interests },
                    });
                    setInterestsInput(interests.join(", "));
                  }}
                  placeholder="Fashion, Shopping, Technology"
                />
              </div>
            </div>
          </div>
        )}

        {/* Step 4: Creative Selection */}
        {step === 4 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Select Creatives *</h2>
            <p className="text-gray-600 mb-4">
              Choose one or more creatives for this campaign
            </p>
            {creatives.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-gray-500 mb-4">
                  No creatives found. Please create some creatives first.
                </p>
                <Button onClick={() => router.push("/creatives")}>
                  Go to Creatives
                </Button>
              </div>
            ) : (
              <>
                {formData.creativeIds.length > 0 && (
                  <div className="mb-4 text-sm text-blue-600">
                    {formData.creativeIds.length} creative(s) selected
                  </div>
                )}
                <div className="max-h-[400px] overflow-y-auto pr-2">
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
                        {creative.file_type === "image" ? (
                          <img
                            src={creative.signed_url || creative.cdn_url}
                            alt="Creative"
                            className="w-full h-48 object-cover"
                          />
                        ) : (
                          <video
                            src={creative.signed_url || creative.cdn_url}
                            className="w-full h-48 object-cover"
                          />
                        )}
                        {formData.creativeIds.includes(creative.id) && (
                          <div className="absolute top-2 right-2 bg-blue-600 text-white rounded-full p-1">
                            <Check className="w-4 h-4" />
                          </div>
                        )}
                        {creative.score && (
                          <div className="absolute bottom-2 left-2 bg-black bg-opacity-60 text-white px-2 py-1 rounded text-sm">
                            Score: {creative.score.toFixed(1)}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="mt-4 text-sm text-gray-500 text-center">
                  Showing {creatives.length} creative(s)
                </div>
              </>
            )}
          </div>
        )}

        {/* Step 5: Review */}
        {step === 5 && (
          <div>
            <h2 className="text-xl font-semibold mb-4">Review & Create</h2>
            <p className="text-gray-600 mb-4">
              Review your campaign settings before creating
            </p>
            <div className="space-y-4">
              <div className="border-b pb-3">
                <div className="text-sm text-gray-600">Ad Account</div>
                <div className="font-medium">
                  {adAccounts.find((a) => a.id === formData.adAccountId)
                    ?.accountName || "N/A"}
                </div>
                <div className="text-sm text-gray-500">
                  {adAccounts.find((a) => a.id === formData.adAccountId)
                    ?.platform.toUpperCase()} • ID: {adAccounts.find((a) => a.id === formData.adAccountId)
                    ?.platformAccountId}
                </div>
              </div>
              <div className="border-b pb-3">
                <div className="text-sm text-gray-600">Campaign Name</div>
                <div className="font-medium">{formData.name}</div>
              </div>
              <div className="border-b pb-3">
                <div className="text-sm text-gray-600">Objective</div>
                <div className="font-medium">
                  {OBJECTIVES.find((o) => o.value === formData.objective)
                    ?.label || formData.objective}
                </div>
              </div>
              <div className="border-b pb-3">
                <div className="text-sm text-gray-600">Budget</div>
                <div className="font-medium">
                  ${formData.budget} / {formData.budgetType}
                </div>
              </div>
              <div className="border-b pb-3">
                <div className="text-sm text-gray-600">Creatives Selected</div>
                <div className="font-medium">{formData.creativeIds.length}</div>
              </div>
              {formData.landingPageId && (
                <div className="border-b pb-3">
                  <div className="text-sm text-gray-600">Landing Page</div>
                  <div className="font-medium">
                    {landingPages.find((lp) => lp.id === formData.landingPageId)
                      ?.name || "N/A"}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </Card>

      {/* Navigation Buttons */}
      <div className="flex justify-between">
        <Button
          variant="outline"
          onClick={() => setStep(step - 1)}
          disabled={step === 1}
        >
          <ArrowLeft className="w-4 h-4 mr-2" />
          Previous
        </Button>

        {step < 5 ? (
          <Button onClick={() => setStep(step + 1)} disabled={!canProceed()}>
            Next
            <ArrowRight className="w-4 h-4 ml-2" />
          </Button>
        ) : (
          <Button onClick={handleSubmit} disabled={loading || !canProceed()}>
            {loading ? "Creating..." : "Create Campaign"}
          </Button>
        )}
      </div>
    </div>
  );
}
