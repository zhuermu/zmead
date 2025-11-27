"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface NotificationPreferences {
  email_enabled: boolean;
  in_app_enabled: boolean;
  credit_warning_threshold: number;
  credit_critical_threshold: number;
  category_preferences?: {
    [key: string]: {
      in_app: boolean;
      email: boolean;
    };
  };
}

const NOTIFICATION_CATEGORIES = [
  {
    id: "ad_rejected",
    label: "Ad Rejected",
    description: "When your ad is rejected by the platform",
    urgent: true,
  },
  {
    id: "token_expired",
    label: "Token Expired",
    description: "When your ad account token expires",
    urgent: true,
  },
  {
    id: "budget_depleted",
    label: "Budget Depleted",
    description: "When your campaign budget is exhausted",
    urgent: true,
  },
  {
    id: "credit_depleted",
    label: "Credit Depleted",
    description: "When your credit balance reaches zero",
    urgent: true,
  },
  {
    id: "daily_report",
    label: "Daily Report",
    description: "Daily performance summary",
    urgent: false,
  },
  {
    id: "ai_suggestion",
    label: "AI Suggestions",
    description: "AI-generated optimization suggestions",
    urgent: false,
  },
  {
    id: "performance_anomaly",
    label: "Performance Anomaly",
    description: "Unusual changes in CPA/ROAS",
    urgent: false,
  },
  {
    id: "creative_generated",
    label: "Creative Generated",
    description: "When creative generation is complete",
    urgent: false,
  },
  {
    id: "landing_page_generated",
    label: "Landing Page Generated",
    description: "When landing page generation is complete",
    urgent: false,
  },
  {
    id: "weekly_summary",
    label: "Weekly Summary",
    description: "Weekly performance summary",
    urgent: false,
  },
  {
    id: "new_feature",
    label: "New Features",
    description: "Announcements about new features",
    urgent: false,
  },
  {
    id: "credit_recharged",
    label: "Credit Recharged",
    description: "Confirmation of credit recharge",
    urgent: false,
  },
  {
    id: "system_maintenance",
    label: "System Maintenance",
    description: "Scheduled maintenance notifications",
    urgent: false,
  },
];

export function NotificationSettings() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    email_enabled: true,
    in_app_enabled: true,
    credit_warning_threshold: 50,
    credit_critical_threshold: 10,
    category_preferences: {},
  });
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setIsLoading(true);
      const response = await api.get("/users/me/notification-preferences");
      const prefs = response.data;
      
      // Initialize category preferences if not set
      const categoryPrefs = prefs.category_preferences || {};
      NOTIFICATION_CATEGORIES.forEach((cat) => {
        if (!categoryPrefs[cat.id]) {
          categoryPrefs[cat.id] = {
            in_app: true,
            email: true,
          };
        }
      });

      setPreferences({
        ...prefs,
        category_preferences: categoryPrefs,
      });
    } catch (error) {
      console.error("Failed to load notification preferences:", error);
      setMessage({ type: "error", text: "Failed to load preferences" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setMessage(null);

      await api.put("/users/me/notification-preferences", preferences);

      setMessage({ type: "success", text: "Notification preferences updated successfully" });
    } catch (error: any) {
      console.error("Failed to save preferences:", error);
      setMessage({
        type: "error",
        text: error.response?.data?.detail || "Failed to save preferences",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const toggleCategoryChannel = (categoryId: string, channel: "in_app" | "email") => {
    setPreferences((prev) => {
      const currentCategory = prev.category_preferences?.[categoryId] || { in_app: false, email: false };
      const currentValue = currentCategory[channel];
      
      return {
        ...prev,
        category_preferences: {
          ...prev.category_preferences,
          [categoryId]: {
            in_app: channel === 'in_app' ? !currentValue : currentCategory.in_app,
            email: channel === 'email' ? !currentValue : currentCategory.email,
          },
        },
      };
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-gray-900">Notification Preferences</h2>
        <p className="text-gray-600 mt-1">
          Manage how you receive notifications
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
        {/* Global Toggles */}
        <div className="bg-gray-50 p-4 rounded-lg space-y-4">
          <h3 className="font-medium text-gray-900">Global Settings</h3>
          
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700">In-App Notifications</p>
              <p className="text-sm text-gray-500">Show notifications in the app</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.in_app_enabled}
                onChange={(e) =>
                  setPreferences({ ...preferences, in_app_enabled: e.target.checked })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
            </label>
          </div>

          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium text-gray-700">Email Notifications</p>
              <p className="text-sm text-gray-500">Receive notifications via email</p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={preferences.email_enabled}
                onChange={(e) =>
                  setPreferences({ ...preferences, email_enabled: e.target.checked })
                }
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-500"></div>
            </label>
          </div>
        </div>

        {/* Credit Alert Thresholds */}
        <div className="bg-gray-50 p-4 rounded-lg space-y-4">
          <h3 className="font-medium text-gray-900">Credit Alerts</h3>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Warning Threshold (credits)
            </label>
            <input
              type="number"
              min="0"
              value={preferences.credit_warning_threshold}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  credit_warning_threshold: parseInt(e.target.value) || 0,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Show warning when balance falls below this amount
            </p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Critical Threshold (credits)
            </label>
            <input
              type="number"
              min="0"
              value={preferences.credit_critical_threshold}
              onChange={(e) =>
                setPreferences({
                  ...preferences,
                  credit_critical_threshold: parseInt(e.target.value) || 0,
                })
              }
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
            <p className="text-xs text-gray-500 mt-1">
              Send alert when balance falls below this amount
            </p>
          </div>
        </div>

        {/* Category-Specific Preferences */}
        <div>
          <h3 className="font-medium text-gray-900 mb-4">Notification Categories</h3>
          <div className="space-y-3">
            {NOTIFICATION_CATEGORIES.map((category) => (
              <div
                key={category.id}
                className={`p-4 rounded-lg border ${
                  category.urgent
                    ? "bg-red-50 border-red-200"
                    : "bg-white border-gray-200"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-gray-900">{category.label}</p>
                      {category.urgent && (
                        <span className="text-xs bg-red-100 text-red-800 px-2 py-0.5 rounded">
                          Urgent
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{category.description}</p>
                    {category.urgent && (
                      <p className="text-xs text-red-600 mt-1">
                        ⚠️ Urgent notifications are always sent regardless of preferences
                      </p>
                    )}
                  </div>
                  <div className="flex gap-4 ml-4">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={
                          preferences.category_preferences?.[category.id]?.in_app ?? true
                        }
                        onChange={() => toggleCategoryChannel(category.id, "in_app")}
                        disabled={category.urgent}
                        className="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <span className="text-sm text-gray-700">In-App</span>
                    </label>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={
                          preferences.category_preferences?.[category.id]?.email ?? true
                        }
                        onChange={() => toggleCategoryChannel(category.id, "email")}
                        disabled={category.urgent}
                        className="w-4 h-4 text-blue-500 border-gray-300 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                      />
                      <span className="text-sm text-gray-700">Email</span>
                    </label>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end pt-4 border-t">
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="min-w-[120px]"
          >
            {isSaving ? (
              <>
                <span className="animate-spin mr-2">⏳</span>
                Saving...
              </>
            ) : (
              "Save Changes"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
