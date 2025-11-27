"use client";

import { useEffect, useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

import { 
  AlertCircle, 
  ArrowDown, 
  Download, 
  Filter,
  Gift,
  CreditCard,
  RefreshCw,
  AlertTriangle
} from 'lucide-react';
import api from '@/lib/api';
import { useRouter } from 'next/navigation';
import { CreditTransaction } from '@/types';

type TransactionType = 'all' | 'deduct' | 'refund' | 'recharge' | 'gift';
type AggregationView = 'transactions' | 'daily' | 'weekly' | 'monthly';

interface TransactionHistoryResponse {
  transactions: CreditTransaction[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

interface AggregatedData {
  period: string;
  totalDeduct: number;
  totalRefund: number;
  totalRecharge: number;
  totalGift: number;
  netChange: number;
  transactionCount: number;
}

export default function TransactionHistoryPage() {
  const router = useRouter();
  const [data, setData] = useState<TransactionHistoryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Filters
  const [typeFilter, setTypeFilter] = useState<TransactionType>('all');
  const [days, setDays] = useState<number>(30);
  const [page, setPage] = useState<number>(1);
  const [view, setView] = useState<AggregationView>('transactions');

  useEffect(() => {
    fetchHistory();
  }, [typeFilter, days, page]);

  const fetchHistory = async () => {
    try {
      setLoading(true);
      const response = await api.get('/credits/history', {
        params: {
          page,
          page_size: 20,
          days,
        }
      });
      setData(response.data);
      setError(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load transaction history');
    } finally {
      setLoading(false);
    }
  };

  const getFilteredTransactions = () => {
    if (!data) return [];
    if (typeFilter === 'all') return data.transactions;
    return data.transactions.filter(t => t.type === typeFilter);
  };

  const getAggregatedData = (): AggregatedData[] => {
    if (!data || view === 'transactions') return [];
    
    const transactions = getFilteredTransactions();
    const grouped: { [key: string]: AggregatedData } = {};

    transactions.forEach(t => {
      const date = new Date(t.createdAt);
      let period: string;

      if (view === 'daily') {
        period = date.toISOString().split('T')[0];
      } else if (view === 'weekly') {
        const weekStart = new Date(date);
        weekStart.setDate(date.getDate() - date.getDay());
        period = weekStart.toISOString().split('T')[0];
      } else {
        period = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      }

      if (!grouped[period]) {
        grouped[period] = {
          period,
          totalDeduct: 0,
          totalRefund: 0,
          totalRecharge: 0,
          totalGift: 0,
          netChange: 0,
          transactionCount: 0,
        };
      }

      const amount = Number(t.amount);
      grouped[period].transactionCount++;

      if (t.type === 'deduct') {
        grouped[period].totalDeduct += amount;
        grouped[period].netChange -= amount;
      } else if (t.type === 'refund') {
        grouped[period].totalRefund += amount;
        grouped[period].netChange += amount;
      } else if (t.type === 'recharge') {
        grouped[period].totalRecharge += amount;
        grouped[period].netChange += amount;
      } else if (t.type === 'gift') {
        grouped[period].totalGift += amount;
        grouped[period].netChange += amount;
      }
    });

    return Object.values(grouped).sort((a, b) => b.period.localeCompare(a.period));
  };

  const exportToCSV = () => {
    const transactions = getFilteredTransactions();
    
    const headers = ['Date', 'Type', 'Amount', 'From Gifted', 'From Purchased', 'Balance After', 'Operation', 'Details'];
    const rows = transactions.map(t => [
      new Date(t.createdAt).toLocaleString(),
      t.type,
      t.amount,
      t.fromGifted,
      t.fromPurchased,
      t.balanceAfter,
      t.operationType || '-',
      JSON.stringify(t.details),
    ]);

    const csv = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `credit-history-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'deduct':
        return <ArrowDown className="w-4 h-4 text-red-500" />;
      case 'refund':
        return <RefreshCw className="w-4 h-4 text-blue-500" />;
      case 'recharge':
        return <CreditCard className="w-4 h-4 text-green-500" />;
      case 'gift':
        return <Gift className="w-4 h-4 text-purple-500" />;
      default:
        return null;
    }
  };

  const getTypeBadge = (type: string) => {
    const colors = {
      deduct: 'bg-red-100 text-red-700',
      refund: 'bg-blue-100 text-blue-700',
      recharge: 'bg-green-100 text-green-700',
      gift: 'bg-purple-100 text-purple-700',
    };
    return (
      <Badge className={colors[type as keyof typeof colors] || 'bg-gray-100 text-gray-700'}>
        {type}
      </Badge>
    );
  };

  const isAnomaly = (transaction: CreditTransaction) => {
    return transaction.type === 'deduct' && Number(transaction.amount) > 1000;
  };

  if (loading && !data) {
    return (
      <div className="container mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/4"></div>
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
          <Button onClick={fetchHistory} className="mt-4">
            Retry
          </Button>
        </Card>
      </div>
    );
  }

  const filteredTransactions = getFilteredTransactions();
  const aggregatedData = getAggregatedData();

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Transaction History</h1>
          <p className="text-gray-600 mt-1">View your credit usage and recharge history</p>
        </div>
        <Button onClick={() => router.push('/billing')} variant="outline">
          Back to Billing
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-500" />
            <span className="text-sm font-medium">Filters:</span>
          </div>

          {/* Type Filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value as TransactionType)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="all">All Types</option>
            <option value="deduct">Deduct</option>
            <option value="refund">Refund</option>
            <option value="recharge">Recharge</option>
            <option value="gift">Gift</option>
          </select>

          {/* Date Range Filter */}
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value={7}>Last 7 days</option>
            <option value={30}>Last 30 days</option>
            <option value={90}>Last 90 days</option>
            <option value={365}>Last year</option>
          </select>

          {/* View Toggle */}
          <select
            value={view}
            onChange={(e) => setView(e.target.value as AggregationView)}
            className="px-3 py-2 border rounded-md text-sm"
          >
            <option value="transactions">Transactions</option>
            <option value="daily">Daily Summary</option>
            <option value="weekly">Weekly Summary</option>
            <option value="monthly">Monthly Summary</option>
          </select>

          <div className="ml-auto">
            <Button onClick={exportToCSV} variant="outline" size="sm">
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </Card>

      {/* Transaction List or Aggregated View */}
      {view === 'transactions' ? (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date & Time
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Type
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Operation
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Details
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Balance After
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {filteredTransactions.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                      No transactions found
                    </td>
                  </tr>
                ) : (
                  filteredTransactions.map((transaction) => (
                    <tr 
                      key={transaction.id}
                      className={`hover:bg-gray-50 ${isAnomaly(transaction) ? 'bg-yellow-50' : ''}`}
                    >
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {new Date(transaction.createdAt).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          {getTypeIcon(transaction.type)}
                          {getTypeBadge(transaction.type)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <span className={`text-sm font-medium ${
                            transaction.type === 'deduct' ? 'text-red-600' : 'text-green-600'
                          }`}>
                            {transaction.type === 'deduct' ? '-' : '+'}
                            {Number(transaction.amount).toFixed(2)}
                          </span>
                          {isAnomaly(transaction) && (
                            <AlertTriangle className="w-4 h-4 text-yellow-500" />
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {transaction.operationType || '-'}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {transaction.details && typeof transaction.details === 'object' && 'model' in transaction.details && (
                          <div>Model: {String(transaction.details.model)}</div>
                        )}
                        {transaction.details && typeof transaction.details === 'object' && 'tokens' in transaction.details && (
                          <div>Tokens: {String(transaction.details.tokens)}</div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {Number(transaction.balanceAfter).toFixed(2)}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data && data.total > 0 && (
            <div className="px-6 py-4 border-t bg-gray-50 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, data.total)} of {data.total} transactions
              </div>
              <div className="flex gap-2">
                <Button
                  onClick={() => setPage(p => Math.max(1, p - 1))}
                  disabled={page === 1}
                  variant="outline"
                  size="sm"
                >
                  Previous
                </Button>
                <Button
                  onClick={() => setPage(p => p + 1)}
                  disabled={!data.hasMore}
                  variant="outline"
                  size="sm"
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      ) : (
        /* Aggregated View */
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Period
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Transactions
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Deducted
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Refunded
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Recharged
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Gifted
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Net Change
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {aggregatedData.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-12 text-center text-gray-500">
                      No data available
                    </td>
                  </tr>
                ) : (
                  aggregatedData.map((item) => (
                    <tr key={item.period} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {item.period}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {item.transactionCount}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-red-600">
                        {item.totalDeduct > 0 ? `-${item.totalDeduct.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-blue-600">
                        {item.totalRefund > 0 ? `+${item.totalRefund.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-green-600">
                        {item.totalRecharge > 0 ? `+${item.totalRecharge.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-purple-600">
                        {item.totalGift > 0 ? `+${item.totalGift.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <span className={item.netChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {item.netChange >= 0 ? '+' : ''}{item.netChange.toFixed(2)}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
