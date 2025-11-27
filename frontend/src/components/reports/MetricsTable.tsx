"use client";

import { useState, useMemo } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ChevronDown, ChevronRight, Download, ArrowUp, ArrowDown } from 'lucide-react';

interface MetricRow {
  id: string;
  name: string;
  type: 'campaign' | 'adset' | 'ad' | 'creative';
  parentId?: string;
  impressions: number;
  clicks: number;
  spend: number;
  conversions: number;
  revenue: number;
  ctr: number;
  cpc: number;
  cpa: number;
  roas: number;
  children?: MetricRow[];
}

interface MetricsTableProps {
  data: MetricRow[];
}

type SortField = 'name' | 'impressions' | 'clicks' | 'spend' | 'conversions' | 'revenue' | 'ctr' | 'cpc' | 'cpa' | 'roas';
type SortDirection = 'asc' | 'desc';

export default function MetricsTable({ data }: MetricsTableProps) {
  const [expandedRows, setExpandedRows] = useState<Set<string>>(new Set());
  const [sortField, setSortField] = useState<SortField>('spend');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  const toggleRow = (id: string) => {
    const newExpanded = new Set(expandedRows);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    setExpandedRows(newExpanded);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
  };

  const sortData = (rows: MetricRow[]): MetricRow[] => {
    return [...rows].sort((a, b) => {
      let aValue = a[sortField];
      let bValue = b[sortField];

      if (typeof aValue === 'string') {
        aValue = aValue.toLowerCase();
        bValue = (bValue as string).toLowerCase();
      }

      if (sortDirection === 'asc') {
        return aValue > bValue ? 1 : -1;
      } else {
        return aValue < bValue ? 1 : -1;
      }
    });
  };

  const sortedData = useMemo(() => sortData(data), [data, sortField, sortDirection]);

  const exportToCSV = () => {
    const headers = [
      'Type',
      'Name',
      'Impressions',
      'Clicks',
      'Spend',
      'Conversions',
      'Revenue',
      'CTR',
      'CPC',
      'CPA',
      'ROAS',
    ];

    const flattenRows = (rows: MetricRow[], level = 0): string[][] => {
      const result: string[][] = [];
      rows.forEach((row) => {
        result.push([
          row.type,
          '  '.repeat(level) + row.name,
          row.impressions.toString(),
          row.clicks.toString(),
          row.spend.toFixed(2),
          row.conversions.toString(),
          row.revenue.toFixed(2),
          (row.ctr * 100).toFixed(2) + '%',
          row.cpc.toFixed(2),
          row.cpa.toFixed(2),
          row.roas.toFixed(2),
        ]);
        if (row.children && row.children.length > 0) {
          result.push(...flattenRows(row.children, level + 1));
        }
      });
      return result;
    };

    const rows = flattenRows(sortedData);
    const csvContent = [headers, ...rows].map((row) => row.join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `metrics-${Date.now()}.csv`;
    link.click();
    URL.revokeObjectURL(url);
  };

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

  const formatPercentage = (value: number) => {
    return `${(value * 100).toFixed(2)}%`;
  };

  const renderRow = (row: MetricRow, level = 0): JSX.Element[] => {
    const isExpanded = expandedRows.has(row.id);
    const hasChildren = row.children && row.children.length > 0;

    const rows: JSX.Element[] = [
      <tr
        key={row.id}
        className={`border-b hover:bg-gray-50 ${level > 0 ? 'bg-gray-50' : ''}`}
      >
          <td className="px-4 py-3">
            <div className="flex items-center" style={{ paddingLeft: `${level * 24}px` }}>
              {hasChildren ? (
                <button
                  onClick={() => toggleRow(row.id)}
                  className="mr-2 focus:outline-none"
                >
                  {isExpanded ? (
                    <ChevronDown className="h-4 w-4" />
                  ) : (
                    <ChevronRight className="h-4 w-4" />
                  )}
                </button>
              ) : (
                <span className="mr-6"></span>
              )}
              <span className="font-medium">{row.name}</span>
              <span className="ml-2 text-xs text-gray-500 uppercase">{row.type}</span>
            </div>
          </td>
          <td className="px-4 py-3 text-right">{formatNumber(row.impressions)}</td>
          <td className="px-4 py-3 text-right">{formatNumber(row.clicks)}</td>
          <td className="px-4 py-3 text-right">{formatCurrency(row.spend)}</td>
          <td className="px-4 py-3 text-right">{formatNumber(row.conversions)}</td>
          <td className="px-4 py-3 text-right">{formatCurrency(row.revenue)}</td>
          <td className="px-4 py-3 text-right">{formatPercentage(row.ctr)}</td>
          <td className="px-4 py-3 text-right">{formatCurrency(row.cpc)}</td>
          <td className="px-4 py-3 text-right">{formatCurrency(row.cpa)}</td>
          <td className="px-4 py-3 text-right">
            <span className={row.roas >= 2 ? 'text-green-600 font-semibold' : 'text-red-600'}>
              {row.roas.toFixed(2)}x
            </span>
          </td>
        </tr>
    ];

    if (isExpanded && hasChildren) {
      row.children!.forEach((child) => {
        rows.push(...renderRow(child, level + 1));
      });
    }

    return rows;
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) return null;
    return sortDirection === 'asc' ? (
      <ArrowUp className="h-4 w-4 inline ml-1" />
    ) : (
      <ArrowDown className="h-4 w-4 inline ml-1" />
    );
  };

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Performance Metrics</CardTitle>
        <Button variant="outline" size="sm" onClick={exportToCSV}>
          <Download className="h-4 w-4 mr-1" />
          Export CSV
        </Button>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-100 border-b">
              <tr>
                <th
                  className="px-4 py-3 text-left font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('name')}
                >
                  Name <SortIcon field="name" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('impressions')}
                >
                  Impressions <SortIcon field="impressions" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('clicks')}
                >
                  Clicks <SortIcon field="clicks" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('spend')}
                >
                  Spend <SortIcon field="spend" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('conversions')}
                >
                  Conversions <SortIcon field="conversions" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('revenue')}
                >
                  Revenue <SortIcon field="revenue" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('ctr')}
                >
                  CTR <SortIcon field="ctr" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('cpc')}
                >
                  CPC <SortIcon field="cpc" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('cpa')}
                >
                  CPA <SortIcon field="cpa" />
                </th>
                <th
                  className="px-4 py-3 text-right font-semibold cursor-pointer hover:bg-gray-200"
                  onClick={() => handleSort('roas')}
                >
                  ROAS <SortIcon field="roas" />
                </th>
              </tr>
            </thead>
            <tbody>{sortedData.map((row) => renderRow(row))}</tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  );
}
