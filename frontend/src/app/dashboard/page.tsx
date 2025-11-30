'use client';

import { useState, useEffect } from 'react';
import { ProtectedRoute, useAuth } from '@/components/auth';
import { DashboardLayout } from '@/components/layout';
import { MetricCard, TrendChart, AISuggestionsCard } from '@/components/dashboard';

interface DashboardMetrics {
  today: {
    spend: number;
    roas: number;
    cpa: number;
  };
  yesterday: {
    spend: number;
    roas: number;
    cpa: number;
  };
}

interface TrendDataPoint {
  date: string;
  spend: number;
  roas: number;
  cpa: number;
}

interface AISuggestion {
  id: string;
  title: string;
  description: string;
  action?: string;
  actionLabel?: string;
  priority: 'high' | 'medium' | 'low';
}

function DashboardContent() {
  const { user } = useAuth();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([]);
  const [suggestions, setSuggestions] = useState<AISuggestion[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate API call to fetch dashboard data
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        
        // TODO: Replace with actual API calls
        // For now, using mock data
        await new Promise(resolve => setTimeout(resolve, 1000));
        
        // Mock metrics data
        setMetrics({
          today: {
            spend: 1250.50,
            roas: 3.45,
            cpa: 12.30
          },
          yesterday: {
            spend: 1100.00,
            roas: 3.20,
            cpa: 13.50
          }
        });

        // Mock trend data (7 days)
        const mockTrendData: TrendDataPoint[] = [
          { date: '11/20', spend: 980.00, roas: 3.10, cpa: 14.20 },
          { date: '11/21', spend: 1050.00, roas: 3.15, cpa: 13.80 },
          { date: '11/22', spend: 1120.00, roas: 3.25, cpa: 13.20 },
          { date: '11/23', spend: 1080.00, roas: 3.18, cpa: 13.60 },
          { date: '11/24', spend: 1150.00, roas: 3.30, cpa: 13.00 },
          { date: '11/25', spend: 1100.00, roas: 3.20, cpa: 13.50 },
          { date: '11/26', spend: 1250.50, roas: 3.45, cpa: 12.30 }
        ];
        setTrendData(mockTrendData);

        // Mock AI suggestions
        const mockSuggestions: AISuggestion[] = [
          {
            id: '1',
            title: 'Optimize Campaign Budget',
            description: 'Campaign "Summer Sale" is performing 25% better than average. Consider increasing budget by $200/day.',
            action: 'optimize_budget',
            actionLabel: 'Apply Suggestion',
            priority: 'high'
          },
          {
            id: '2',
            title: 'Update Creative Assets',
            description: 'Your top-performing creative has been running for 14 days. Refresh it to avoid ad fatigue.',
            action: 'refresh_creative',
            actionLabel: 'Generate New Creative',
            priority: 'medium'
          },
          {
            id: '3',
            title: 'Expand Target Audience',
            description: 'Similar audiences to your current targeting show high engagement potential.',
            action: 'expand_audience',
            actionLabel: 'View Recommendations',
            priority: 'low'
          }
        ];
        setSuggestions(mockSuggestions);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const handleSuggestionAction = (suggestion: AISuggestion) => {
    console.log('Action clicked:', suggestion);
    // TODO: Implement action handling
    alert(`Action: ${suggestion.action}\nThis will be implemented in the AI Agent integration.`);
  };

  return (
    <DashboardLayout>
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">
          Welcome back, {user?.displayName}!
        </h1>
        <p className="text-gray-600">
          Here&apos;s what&apos;s happening with your campaigns today.
        </p>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <MetricCard
          title="Total Spend"
          value={metrics?.today.spend || 0}
          previousValue={metrics?.yesterday.spend}
          format="currency"
          loading={loading}
        />
        <MetricCard
          title="ROAS"
          value={metrics?.today.roas || 0}
          previousValue={metrics?.yesterday.roas}
          format="number"
          loading={loading}
        />
        <MetricCard
          title="CPA"
          value={metrics?.today.cpa || 0}
          previousValue={metrics?.yesterday.cpa}
          format="currency"
          loading={loading}
        />
      </div>

      {/* Trend Chart */}
      <div className="mb-8">
        <TrendChart data={trendData} loading={loading} />
      </div>

      {/* AI Suggestions */}
      <div className="mb-8">
        <AISuggestionsCard 
          suggestions={suggestions} 
          loading={loading}
          onActionClick={handleSuggestionAction}
        />
      </div>

      {/* Credits Overview */}
      {user && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Total Credits</h3>
            <p className="text-3xl font-bold text-gray-900">
              {(Number(user.giftedCredits) + Number(user.purchasedCredits)).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-2">Available balance</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Gifted Credits</h3>
            <p className="text-3xl font-bold text-green-600">
              {Number(user.giftedCredits).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-2">From registration bonus</p>
          </div>
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-sm font-medium text-gray-500 mb-1">Purchased Credits</h3>
            <p className="text-3xl font-bold text-blue-600">
              {Number(user.purchasedCredits).toFixed(2)}
            </p>
            <p className="text-xs text-gray-500 mt-2">From recharges</p>
          </div>
        </div>
      )}

    </DashboardLayout>
  );
}

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}
