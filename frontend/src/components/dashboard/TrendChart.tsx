'use client';

import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface TrendDataPoint {
  date: string;
  spend: number;
  roas: number;
  cpa: number;
}

interface TrendChartProps {
  data: TrendDataPoint[];
  loading?: boolean;
}

export function TrendChart({ data, loading = false }: TrendChartProps) {
  if (loading) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-gray-100 rounded"></div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">7-Day Performance Trend</h3>
        <div className="h-64 flex items-center justify-center text-gray-500">
          No data available
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">7-Day Performance Trend</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="date" 
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
          />
          <YAxis 
            yAxisId="left"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'Spend ($)', angle: -90, position: 'insideLeft', style: { fontSize: '12px' } }}
          />
          <YAxis 
            yAxisId="right"
            orientation="right"
            stroke="#6b7280"
            style={{ fontSize: '12px' }}
            label={{ value: 'ROAS / CPA', angle: 90, position: 'insideRight', style: { fontSize: '12px' } }}
          />
          <Tooltip 
            contentStyle={{ 
              backgroundColor: '#fff', 
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
              padding: '12px'
            }}
            formatter={(value: number, name: string) => {
              if (name === 'spend') return [`$${value.toFixed(2)}`, 'Spend'];
              if (name === 'roas') return [value.toFixed(2), 'ROAS'];
              if (name === 'cpa') return [`$${value.toFixed(2)}`, 'CPA'];
              return [value, name];
            }}
          />
          <Legend 
            wrapperStyle={{ paddingTop: '20px' }}
            formatter={(value) => {
              if (value === 'spend') return 'Spend';
              if (value === 'roas') return 'ROAS';
              if (value === 'cpa') return 'CPA';
              return value;
            }}
          />
          <Line 
            yAxisId="left"
            type="monotone" 
            dataKey="spend" 
            stroke="#3b82f6" 
            strokeWidth={2}
            dot={{ fill: '#3b82f6', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line 
            yAxisId="right"
            type="monotone" 
            dataKey="roas" 
            stroke="#10b981" 
            strokeWidth={2}
            dot={{ fill: '#10b981', r: 4 }}
            activeDot={{ r: 6 }}
          />
          <Line 
            yAxisId="right"
            type="monotone" 
            dataKey="cpa" 
            stroke="#f59e0b" 
            strokeWidth={2}
            dot={{ fill: '#f59e0b', r: 4 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
