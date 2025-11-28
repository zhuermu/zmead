"use client";

import { useState, useEffect } from 'react';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { AdAccount, MetricsSummary, TrendDataPoint } from '@/types';
import { TrendingUp, TrendingDown, DollarSign, Target, MousePointer } from 'lucide-react';
import PerformanceCharts from '@/components/reports/PerformanceCharts';
import MetricsTable from '@/components/reports/MetricsTable';

type DateRange = '7d' | '30d' | 'custom';

export default function ReportsPage() {
  const [dateRange, setDateRange] = useState<DateRange>('7d');
  const [selectedAdAccount, setSelectedAdAccount] = useState<number | 'all'>('all');
  const [adAccounts, setAdAccounts] = useState<AdAccount[]>([]);
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null);
  const [trendData, setTrendData] = useState<TrendDataPoint[]>([]);
  const [spendByCampaign, setSpendByCampaign] = useState<{ name: string; value: number }[]>([]);
  const [metricsTableData, setMetricsTableData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');

  // Fetch ad accounts
  useEffect(() => {
    const fetchAdAccounts = async () => {
      try {
        const response = await api.get('/ad-accounts');
        setAdAccounts(response.data.items || response.data);
      } catch (error) {
        console.error('Failed to fetch ad accounts:', error);
      }
    };
    fetchAdAccounts();
  }, []);

  // Fetch metrics and trend data
  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      try {
        const params: Record<string, string> = {};
        
        // Set date range
        if (dateRange === 'custom' && customStartDate && customEndDate) {
          params.start_date = customStartDate;
          params.end_date = customEndDate;
        } else {
          const days = dateRange === '7d' ? 7 : 30;
          const endDate = new Date();
          const startDate = new Date();
          startDate.setDate(startDate.getDate() - days);
          params.start_date = startDate.toISOString().split('T')[0];
          params.end_date = endDate.toISOString().split('T')[0];
        }
        
        // Set ad account filter
        if (selectedAdAccount !== 'all') {
          params.ad_account_id = selectedAdAccount.toString();
        }

        // Fetch summary metrics
        const summaryResponse = await api.get('/reports/summary', { params });
        setMetrics(summaryResponse.data);

        // Fetch trend data
        const trendResponse = await api.get('/reports/trends', { params });
        setTrendData(trendResponse.data || []);

        // Fetch spend by campaign
        const spendResponse = await api.get('/reports/spend-by-campaign', { params });
        setSpendByCampaign(spendResponse.data || []);

        // Fetch hierarchical metrics data
        const metricsResponse = await api.get('/reports/metrics', { params });
        setMetricsTableData(metricsResponse.data || []);
      } catch (error) {
        console.error('Failed to fetch data:', error);
      } finally {
        setLoading(false);
      }
    };

    if (dateRange !== 'custom' || (customStartDate && customEndDate)) {
      fetchData();
    }
  }, [dateRange, selectedAdAccount, customStartDate, customEndDate]);

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value: number) => {
    return new Intl.NumberFormat('en-US').format(value);
  };

  const formatPercentage = (value: number | undefined) => {
    return `${((value || 0) * 100).toFixed(2)}%`;
  };

  return (
    <DashboardLayout>
      <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold">Reports</h1>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4 items-end">
            {/* Date Range Selector */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-2">Date Range</label>
              <select
                value={dateRange}
                onChange={(e) => setDateRange(e.target.value as DateRange)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>

            {/* Custom Date Range */}
            {dateRange === 'custom' && (
              <>
                <div className="flex-1 min-w-[150px]">
                  <label className="block text-sm font-medium mb-2">Start Date</label>
                  <input
                    type="date"
                    value={customStartDate}
                    onChange={(e) => setCustomStartDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
                <div className="flex-1 min-w-[150px]">
                  <label className="block text-sm font-medium mb-2">End Date</label>
                  <input
                    type="date"
                    value={customEndDate}
                    onChange={(e) => setCustomEndDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                </div>
              </>
            )}

            {/* Ad Account Filter */}
            <div className="flex-1 min-w-[200px]">
              <label className="block text-sm font-medium mb-2">Ad Account</label>
              <select
                value={selectedAdAccount}
                onChange={(e) => setSelectedAdAccount(e.target.value === 'all' ? 'all' : parseInt(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="all">All Accounts</option>
                {adAccounts.map((account) => (
                  <option key={account.id} value={account.id}>
                    {account.accountName} ({account.platform})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Core Metrics Cards */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-gray-200 rounded w-3/4 mb-2"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : metrics ? (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Spend Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Total Spend</CardTitle>
              <DollarSign className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(metrics.spend || 0)}</div>
              <div className="flex items-center text-sm text-gray-600 mt-1">
                <span>{formatNumber(metrics.impressions || 0)} impressions</span>
              </div>
            </CardContent>
          </Card>

          {/* ROAS Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">ROAS</CardTitle>
              <TrendingUp className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{metrics.roas?.toFixed(2) || '0.00'}x</div>
              <div className="flex items-center text-sm mt-1">
                <span className={(metrics.roas || 0) >= 2 ? 'text-green-600' : 'text-red-600'}>
                  {(metrics.roas || 0) >= 2 ? '✓ Good' : '⚠ Needs improvement'}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* CPA Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">CPA</CardTitle>
              <Target className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(metrics.cpa || 0)}</div>
              <div className="flex items-center text-sm text-gray-600 mt-1">
                <span>{formatNumber(metrics.conversions || 0)} conversions</span>
              </div>
            </CardContent>
          </Card>

          {/* Additional Metrics */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">CTR</CardTitle>
              <MousePointer className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatPercentage(metrics.ctr || 0)}</div>
              <div className="flex items-center text-sm text-gray-600 mt-1">
                <span>{formatNumber(metrics.clicks || 0)} clicks</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">CPC</CardTitle>
              <DollarSign className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(metrics.cpc)}</div>
              <div className="flex items-center text-sm text-gray-600 mt-1">
                <span>Cost per click</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-gray-600">Revenue</CardTitle>
              <TrendingUp className="h-4 w-4 text-gray-400" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatCurrency(metrics.revenue)}</div>
              <div className="flex items-center text-sm text-gray-600 mt-1">
                <span>Total revenue</span>
              </div>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-gray-500">
            No data available for the selected period
          </CardContent>
        </Card>
      )}

      {/* Performance Charts */}
      {!loading && trendData.length > 0 && (
        <PerformanceCharts trendData={trendData} spendByCampaign={spendByCampaign} />
      )}

      {/* Metrics Table */}
      {!loading && metricsTableData.length > 0 && (
        <MetricsTable data={metricsTableData} />
      )}
      </div>
    </DashboardLayout>
  );
}
