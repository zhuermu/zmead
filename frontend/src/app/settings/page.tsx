"use client";

import { useState } from "react";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ProfileSettings } from "@/components/settings/ProfileSettings";
import { NotificationSettings } from "@/components/settings/NotificationSettings";
import { DataPrivacySettings } from "@/components/settings/DataPrivacySettings";
import { ModelPreferences } from "@/components/settings/ModelPreferences";

type TabType = "profile" | "notifications" | "models" | "data";

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>("profile");

  const tabs = [
    { id: "profile" as TabType, label: "Profile", icon: "👤" },
    { id: "notifications" as TabType, label: "Notifications", icon: "🔔" },
    { id: "models" as TabType, label: "AI Models", icon: "🤖" },
    { id: "data" as TabType, label: "Data & Privacy", icon: "🔒" },
  ];

  return (
    <DashboardLayout>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Settings</h1>
        <p className="text-gray-600 mt-2">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Tab Navigation - Sidebar on desktop, horizontal on mobile */}
        <div className="lg:col-span-1">
          <Card className="p-2">
            <nav className="flex lg:flex-col gap-1">
              {tabs.map((tab) => (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? "default" : "ghost"}
                  className={`w-full justify-start ${
                    activeTab === tab.id
                      ? "bg-blue-500 text-white hover:bg-blue-600"
                      : "hover:bg-gray-100"
                  }`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <span className="mr-2">{tab.icon}</span>
                  <span className="hidden sm:inline">{tab.label}</span>
                </Button>
              ))}
            </nav>
          </Card>
        </div>

        {/* Tab Content */}
        <div className="lg:col-span-3">
          <Card className="p-6">
            {activeTab === "profile" && <ProfileSettings />}
            {activeTab === "notifications" && <NotificationSettings />}
            {activeTab === "models" && <ModelPreferences />}
            {activeTab === "data" && <DataPrivacySettings />}
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
