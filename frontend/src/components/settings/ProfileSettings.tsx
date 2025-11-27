"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/store";

interface UserProfile {
  display_name: string;
  email: string;
  avatar_url: string | null;
  language: string;
  timezone: string;
}

const LANGUAGES = [
  { value: "en", label: "English" },
  { value: "zh", label: "中文" },
  { value: "es", label: "Español" },
  { value: "fr", label: "Français" },
  { value: "de", label: "Deutsch" },
  { value: "ja", label: "日本語" },
];

const TIMEZONES = [
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "Eastern Time (ET)" },
  { value: "America/Chicago", label: "Central Time (CT)" },
  { value: "America/Denver", label: "Mountain Time (MT)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT)" },
  { value: "Europe/London", label: "London (GMT)" },
  { value: "Europe/Paris", label: "Paris (CET)" },
  { value: "Asia/Tokyo", label: "Tokyo (JST)" },
  { value: "Asia/Shanghai", label: "Shanghai (CST)" },
  { value: "Asia/Singapore", label: "Singapore (SGT)" },
  { value: "Australia/Sydney", label: "Sydney (AEDT)" },
];

export function ProfileSettings() {
  const { user, setUser } = useAuthStore();
  const [profile, setProfile] = useState<UserProfile>({
    display_name: "",
    email: "",
    avatar_url: null,
    language: "en",
    timezone: "UTC",
  });
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  useEffect(() => {
    loadProfile();
  }, []);

  const loadProfile = async () => {
    try {
      setIsLoading(true);
      const response = await api.get("/users/me");
      const userData = response.data;
      setProfile({
        display_name: userData.display_name,
        email: userData.email,
        avatar_url: userData.avatar_url,
        language: userData.language,
        timezone: userData.timezone,
      });
      setAvatarPreview(userData.avatar_url);
    } catch (error) {
      console.error("Failed to load profile:", error);
      setMessage({ type: "error", text: "Failed to load profile" });
    } finally {
      setIsLoading(false);
    }
  };

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      // Validate file type
      if (!file.type.startsWith("image/")) {
        setMessage({ type: "error", text: "Please select an image file" });
        return;
      }

      // Validate file size (max 5MB)
      if (file.size > 5 * 1024 * 1024) {
        setMessage({ type: "error", text: "Image size must be less than 5MB" });
        return;
      }

      setAvatarFile(file);
      
      // Create preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setMessage(null);

      let avatarUrl = profile.avatar_url;

      // Upload avatar if changed
      if (avatarFile) {
        // Get presigned URL for avatar upload
        const uploadResponse = await api.post("/users/me/avatar-upload-url", {
          file_name: avatarFile.name,
          file_type: avatarFile.type,
        });

        const { upload_url, file_url } = uploadResponse.data;

        // Upload to S3
        await fetch(upload_url, {
          method: "PUT",
          body: avatarFile,
          headers: {
            "Content-Type": avatarFile.type,
          },
        });

        avatarUrl = file_url;
      }

      // Update profile
      const response = await api.put("/users/me", {
        display_name: profile.display_name,
        avatar_url: avatarUrl,
        language: profile.language,
        timezone: profile.timezone,
      });

      // Update user in store
      setUser(response.data);

      setMessage({ type: "success", text: "Profile updated successfully" });
      setAvatarFile(null);
    } catch (error: any) {
      console.error("Failed to save profile:", error);
      setMessage({
        type: "error",
        text: error.response?.data?.detail || "Failed to save profile",
      });
    } finally {
      setIsSaving(false);
    }
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
        <h2 className="text-2xl font-semibold text-gray-900">Profile Settings</h2>
        <p className="text-gray-600 mt-1">
          Update your personal information and preferences
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
        {/* Avatar Upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Profile Picture
          </label>
          <div className="flex items-center gap-4">
            <div className="relative">
              {avatarPreview ? (
                <img
                  src={avatarPreview}
                  alt="Avatar preview"
                  className="w-20 h-20 rounded-full object-cover border-2 border-gray-200"
                />
              ) : (
                <div className="w-20 h-20 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 text-2xl">
                  {profile.display_name.charAt(0).toUpperCase()}
                </div>
              )}
            </div>
            <div>
              <input
                type="file"
                id="avatar-upload"
                accept="image/*"
                onChange={handleAvatarChange}
                className="hidden"
              />
              <label htmlFor="avatar-upload">
                <Button type="button" variant="outline" asChild>
                  <span className="cursor-pointer">Change Picture</span>
                </Button>
              </label>
              <p className="text-xs text-gray-500 mt-1">
                JPG, PNG or GIF. Max size 5MB.
              </p>
            </div>
          </div>
        </div>

        {/* Display Name */}
        <div>
          <label htmlFor="display_name" className="block text-sm font-medium text-gray-700 mb-2">
            Display Name
          </label>
          <Input
            id="display_name"
            type="text"
            value={profile.display_name}
            onChange={(e) => setProfile({ ...profile, display_name: e.target.value })}
            placeholder="Enter your display name"
          />
        </div>

        {/* Email (Read-only) */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
            Email
          </label>
          <Input
            id="email"
            type="email"
            value={profile.email}
            disabled
            className="bg-gray-50 cursor-not-allowed"
          />
          <p className="text-xs text-gray-500 mt-1">
            Email cannot be changed. It's linked to your Google account.
          </p>
        </div>

        {/* Language */}
        <div>
          <label htmlFor="language" className="block text-sm font-medium text-gray-700 mb-2">
            Language
          </label>
          <Select
            value={profile.language}
            onValueChange={(value) => setProfile({ ...profile, language: value })}
          >
            {LANGUAGES.map((lang) => (
              <option key={lang.value} value={lang.value}>
                {lang.label}
              </option>
            ))}
          </Select>
        </div>

        {/* Timezone */}
        <div>
          <label htmlFor="timezone" className="block text-sm font-medium text-gray-700 mb-2">
            Timezone
          </label>
          <Select
            value={profile.timezone}
            onValueChange={(value) => setProfile({ ...profile, timezone: value })}
          >
            {TIMEZONES.map((tz) => (
              <option key={tz.value} value={tz.value}>
                {tz.label}
              </option>
            ))}
          </Select>
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
