"use client";

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AlertCircle, Bell, Check, Mail, Save } from 'lucide-react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

interface NotificationPreferences {
  creditAlerts: {
    enabled: boolean;
    warningThreshold: number;
    criticalThreshold: number;
    channels: {
      inApp: boolean;
      email: boolean;
    };
  };
}

export default function BillingSettingsPage() {
  const router = useRouter();
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    creditAlerts: {
      enabled: true,
      warningThreshold: 50,
      criticalThreshold: 10,
      channels: {
        inApp: true,
        email: true,
      },
    },
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    fetchPreferences();
  }, []);

  const fetchPreferences = async () => {
    try {
      setLoading(true);
      // In a real implementation, this would fetch from /api/v1/users/me
      // For now, we'll use default values
      const response = await api.get('/users/me');
      
      // Extract notification preferences from user data
      const userPrefs = response.data.notificationPreferences || {};
      
      setPreferences({
        creditAlerts: {
          enabled: userPrefs.creditAlerts?.enabled ?? true,
          warningThreshold: userPrefs.creditAlerts?.warningThreshold ?? 50,
          criticalThreshold: userPrefs.creditAlerts?.criticalThreshold ?? 10,
          channels: {
            inApp: userPrefs.creditAlerts?.channels?.inApp ?? true,
            email: userPrefs.creditAlerts?.channels?.email ?? true,
          },
        },
      });
      setError(null);
    } catch (err: any) {
      // If endpoint doesn't exist yet, use defaults
      console.warn('Failed to load preferences, using defaults');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      setSuccess(false);
      
      // Validate thresholds
      if (preferences.creditAlerts.warningThreshold <= preferences.creditAlerts.criticalThreshold) {
        setError('Warning threshold must be greater than critical threshold');
        return;
      }

      if (preferences.creditAlerts.criticalThreshold < 0) {
        setError('Critical threshold must be at least 0');
        return;
      }

      // Save to backend
      await api.put('/users/me', {
        notificationPreferences: {
          creditAlerts: preferences.creditAlerts,
        },
      });

      setSuccess(true);
      setError(null);
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updatePreference = (path: string[], value: any) => {
    setPreferences(prev => {
      const newPrefs = { ...prev };
      let current: any = newPrefs;
      
      for (let i = 0; i < path.length - 1; i++) {
        current = current[path[i]];
      }
      
      current[path[path.length - 1]] = value;
      return newPrefs;
    });
  };

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6 max-w-4xl">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Credit Alert Settings</h1>
          <p className="text-gray-600 mt-1">Configure when and how you receive credit balance alerts</p>
        </div>
        <Button onClick={() => router.push('/billing')} variant="outline">
          Back to Billing
        </Button>
      </div>

      {/* Success Message */}
      {success && (
        <Card className="p-4 border-green-200 bg-green-50">
          <div className="flex items-center gap-2 text-green-700">
            <Check className="w-5 h-5" />
            <p>Settings saved successfully!</p>
          </div>
        </Card>
      )}

      {/* Error Message */}
      {error && (
        <Card className="p-4 border-red-200 bg-red-50">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
        </Card>
      )}

      {/* Alert Settings */}
      <Card className="p-6 space-y-6">
        <div>
          <h2 className="text-xl font-semibold mb-2">Credit Balance Alerts</h2>
          <p className="text-sm text-gray-600">
            Get notified when your credit balance falls below certain thresholds
          </p>
        </div>

        {/* Enable/Disable Alerts */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-gray-600" />
            <div>
              <p className="font-medium">Enable Credit Alerts</p>
              <p className="text-sm text-gray-600">Receive notifications about your credit balance</p>
            </div>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              type="checkbox"
              checked={preferences.creditAlerts.enabled}
              onChange={(e) => updatePreference(['creditAlerts', 'enabled'], e.target.checked)}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
          </label>
        </div>

        {/* Threshold Settings */}
        {preferences.creditAlerts.enabled && (
          <div className="space-y-6">
            {/* Warning Threshold */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Warning Threshold
              </label>
              <div className="flex items-center gap-4">
                <Input
                  type="number"
                  min="0"
                  step="10"
                  value={preferences.creditAlerts.warningThreshold}
                  onChange={(e) => updatePreference(['creditAlerts', 'warningThreshold'], Number(e.target.value))}
                  className="max-w-xs"
                />
                <span className="text-sm text-gray-600">credits</span>
              </div>
              <p className="text-sm text-gray-500">
                You'll receive a warning notification when your balance falls below this amount
              </p>
            </div>

            {/* Critical Threshold */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-700">
                Critical Threshold
              </label>
              <div className="flex items-center gap-4">
                <Input
                  type="number"
                  min="0"
                  step="5"
                  value={preferences.creditAlerts.criticalThreshold}
                  onChange={(e) => updatePreference(['creditAlerts', 'criticalThreshold'], Number(e.target.value))}
                  className="max-w-xs"
                />
                <span className="text-sm text-gray-600">credits</span>
              </div>
              <p className="text-sm text-gray-500">
                You'll receive an urgent notification when your balance falls below this amount
              </p>
            </div>

            {/* Notification Channels */}
            <div className="space-y-3">
              <label className="block text-sm font-medium text-gray-700">
                Notification Channels
              </label>
              
              {/* In-App Notifications */}
              <div className="flex items-center gap-3 p-3 border rounded-lg">
                <input
                  type="checkbox"
                  id="inApp"
                  checked={preferences.creditAlerts.channels.inApp}
                  onChange={(e) => updatePreference(['creditAlerts', 'channels', 'inApp'], e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <label htmlFor="inApp" className="flex items-center gap-2 cursor-pointer flex-1">
                  <Bell className="w-4 h-4 text-gray-600" />
                  <div>
                    <p className="font-medium text-sm">In-App Notifications</p>
                    <p className="text-xs text-gray-500">Show alerts in the application</p>
                  </div>
                </label>
              </div>

              {/* Email Notifications */}
              <div className="flex items-center gap-3 p-3 border rounded-lg">
                <input
                  type="checkbox"
                  id="email"
                  checked={preferences.creditAlerts.channels.email}
                  onChange={(e) => updatePreference(['creditAlerts', 'channels', 'email'], e.target.checked)}
                  className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
                />
                <label htmlFor="email" className="flex items-center gap-2 cursor-pointer flex-1">
                  <Mail className="w-4 h-4 text-gray-600" />
                  <div>
                    <p className="font-medium text-sm">Email Notifications</p>
                    <p className="text-xs text-gray-500">Send alerts to your email address</p>
                  </div>
                </label>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* Preview */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">Alert Preview</h3>
        <div className="space-y-3">
          {preferences.creditAlerts.enabled ? (
            <>
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
                  <div>
                    <p className="font-medium text-yellow-700">Warning Alert</p>
                    <p className="text-sm text-yellow-600 mt-1">
                      Your credit balance has fallen below {preferences.creditAlerts.warningThreshold} credits. 
                      Consider recharging soon.
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-red-500 mt-0.5" />
                  <div>
                    <p className="font-medium text-red-700">Critical Alert</p>
                    <p className="text-sm text-red-600 mt-1">
                      Your credit balance has fallen below {preferences.creditAlerts.criticalThreshold} credits. 
                      Please recharge immediately to continue using services.
                    </p>
                  </div>
                </div>
              </div>

              <p className="text-sm text-gray-500 mt-4">
                Alerts will be sent via: {
                  [
                    preferences.creditAlerts.channels.inApp && 'In-App',
                    preferences.creditAlerts.channels.email && 'Email'
                  ].filter(Boolean).join(' and ') || 'No channels selected'
                }
              </p>
            </>
          ) : (
            <p className="text-sm text-gray-500">
              Credit alerts are currently disabled. Enable them to receive notifications.
            </p>
          )}
        </div>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        <Button 
          onClick={() => router.push('/billing')}
          variant="outline"
        >
          Cancel
        </Button>
        <Button 
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {saving ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Save Settings
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
