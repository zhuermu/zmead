"use client";

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, AlertTriangle, CreditCard, TrendingUp } from 'lucide-react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';

interface CreditBalance {
  giftedCredits: number;
  purchasedCredits: number;
  totalCredits: number;
}

export default function BillingPage() {
  const router = useRouter();
  const [balance, setBalance] = useState<CreditBalance | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    try {
      setLoading(true);
      const response = await api.get('/credits/balance');
      setBalance(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load credit balance');
    } finally {
      setLoading(false);
    }
  };

  const getBalanceStatus = () => {
    if (!balance) return null;
    
    if (balance.totalCredits < 10) {
      return {
        type: 'critical',
        icon: <AlertCircle className="w-5 h-5 text-red-500" />,
        message: 'Critical: Your credit balance is very low. Please recharge immediately.',
        bgColor: 'bg-red-50',
        borderColor: 'border-red-200',
        textColor: 'text-red-700'
      };
    }
    
    if (balance.totalCredits < 50) {
      return {
        type: 'warning',
        icon: <AlertTriangle className="w-5 h-5 text-yellow-500" />,
        message: 'Warning: Your credit balance is running low. Consider recharging soon.',
        bgColor: 'bg-yellow-50',
        borderColor: 'border-yellow-200',
        textColor: 'text-yellow-700'
      };
    }
    
    return null;
  };

  const balanceStatus = getBalanceStatus();

  if (loading) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-6 border-red-200 bg-red-50">
          <div className="flex items-center gap-2 text-red-700">
            <AlertCircle className="w-5 h-5" />
            <p>{error}</p>
          </div>
          <Button onClick={fetchBalance} className="mt-4">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold">Billing & Credits</h1>
        <p className="text-gray-600 mt-1">Manage your credit balance and purchase history</p>
      </div>

      {/* Balance Alert */}
      {balanceStatus && (
        <Card className={`p-4 border ${balanceStatus.borderColor} ${balanceStatus.bgColor}`}>
          <div className="flex items-start gap-3">
            {balanceStatus.icon}
            <div className="flex-1">
              <p className={`font-medium ${balanceStatus.textColor}`}>
                {balanceStatus.message}
              </p>
            </div>
            <Button 
              onClick={() => router.push('/billing/recharge')}
              className="bg-blue-600 hover:bg-blue-700"
            >
              Recharge Now
            </Button>
          </div>
        </Card>
      )}

      {/* Credit Balance Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Balance */}
        <Card className="p-6 border-2 border-blue-200 bg-gradient-to-br from-blue-50 to-white">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Total Balance</h3>
            <CreditCard className="w-5 h-5 text-blue-600" />
          </div>
          <div className="space-y-1">
            <p className="text-4xl font-bold text-blue-600">
              {balance?.totalCredits.toFixed(2)}
            </p>
            <p className="text-sm text-gray-500">Credits Available</p>
          </div>
        </Card>

        {/* Gifted Credits */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Gifted Credits</h3>
            <TrendingUp className="w-5 h-5 text-green-600" />
          </div>
          <div className="space-y-1">
            <p className="text-3xl font-bold text-gray-900">
              {balance?.giftedCredits.toFixed(2)}
            </p>
            <p className="text-sm text-gray-500">From registration & promotions</p>
          </div>
        </Card>

        {/* Purchased Credits */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-medium text-gray-600">Purchased Credits</h3>
            <CreditCard className="w-5 h-5 text-purple-600" />
          </div>
          <div className="space-y-1">
            <p className="text-3xl font-bold text-gray-900">
              {balance?.purchasedCredits.toFixed(2)}
            </p>
            <p className="text-sm text-gray-500">From recharges</p>
          </div>
        </Card>
      </div>

      {/* Credit Info */}
      <Card className="p-6">
        <h3 className="text-lg font-semibold mb-4">How Credits Work</h3>
        <div className="space-y-3 text-sm text-gray-600">
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Credits are used to pay for AI services like image generation, chat, and landing page creation</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Gifted credits are used first, followed by purchased credits</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Credits never expire - use them whenever you need</p>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-1.5 h-1.5 rounded-full bg-blue-600 mt-2"></div>
            <p>Purchase larger packages to get better discounts</p>
          </div>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button 
          onClick={() => router.push('/billing/recharge')}
          className="bg-blue-600 hover:bg-blue-700"
          size="lg"
        >
          <CreditCard className="w-4 h-4 mr-2" />
          Recharge Credits
        </Button>
        <Button 
          onClick={() => router.push('/billing/history')}
          variant="outline"
          size="lg"
        >
          View Transaction History
        </Button>
        <Button 
          onClick={() => router.push('/billing/settings')}
          variant="outline"
          size="lg"
        >
          Alert Settings
        </Button>
      </div>
    </div>
  );
}
